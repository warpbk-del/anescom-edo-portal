"""Портал EDO.ANESCOM — приём документов из 1С и подписание клиентом (ПЭП).

Запуск:  uvicorn app.main:app --host 127.0.0.1 --port 8096
"""
import base64
import contextvars
import binascii
import io
import json
import hmac
import hashlib
import re as _re
import urllib.parse
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Request, Form, HTTPException, Depends, Header, UploadFile, File
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    Response,
    RedirectResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from typing import Optional

from . import config, db, pdfcert, pdfstamp, payments, orderpdf, workflow, z2, branch, registry, analytics, dashboards, b24auth, access, briefing, reports, debtweek

# root_path НЕ задаём: caddy срезает префикс /dogovor (handle_path), приложение
# обслуживает чистые пути (/static, /cabinet, /s, ...). Префикс для ссылок в
# шаблонах берётся из _root() (заголовок X-Forwarded-Prefix от caddy / хост edo.* / config.ROOT_PATH), а абсолютные ссылки
# клиентам — из PUBLIC_BASE_URL.
app = FastAPI(title="EDO.ANESCOM", docs_url=None, redoc_url=None)
templates = Jinja2Templates(directory=str(config.BASE_DIR / "app" / "templates"))
app.include_router(payments.router)
app.include_router(orderpdf.router)
app.include_router(z2.router)
app.include_router(branch.router)
app.include_router(analytics.router)
app.include_router(dashboards.router)
app.include_router(b24auth.router)
app.include_router(access.router)
app.include_router(briefing.router)
app.include_router(reports.router)
from . import driver as _driver, helppages as _help, clientcab as _client, phonelogin as _phone  # noqa: E402
app.include_router(_driver.router)
app.include_router(_client.router)
app.include_router(_phone.router)
app.include_router(_help.router)
app.include_router(debtweek.router)
from . import finplan as _finplan  # noqa: E402
app.include_router(_finplan.router)
templates.env.globals["edo_me"] = b24auth.me
# Префикс зависит от адреса, по которому пришли: bot.anescom.kz/dogovor (caddy
# передаёт X-Forwarded-Prefix: /dogovor) или edo.anescom.kz (без префикса).
_ROOT = contextvars.ContextVar("edo_root", default=config.ROOT_PATH)


def _root() -> str:
    return _ROOT.get()


@app.middleware("http")
async def _prefix_mw(request: Request, call_next):
    pref = request.headers.get("x-forwarded-prefix")
    if pref is None:
        host = (request.headers.get("host") or "").lower()
        pref = "" if host.startswith("edo.") else config.ROOT_PATH
    tok = _ROOT.set(pref.rstrip("/"))
    try:
        return await call_next(request)
    finally:
        _ROOT.reset(tok)


app.mount("/static", StaticFiles(directory=str(config.BASE_DIR / "app" / "static")), name="static")


@app.on_event("startup")
def _startup():
    db.init()
    b24auth.init()
    with db.conn() as c:
        workflow.init(c)


# ---------------------------------------------------------------- helpers
def client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "?"


def fmt_dt(iso: Optional[str]) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso)
        dt = dt.astimezone(timezone(timedelta(hours=config.TZ_OFFSET_HOURS)))
        return dt.strftime("%d.%m.%Y %H:%M:%S") + f" (UTC+{config.TZ_OFFSET_HOURS})"
    except Exception:
        return iso


def require_api(authorization: str = Header(default="")):
    token = ""
    if authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if token != config.API_TOKEN:
        raise HTTPException(status_code=401, detail="Неверный токен API")
    return True


def sign_url(token: str) -> str:
    return f"{config.PUBLIC_BASE_URL}/s/{token}"


def doc_public(row) -> dict:
    return {
        "id": row["id"],
        "doc_uid": row["doc_uid"],
        "external_id": row["external_id"],
        "title": row["title"],
        "client_name": row["client_name"],
        "client_phone": row["client_phone"],
        "status": row["status"],
        "created_at": row["created_at"],
        "sent_at": row["sent_at"],
        "viewed_at": row["viewed_at"],
        "signed_at": row["signed_at"],
        "expires_at": row["expires_at"],
        "signer_name": row["signer_name"],
        "signer_ip": row["signer_ip"],
        "doc_hash": row["doc_hash"],
        "sign_url": sign_url(row["sign_token"]),
        "wa_status": row["wa_status"],
    }


def _wa_link(phone, text):
    digits = _re.sub(r"\D", "", phone or "")
    return "https://wa.me/" + digits + "?text=" + urllib.parse.quote(text)


def _image_to_pdf(raw: bytes) -> bytes:
    from PIL import Image
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    buf = io.BytesIO()
    im.save(buf, format="PDF", resolution=150.0)
    return buf.getvalue()


def _login_page(request, error=None, status=200):
    return templates.TemplateResponse("login.html", {
        "request": request, "brand": config.BRAND, "company": config.COMPANY,
        "base": _root(), "error": error,
    }, status_code=status)


# ---------------------------------------------------------------- API (1С)
class DocIn(BaseModel):
    external_id: Optional[str] = Field(None, description="Ссылка/номер документа в 1С")
    title: str = Field(..., description="Заголовок документа")
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    body_kind: str = Field("pdf", description="'pdf' или 'html'")
    body_base64: Optional[str] = Field(None, description="PDF в base64 (если body_kind=pdf)")
    body_html: Optional[str] = Field(None, description="HTML-тело (если body_kind=html)")
    meta: Optional[dict] = None


@app.post("/api/documents")
def api_create_document(payload: DocIn, request: Request, _=Depends(require_api)):
    kind = (payload.body_kind or "pdf").lower()
    if kind not in ("pdf", "html"):
        raise HTTPException(400, "body_kind должен быть 'pdf' или 'html'")

    doc_id = db.gen_token(8)
    doc_uid = db.gen_doc_uid()
    token = db.gen_token(24)
    code = db.gen_code()
    created = db.now_iso()
    expires = (datetime.now(timezone.utc) + timedelta(days=config.LINK_TTL_DAYS)).isoformat()

    if kind == "pdf":
        if not payload.body_base64:
            raise HTTPException(400, "Для body_kind=pdf нужен body_base64")
        try:
            raw = base64.b64decode("".join((payload.body_base64 or "").split()), validate=True)
        except (binascii.Error, ValueError):
            raise HTTPException(400, "body_base64 не является корректным base64")
        if raw[:4] != b"%PDF":
            raise HTTPException(400, "Содержимое не похоже на PDF (нет сигнатуры %PDF)")
        body_path = str(config.DOCS_DIR / f"{doc_id}.pdf")
        with open(body_path, "wb") as f:
            f.write(raw)
        doc_hash = db.sha256_bytes(raw)
    else:
        if not payload.body_html:
            raise HTTPException(400, "Для body_kind=html нужен body_html")
        raw = payload.body_html.encode("utf-8")
        body_path = str(config.DOCS_DIR / f"{doc_id}.html")
        with open(body_path, "wb") as f:
            f.write(raw)
        doc_hash = db.sha256_bytes(raw)

    with db.conn() as c:
        c.execute(
            """INSERT INTO documents
               (id, doc_uid, external_id, title, client_name, client_phone, body_kind,
                body_path, doc_hash, sign_token, sign_code, status, created_at,
                expires_at, meta)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                doc_id, doc_uid, payload.external_id, payload.title, payload.client_name,
                payload.client_phone, kind, body_path, doc_hash, token, code,
                "created", created, expires,
                json.dumps(payload.meta, ensure_ascii=False) if payload.meta else None,
            ),
        )
        db.add_event(c, doc_id, "created", ip=client_ip(request),
                     detail=f"external_id={payload.external_id}; hash={doc_hash}")

    return {
        "id": doc_id,
        "doc_uid": doc_uid,
        "sign_token": token,
        "sign_url": sign_url(token),
        "sign_code": code,
        "status": "created",
        "doc_hash": doc_hash,
        "expires_at": expires,
    }


@app.get("/api/documents/{doc_id}")
def api_get_document(doc_id: str, _=Depends(require_api)):
    with db.conn() as c:
        row = db.get_doc(c, doc_id)
        if not row:
            raise HTTPException(404, "Документ не найден")
        data = doc_public(row)
        data["events"] = [
            {"ts": e["ts"], "kind": e["kind"], "ip": e["ip"], "detail": e["detail"]}
            for e in db.get_events(c, doc_id)
        ]
        if row["workflow"]:
            data["steps"] = workflow.summary(workflow.signers(c, doc_id))
            data["current_step"] = row["current_step"]
    return data


@app.get("/api/documents")
def api_find(external_id: str, _=Depends(require_api)):
    with db.conn() as c:
        rows = c.execute(
            "SELECT * FROM documents WHERE external_id=? ORDER BY created_at DESC",
            (external_id,),
        ).fetchall()
    return [doc_public(r) for r in rows]


@app.post("/api/documents/{doc_id}/send")
def api_mark_sent(doc_id: str, request: Request, _=Depends(require_api)):
    """Помечает документ отправленным и инициирует отправку в WhatsApp."""
    from . import notify
    with db.conn() as c:
        row = db.get_doc(c, doc_id)
        if not row:
            raise HTTPException(404, "Документ не найден")
    wa = notify.send_sign_link(
        phone=row["client_phone"],
        link=sign_url(row["sign_token"]),
        code=row["sign_code"],
        title=row["title"],
        client_name=row["client_name"],
    )
    with db.conn() as c:
        c.execute(
            "UPDATE documents SET status=CASE WHEN status='created' THEN 'sent' ELSE status END,"
            " sent_at=COALESCE(sent_at,?), wa_status=? WHERE id=?",
            (db.now_iso(), wa.get("status"), doc_id),
        )
        db.add_event(c, doc_id, "sent", ip=client_ip(request),
                     detail=json.dumps(wa, ensure_ascii=False))
    return {"id": doc_id, "wa": wa}


@app.get("/api/documents/{doc_id}/certificate")
def api_certificate(doc_id: str, _=Depends(require_api)):
    with db.conn() as c:
        row = db.get_doc(c, doc_id)
        if not row:
            raise HTTPException(404, "Документ не найден")
        if row["status"] != "signed":
            raise HTTPException(409, "Документ ещё не подписан")
    return _certificate_response(row)


# ---------------------------------------------------------------- Подписание (клиент)
def _resolve(c, token):
    """→ (документ, подписант цепочки или None). Токен документа или токен подписанта."""
    row = db.get_doc_by_token(c, token)
    if row:
        return row, None
    s = workflow.signer_by_token(c, token)
    if s:
        return db.get_doc(c, s["document_id"]), s
    raise HTTPException(404, "Документ не найден")


def _is_expired(row) -> bool:
    if not row["expires_at"]:
        return False
    try:
        return datetime.now(timezone.utc) > datetime.fromisoformat(row["expires_at"])
    except Exception:
        return False


def _sign_ctx(request, row, s, token, **kw):
    wf = bool(row["workflow"]) if "workflow" in row.keys() else False
    chain = []
    if wf:
        with db.conn() as c:
            chain = workflow.signers(c, row["id"])
    ctx = {
        "request": request, "d": row, "s": s, "wf": wf, "chain": chain,
        "brand": config.BRAND, "company": config.COMPANY, "fmt_dt": fmt_dt,
        "expired": _is_expired(row), "base": _root(), "token": token,
        "doc_token": row["sign_token"],
        # код из ссылки сообщения (…/s/<token>?k=1234) — клиенту не нужно вводить его вручную
        "prefill_code": "".join(ch for ch in (request.query_params.get("k") or "") if ch.isdigit())[:6],
    }
    ctx.update(kw)
    return ctx


@app.get("/s/{token}", response_class=HTMLResponse)
def sign_page(token: str, request: Request):
    ip, ua = client_ip(request), request.headers.get("user-agent")
    with db.conn() as c:
        row, s = _resolve(c, token)
        if s is not None:
            workflow.mark_viewed(c, s, ip, ua)
            s = workflow.signer_by_token(c, token)
        elif not row["workflow"] and row["status"] in ("created", "sent"):
            # отметка первого просмотра (обычный документ с одним подписантом)
            c.execute("UPDATE documents SET status='viewed', viewed_at=COALESCE(viewed_at,?) WHERE id=?",
                      (db.now_iso(), row["id"]))
            db.add_event(c, row["id"], "viewed", ip=ip, ua=ua)
            row = db.get_doc_by_token(c, token)
    return templates.TemplateResponse("sign.html", _sign_ctx(request, row, s, token))


@app.get("/s/{token}/doc", response_class=HTMLResponse)
def sign_doc_page(token: str, request: Request, back: str = "", f: str = ""):
    """Просмотр PDF на телефоне со своей шапкой «← Назад» / «Скачать» (в приложении на экране телефона нет кнопки браузера)."""
    with db.conn() as c:
        row, _s = _resolve(c, token)
    r = _root()
    bk = back if (back.startswith("/") and not back.startswith("//")) else f"/s/{token}"
    return templates.TemplateResponse("pdfview.html", {"request": request, "brand": config.BRAND, "title": row["title"],
                                                       "pdf": f"{r}/s/{token}/{'certificate' if f == 'cert' else 'view'}",
                                                       "back": f"{r}{bk}"})


@app.get("/s/{token}/view")
def sign_view(token: str, orig: int = 0):
    with db.conn() as c:
        row, _s = _resolve(c, token)
        chain = workflow.signers(c, row["id"]) if row["workflow"] else None
    with open(row["body_path"], "rb") as f:
        data = f.read()
    if row["body_kind"] == "pdf":
        # штамп ЭП с QR внизу каждой страницы (оригинал на диске не меняется; ?orig=1 — без штампа)
        if not orig:
            data = pdfstamp.stamp(data, row, chain)
        return Response(data, media_type="application/pdf",
                        headers={"Content-Disposition": "inline"})
    return HTMLResponse(data.decode("utf-8"))


@app.post("/s/{token}/sign")
def do_sign(token: str, request: Request,
            code: str = Form(...), signer_name: str = Form(...),
            agree: str = Form(default="")):
    ip = client_ip(request)
    ua = request.headers.get("user-agent", "")
    completed, next_ids = False, []
    with db.conn() as c:
        row, s = _resolve(c, token)
        if row["workflow"]:
            if s is None or s["status"] not in ("active", "viewed") or row["status"] != "in_progress":
                return RedirectResponse(f"{_root()}/s/{token}", status_code=303)
            expected = s["code"]
        else:
            if row["status"] == "signed":
                return RedirectResponse(f"{_root()}/s/{token}", status_code=303)
            expected = row["sign_code"]

        if _is_expired(row):
            db.add_event(c, row["id"], "sign_rejected", ip=ip, detail="срок ссылки истёк")
            raise HTTPException(410, "Срок действия ссылки истёк")

        errors = []
        if not signer_name.strip():
            errors.append("Укажите ФИО")
        if code.strip() != expected:
            errors.append("Неверный код подтверждения")
            db.add_event(c, row["id"], "code_failed", ip=ip,
                         detail=(f"Шаг {s['step']}; " if s is not None else "") + f"введён код: {code.strip()[:8]}")
        if not agree:
            errors.append("Нужно согласие с подписанием")

        if errors:
            return templates.TemplateResponse("sign.html", _sign_ctx(
                request, row, s, token, errors=errors, signer_name=signer_name), status_code=400)

        if s is not None:
            completed, next_ids = workflow.sign(c, s, signer_name, ip, ua)
        else:
            c.execute(
                "UPDATE documents SET status='signed', signed_at=?, signer_name=?, "
                "signer_ip=?, signer_ua=? WHERE id=?",
                (db.now_iso(), signer_name.strip(), ip, ua, row["id"]),
            )
            db.add_event(c, row["id"], "signed", ip=ip, ua=ua,
                         detail=f"ФИО: {signer_name.strip()}; код подтверждён; хэш={row['doc_hash']}")
    # сеть — вне транзакции
    if next_ids:
        workflow.notify(next_ids, ip)
    if completed:
        workflow.notify_done(row["id"], ip)
    return RedirectResponse(f"{config.PUBLIC_BASE_URL}/s/{token}", status_code=303)


@app.post("/s/{token}/decline")
def do_decline(token: str, request: Request, reason: str = Form(""), signer_name: str = Form("")):
    """Отказ от подписания с обязательной причиной (подписант по своей ссылке)."""
    ip = client_ip(request)
    ua = request.headers.get("user-agent", "")
    with db.conn() as c:
        row, s = _resolve(c, token)
        ok_wf = row["workflow"] and s is not None and s["status"] in ("active", "viewed") and row["status"] == "in_progress"
        ok_one = (not row["workflow"]) and row["status"] in ("created", "sent", "viewed")
        if not (ok_wf or ok_one) or _is_expired(row):
            return RedirectResponse(f"{_root()}/s/{token}", status_code=303)
        if len(reason.strip()) < 3:
            return templates.TemplateResponse("sign.html", _sign_ctx(
                request, row, s, token, errors=["Чтобы отказаться, напишите причину"],
                signer_name=signer_name, open_decline=True), status_code=400)
        workflow.decline(c, row, s, reason, signer_name, ip, ua)
    workflow.notify_declined(row["id"], ip)
    return RedirectResponse(f"{config.PUBLIC_BASE_URL}/s/{token}", status_code=303)


@app.post("/api/sign/remind")
def api_sign_remind(force: int = 0, _=Depends(require_api)):
    """Автонапоминания подписантам (задача «ANESCOM sign remind», раз в час)."""
    return workflow.send_reminders(force=bool(force))


@app.post("/cabinet/bulk-sign")
async def cabinet_bulk_sign(request: Request):
    """Массовая подпись: сотрудник, вошедший через Bitrix24, подписывает свои шаги без кода из сообщения."""
    if not is_staff(request):
        raise HTTPException(403, "Требуется вход")
    sc = access.scope(request)
    u = b24auth.current_user(request)
    if not u or sc.viewing_as:
        return RedirectResponse(f"{_root()}/cabinet?view=tasks&bulk=noauth", status_code=303)
    form = await request.form()
    ids = [x for x in form.getlist("sid") if x][:100]
    if not form.get("agree"):
        return RedirectResponse(f"{_root()}/cabinet?view=tasks&bulk=agree", status_code=303)
    ip, ua = client_ip(request), request.headers.get("user-agent", "")
    done, nexts, finished = 0, [], []
    with db.conn() as c:
        for sid in ids:
            s = workflow.signer(c, sid)
            if not s or str(s["b24_user_id"] or "") != str(u["b24_id"]) or s["status"] not in ("active", "viewed"):
                continue
            d = db.get_doc(c, s["document_id"])
            if not d or d["status"] != "in_progress":
                continue
            completed, nx = workflow.sign(c, s, u.get("name") or s["name"] or "", ip, ua, method="b24")
            done += 1
            nexts += nx
            if completed:
                finished.append(d["id"])
    b24auth.log_access(request, "bulk_sign", u, f"подписано шагов: {done}")
    if nexts:
        workflow.notify(nexts, ip)
    for doc_id in finished:
        workflow.notify_done(doc_id, ip)
    return RedirectResponse(f"{_root()}/cabinet?view=tasks&bulk={done}", status_code=303)


def _certificate_response(row):
    with db.conn() as c:
        events = db.get_events(c, row["id"])
        chain = workflow.signers(c, row["id"]) if row["workflow"] else None
    pdf = pdfcert.build_certificate(row, events, chain)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="protokol_{row["id"]}.pdf"'})


@app.get("/s/{token}/certificate")
def sign_certificate(token: str):
    with db.conn() as c:
        row, _s = _resolve(c, token)
    # промежуточный протокол — для цепочки, где уже есть подписи
    if row["status"] != "signed" and not (row["workflow"] and row["status"] == "in_progress"):
        raise HTTPException(409, "Документ ещё не подписан")
    return _certificate_response(row)


# ---------------------------------------------------------------- Кабинет (сотрудники)
_COOKIE = "edo_staff"


_PWFILE = config.DATA_DIR / "staff_password.txt"   # хэш общего пароля, заданного администратором на портале


def _pw_hash(pw: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), config.SECRET_KEY.encode(), 120000).hex()


def _stored_pw_hash() -> str:
    try:
        return _PWFILE.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def check_staff_password(pw: str) -> bool:
    """Единый пароль руководителей для всех кабинетов. Задаётся администратором на /cabinet/password
    (хранится только хэш), иначе — EDO_STAFF_PASSWORD из config.env."""
    h = _stored_pw_hash()
    if h:
        return hmac.compare_digest(_pw_hash(pw or ""), h)
    return bool(pw) and hmac.compare_digest(pw, config.STAFF_PASSWORD)


def _make_cookie() -> str:
    # смена пароля закрывает все старые входы по паролю
    return hmac.new(config.SECRET_KEY.encode(), b"staff-ok" + _stored_pw_hash().encode(), hashlib.sha256).hexdigest()


def is_staff(request: Request) -> bool:
    # вход через Bitrix24 (b24auth) или запасной общий пароль
    if b24auth.current_user(request):
        return True
    return request.cookies.get(_COOKIE) == _make_cookie()


@app.get("/cabinet", response_class=HTMLResponse)
def cabinet(request: Request, view: str = "", status: str = "", q: str = "", cat: str = "", dept: str = ""):
    if not is_staff(request):
        return templates.TemplateResponse("login.html", {
            "request": request, "brand": config.BRAND, "company": config.COMPANY,
            "base": _root(), "b24": b24auth.configured(),
        })
    # водителю — сразу «Мои доставки» (18.10.2026)
    if not (view or status or q or cat):
        _u = b24auth.current_user(request) or {}
        if _u.get("role") == "driver":
            return RedirectResponse(f"{_root()}/driver", status_code=303)
    # «Мои задачи» — по умолчанию; любой фильтр/поиск переключает в реестр
    if not view:
        view = "all" if (status or q or cat) else "tasks"
    with db.conn() as c:
        raw = c.execute("SELECT * FROM documents ORDER BY created_at DESC LIMIT 2000").fetchall()
        sc = access.scope(request)
        docs = access.filter_docs(sc, c, registry.decorate(c, raw))
        vis = {d["id"] for d in docs}
        events = [e for e in registry.recent_events(c, 30, dept) if e["doc_id"] in vis][:8]
    depts = sorted({d["dept"] for d in docs if d["dept"]})
    scoped = [d for d in docs if not dept or d["dept"] == dept]
    cat_counts = {}
    for d in scoped:
        cat_counts[d["cat"]] = cat_counts.get(d["cat"], 0) + 1
    rows = scoped
    if cat:
        rows = [d for d in rows if d["cat"] == cat]
    if status:
        rows = [d for d in rows if d["status"] == status]
    if q:
        ql = q.lower()
        rows = [d for d in rows if any(ql in str(d.get(k) or "").lower()
                                       for k in ("title", "client_name", "client_phone", "external_id"))]
    dash = registry.dashboard(None, [d for d in docs if d["cat"] != "kadr"], dept)
    my = []
    u = b24auth.current_user(request)
    if u and not sc.viewing_as:
        with db.conn() as c:
            for s in workflow.my_tasks(c, u["b24_id"]):
                my.append({"sid": s["id"], "doc_id": s["document_id"], "title": s["title"],
                           "client": s["client_name"], "step": s["step"], "role_title": s["role_title"],
                           "since": registry.local_time(s["activated_at"])})
    status_counts = {}
    for d in scoped:
        status_counts[d["status"]] = status_counts.get(d["status"], 0) + 1
    return templates.TemplateResponse("cabinet.html", {
        "request": request, "brand": config.BRAND, "company": config.COMPANY,
        "base": _root(), "rows": rows[:500], "fmt_dt": fmt_dt, "local_time": registry.local_time,
        "sign_url": sign_url, "view": view, "status": status, "q": q, "cat": cat, "dept": dept,
        "depts": depts, "categories": registry.CATEGORIES, "cat_counts": cat_counts,
        "status_counts": status_counts, "total": len(scoped), "dash": dash, "events": events,
        "sla": registry.SLA_HOURS, "today": registry.today_title(),
        "my_tasks": my, "sla_table": workflow.sla_table(), "bulk": request.query_params.get("bulk"),
        "kadr_ok": sc.kadr,
    })


@app.post("/cabinet/login")
def cabinet_login(request: Request, password: str = Form(...), next: str = Form("")):
    if not check_staff_password(password):
        b24auth.log_access(request, "denied", None, "неверный пароль")
        return templates.TemplateResponse("login.html", {
            "request": request, "brand": config.BRAND, "company": config.COMPANY,
            "base": _root(), "error": "Неверный пароль", "b24": b24auth.configured(),
        }, status_code=401)
    b24auth.log_access(request, "login_password")
    # вернуть на страницу, с которой входили (/driver, /cabinet/clients, /dash …)
    root = _root()
    nxt = next if (next.startswith("/") and not next.startswith("//")) else ""
    if root and nxt.startswith(root):
        nxt = nxt[len(root):]
    resp = RedirectResponse(f"{root}{nxt or '/cabinet'}", status_code=303)
    resp.set_cookie(_COOKIE, _make_cookie(), max_age=60 * 60 * 24 * 30,
                    httponly=True, samesite="lax")
    return resp


@app.get("/cabinet/logout")
def cabinet_logout(request: Request):
    b24auth.log_access(request, "logout", b24auth.current_user(request))
    resp = RedirectResponse(f"{_root()}/cabinet", status_code=303)
    resp.delete_cookie(_COOKIE)
    b24auth.clear_session(resp)
    return resp


@app.post("/cabinet/resend/{doc_id}")
def cabinet_resend(doc_id: str, request: Request):
    if not is_staff(request):
        raise HTTPException(403, "Требуется вход")
    access.require_doc(request, doc_id)
    return api_mark_sent(doc_id, request, True)


# --- цепочка подписантов (З-2): телефон, повторная отправка, отмена ---
def _back_to(doc_id):
    return RedirectResponse(f"{_root()}/cabinet/doc/{doc_id}", status_code=303)


@app.post("/cabinet/signer/{sid}/phone")
def cabinet_signer_phone(sid: str, request: Request, phone: str = Form(...)):
    if not is_staff(request):
        raise HTTPException(403, "Требуется вход")
    access.require_doc(request, access.doc_of_signer(sid) or "")
    from . import chatapp
    n = chatapp.normalize_phone(phone)
    with db.conn() as c:
        s = workflow.signer(c, sid)
        if not s:
            raise HTTPException(404, "Подписант не найден")
        if n:
            workflow.set_phone(c, sid, n, client_ip(request))
            active = s["status"] in ("active", "viewed")
    if n and active:
        workflow.notify([sid], client_ip(request))
    return _back_to(s["document_id"])


@app.post("/cabinet/signer/{sid}/resend")
def cabinet_signer_resend(sid: str, request: Request, back: str = Form("")):
    if not is_staff(request):
        raise HTTPException(403, "Требуется вход")
    access.require_doc(request, access.doc_of_signer(sid) or "")
    with db.conn() as c:
        s = workflow.signer(c, sid)
        if not s:
            raise HTTPException(404, "Подписант не найден")
    if s["status"] in ("active", "viewed"):
        workflow.notify([sid], client_ip(request))
    if back == "tasks":
        return RedirectResponse(f"{_root()}/cabinet?sent=1", status_code=303)
    return _back_to(s["document_id"])


@app.post("/cabinet/doc/{doc_id}/start")
def cabinet_doc_start(doc_id: str, request: Request):
    if not is_staff(request):
        raise HTTPException(403, "Требуется вход")
    access.require_doc(request, doc_id)
    with db.conn() as c:
        row = db.get_doc(c, doc_id)
        ids = []
        if row and row["workflow"] and row["status"] == "in_progress" and not row["current_step"]:
            ids = workflow.start(c, doc_id, client_ip(request))
    if ids:
        workflow.notify(ids, client_ip(request))
    return _back_to(doc_id)


@app.post("/cabinet/doc/{doc_id}/cancel")
def cabinet_doc_cancel(doc_id: str, request: Request, reason: str = Form("")):
    if not is_staff(request):
        raise HTTPException(403, "Требуется вход")
    access.require_doc(request, doc_id)
    with db.conn() as c:
        row = db.get_doc(c, doc_id)
        if row and row["status"] not in ("signed", "cancelled"):
            workflow.cancel(c, doc_id, reason.strip() or "отменён в кабинете", client_ip(request))
    return _back_to(doc_id)


@app.post("/cabinet/doc/{doc_id}/skip")
def cabinet_doc_skip(doc_id: str, request: Request, reason: str = Form("")):
    if not is_staff(request):
        raise HTTPException(403, "Требуется вход")
    access.require_doc(request, doc_id)
    if not reason.strip():
        return RedirectResponse(f"{_root()}/cabinet/doc/{doc_id}?err=reason", status_code=303)
    with db.conn() as c:
        ids = workflow.skip_step(c, doc_id, reason, client_ip(request))
    if ids:
        workflow.notify(ids, client_ip(request))
    return _back_to(doc_id)


# --- загрузка документа в кабинете (как «Создать документ» в Документологе) ---
@app.get("/cabinet/new", response_class=HTMLResponse)
def cabinet_new(request: Request):
    if not is_staff(request):
        return _login_page(request)
    return templates.TemplateResponse("cabinet_new.html", {
        "request": request, "brand": config.BRAND, "company": config.COMPANY,
        "base": _root(), "err": None, "title": "",
        "client_name": "", "client_phone": "",
    })


@app.post("/cabinet/new")
async def cabinet_new_post(request: Request, title: str = Form(...),
                           client_name: str = Form(""), client_phone: str = Form(""),
                           file: UploadFile = File(...)):
    if not is_staff(request):
        raise HTTPException(403, "Требуется вход")
    raw = await file.read()
    fn = (file.filename or "").lower()

    def _back(msg):
        return templates.TemplateResponse("cabinet_new.html", {
            "request": request, "brand": config.BRAND, "company": config.COMPANY,
            "base": _root(), "err": msg, "title": title,
            "client_name": client_name, "client_phone": client_phone,
        }, status_code=400)

    if not raw:
        return _back("Файл не выбран или пустой.")
    if raw[:4] == b"%PDF" or fn.endswith(".pdf"):
        data = raw
    elif (fn.endswith((".jpg", ".jpeg", ".png", ".webp", ".bmp"))
          or raw[:3] == b"\xff\xd8\xff" or raw[:8] == b"\x89PNG\r\n\x1a\n"):
        try:
            data = _image_to_pdf(raw)
        except Exception:
            return _back("Не удалось обработать изображение.")
    else:
        return _back("Пока поддерживаются PDF и изображения (JPG, PNG). "
                     "Word/PowerPoint — сохраните в PDF и загрузите.")

    doc_id = db.gen_token(8)
    doc_uid = db.gen_doc_uid()
    token = db.gen_token(24)
    code = db.gen_code()
    created = db.now_iso()
    expires = (datetime.now(timezone.utc) + timedelta(days=config.LINK_TTL_DAYS)).isoformat()
    body_path = str(config.DOCS_DIR / f"{doc_id}.pdf")
    with open(body_path, "wb") as f:
        f.write(data)
    doc_hash = db.sha256_bytes(data)
    with db.conn() as c:
        c.execute(
            """INSERT INTO documents(id, doc_uid, external_id, source, title, client_name,
               client_phone, body_kind, body_path, doc_hash, sign_token, sign_code, status,
               created_at, expires_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (doc_id, doc_uid, None, "cabinet", title.strip(),
             client_name.strip() or None, client_phone.strip() or None, "pdf",
             body_path, doc_hash, token, code, "created", created, expires),
        )
        db.add_event(c, doc_id, "created", ip=client_ip(request),
                     detail=f"загружен в кабинете: {file.filename}; hash={doc_hash}")
    return RedirectResponse(f"{_root()}/cabinet/doc/{doc_id}", status_code=303)


@app.get("/cabinet/doc/{doc_id}", response_class=HTMLResponse)
def cabinet_doc(doc_id: str, request: Request):
    if not is_staff(request):
        return _login_page(request)
    access.require_doc(request, doc_id)
    with db.conn() as c:
        row = db.get_doc(c, doc_id)
        if not row:
            raise HTTPException(404, "Документ не найден")
        events = db.get_events(c, doc_id)
        chain = workflow.signers(c, doc_id) if row["workflow"] else []
        info = registry.decorate(c, [row])[0]
        can_skip = workflow.can_skip(c, row)
    link = sign_url(row["sign_token"])
    from . import notify
    wa_text = notify.build_message(link, row["sign_code"], row["title"], row["client_name"])
    wa = _wa_link(row["client_phone"], wa_text) if row["client_phone"] else ""
    return templates.TemplateResponse("cabinet_doc.html", {
        "request": request, "brand": config.BRAND, "company": config.COMPANY,
        "base": _root(), "d": row, "events": events, "fmt_dt": fmt_dt,
        "link": link, "wa": wa, "wa_text": wa_text, "chain": chain,
        "config_base": config.PUBLIC_BASE_URL, "info": info, "can_skip": can_skip,
        "local_time": registry.local_time, "ev_titles": registry.EVENT_TITLES, "sla": registry.SLA_HOURS, "num": registry._meta(row).get("number"),
        "err": request.query_params.get("err"),
        "step_wa": {r["id"]: (_wa_link(r["phone"], workflow.build_message(r, row)) if r["phone"] else "")
                    for r in chain},
    })


# ---------------------------------------------------------------- служебное
@app.get("/manifest.webmanifest")
def manifest():
    r = _root()
    return JSONResponse({
        "name": f"{config.BRAND} Сотрудники",
        "short_name": config.BRAND,
        "id": f"{r}/cabinet",
        "start_url": f"{r}/cabinet",
        "scope": f"{r}/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#cc2b28",
        "icons": [
            {"src": f"{r}/static/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": f"{r}/static/icon-512.png", "sizes": "512x512", "type": "image/png",
             "purpose": "any maskable"},
        ],
    }, media_type="application/manifest+json")


@app.get("/health")
def health():
    return {"ok": True, "brand": config.BRAND}


@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("landing.html", {
        "request": request, "brand": config.BRAND, "company": config.COMPANY,
        "base": _root(),
    })



# ---------------------------------------------------------------- единый пароль руководителей (18.10.2026)
@app.get("/cabinet/password", response_class=HTMLResponse)
def staff_password_page(request: Request, msg: str = ""):
    u = b24auth.current_user(request)
    if not u or u.get("role") != "admin":
        return templates.TemplateResponse("noaccess.html", {"request": request, "brand": config.BRAND, "base": _root(),
            "title": "Нет доступа", "text": "Пароль меняет администратор, вошедший через Битрикс24."})
    return templates.TemplateResponse("password.html", {"request": request, "brand": config.BRAND, "base": _root(),
        "msg": msg, "custom": bool(_stored_pw_hash())})


@app.post("/cabinet/password")
def staff_password_set(request: Request, pw1: str = Form(...), pw2: str = Form(...)):
    u = b24auth.current_user(request)
    if not u or u.get("role") != "admin":
        return RedirectResponse(f"{_root()}/cabinet", status_code=303)
    if len(pw1) < 8 or pw1 != pw2:
        return RedirectResponse(f"{_root()}/cabinet/password?msg=" + ("Пароли не совпадают" if pw1 != pw2 else "Нужно не меньше 8 символов"), status_code=303)
    _PWFILE.write_text(_pw_hash(pw1), encoding="utf-8")
    b24auth.log_access(request, "staff_password_changed")
    return RedirectResponse(f"{_root()}/cabinet/password?msg=Пароль сохранён. Старые входы по паролю закрыты.", status_code=303)
