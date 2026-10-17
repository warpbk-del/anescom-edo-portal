"""Портал ЭДО АНЕСКОМ — приём документов из 1С и подписание клиентом (ПЭП).

Запуск:  uvicorn app.main:app --host 127.0.0.1 --port 8096
"""
import base64
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

from . import config, db, pdfcert, payments, orderpdf, workflow, z2

# root_path НЕ задаём: caddy срезает префикс /dogovor (handle_path), приложение
# обслуживает чистые пути (/static, /cabinet, /s, ...). Префикс для ссылок в
# шаблонах берётся из config.ROOT_PATH (относительные URL), а абсолютные ссылки
# клиентам — из PUBLIC_BASE_URL.
app = FastAPI(title="ЭДО АНЕСКОМ", docs_url=None, redoc_url=None)
templates = Jinja2Templates(directory=str(config.BASE_DIR / "app" / "templates"))
app.include_router(payments.router)
app.include_router(orderpdf.router)
app.include_router(z2.router)
app.mount("/static", StaticFiles(directory=str(config.BASE_DIR / "app" / "static")), name="static")


@app.on_event("startup")
def _startup():
    db.init()
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
        "base": config.ROOT_PATH, "error": error,
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
            raw = base64.b64decode(payload.body_base64, validate=True)
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
        "expired": _is_expired(row), "base": config.ROOT_PATH, "token": token,
        "doc_token": row["sign_token"],
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


@app.get("/s/{token}/view")
def sign_view(token: str):
    with db.conn() as c:
        row, _s = _resolve(c, token)
    with open(row["body_path"], "rb") as f:
        data = f.read()
    if row["body_kind"] == "pdf":
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
                return RedirectResponse(f"{config.ROOT_PATH}/s/{token}", status_code=303)
            expected = s["code"]
        else:
            if row["status"] == "signed":
                return RedirectResponse(f"{config.ROOT_PATH}/s/{token}", status_code=303)
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
    if row["status"] != "signed":
        raise HTTPException(409, "Документ ещё не подписан")
    return _certificate_response(row)


# ---------------------------------------------------------------- Кабинет (сотрудники)
_COOKIE = "edo_staff"


def _make_cookie() -> str:
    return hmac.new(config.SECRET_KEY.encode(), b"staff-ok", hashlib.sha256).hexdigest()


def is_staff(request: Request) -> bool:
    return request.cookies.get(_COOKIE) == _make_cookie()


@app.get("/cabinet", response_class=HTMLResponse)
def cabinet(request: Request, status: str = "", q: str = ""):
    if not is_staff(request):
        return templates.TemplateResponse("login.html", {
            "request": request, "brand": config.BRAND, "company": config.COMPANY,
            "base": config.ROOT_PATH,
        })
    sql = "SELECT * FROM documents"
    args = []
    where = []
    if status:
        where.append("status=?"); args.append(status)
    if q:
        where.append("(title LIKE ? OR client_name LIKE ? OR client_phone LIKE ? OR external_id LIKE ?)")
        args += [f"%{q}%"] * 4
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC LIMIT 500"
    with db.conn() as c:
        rows = c.execute(sql, args).fetchall()
        counts = {r["status"]: r["n"] for r in c.execute(
            "SELECT status, COUNT(*) n FROM documents GROUP BY status").fetchall()}
        total = c.execute("SELECT COUNT(*) n FROM documents").fetchone()["n"]
    return templates.TemplateResponse("cabinet.html", {
        "request": request, "brand": config.BRAND, "company": config.COMPANY,
        "base": config.ROOT_PATH, "rows": rows, "fmt_dt": fmt_dt,
        "sign_url": sign_url, "status": status, "q": q, "counts": counts, "total": total,
    })


@app.post("/cabinet/login")
def cabinet_login(request: Request, password: str = Form(...)):
    if password != config.STAFF_PASSWORD:
        return templates.TemplateResponse("login.html", {
            "request": request, "brand": config.BRAND, "company": config.COMPANY,
            "base": config.ROOT_PATH, "error": "Неверный пароль",
        }, status_code=401)
    resp = RedirectResponse(f"{config.ROOT_PATH}/cabinet", status_code=303)
    resp.set_cookie(_COOKIE, _make_cookie(), max_age=60 * 60 * 24 * 30,
                    httponly=True, samesite="lax")
    return resp


@app.get("/cabinet/logout")
def cabinet_logout():
    resp = RedirectResponse(f"{config.ROOT_PATH}/cabinet", status_code=303)
    resp.delete_cookie(_COOKIE)
    return resp


@app.post("/cabinet/resend/{doc_id}")
def cabinet_resend(doc_id: str, request: Request):
    if not is_staff(request):
        raise HTTPException(403, "Требуется вход")
    return api_mark_sent(doc_id, request, True)


# --- цепочка подписантов (З-2): телефон, повторная отправка, отмена ---
def _back_to(doc_id):
    return RedirectResponse(f"{config.ROOT_PATH}/cabinet/doc/{doc_id}", status_code=303)


@app.post("/cabinet/signer/{sid}/phone")
def cabinet_signer_phone(sid: str, request: Request, phone: str = Form(...)):
    if not is_staff(request):
        raise HTTPException(403, "Требуется вход")
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
def cabinet_signer_resend(sid: str, request: Request):
    if not is_staff(request):
        raise HTTPException(403, "Требуется вход")
    with db.conn() as c:
        s = workflow.signer(c, sid)
        if not s:
            raise HTTPException(404, "Подписант не найден")
    if s["status"] in ("active", "viewed"):
        workflow.notify([sid], client_ip(request))
    return _back_to(s["document_id"])


@app.post("/cabinet/doc/{doc_id}/start")
def cabinet_doc_start(doc_id: str, request: Request):
    if not is_staff(request):
        raise HTTPException(403, "Требуется вход")
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
    with db.conn() as c:
        row = db.get_doc(c, doc_id)
        if row and row["status"] not in ("signed", "cancelled"):
            workflow.cancel(c, doc_id, reason.strip() or "отменён в кабинете", client_ip(request))
    return _back_to(doc_id)


# --- загрузка документа в кабинете (как «Создать документ» в Документологе) ---
@app.get("/cabinet/new", response_class=HTMLResponse)
def cabinet_new(request: Request):
    if not is_staff(request):
        return _login_page(request)
    return templates.TemplateResponse("cabinet_new.html", {
        "request": request, "brand": config.BRAND, "company": config.COMPANY,
        "base": config.ROOT_PATH, "err": None, "title": "",
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
            "base": config.ROOT_PATH, "err": msg, "title": title,
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
    return RedirectResponse(f"{config.ROOT_PATH}/cabinet/doc/{doc_id}", status_code=303)


@app.get("/cabinet/doc/{doc_id}", response_class=HTMLResponse)
def cabinet_doc(doc_id: str, request: Request):
    if not is_staff(request):
        return _login_page(request)
    with db.conn() as c:
        row = db.get_doc(c, doc_id)
        if not row:
            raise HTTPException(404, "Документ не найден")
        events = db.get_events(c, doc_id)
        chain = workflow.signers(c, doc_id) if row["workflow"] else []
    link = sign_url(row["sign_token"])
    from . import notify
    wa_text = notify.build_message(link, row["sign_code"], row["title"], row["client_name"])
    wa = _wa_link(row["client_phone"], wa_text) if row["client_phone"] else ""
    return templates.TemplateResponse("cabinet_doc.html", {
        "request": request, "brand": config.BRAND, "company": config.COMPANY,
        "base": config.ROOT_PATH, "d": row, "events": events, "fmt_dt": fmt_dt,
        "link": link, "wa": wa, "wa_text": wa_text, "chain": chain,
        "config_base": config.PUBLIC_BASE_URL,
        "step_wa": {r["id"]: (_wa_link(r["phone"], workflow.build_message(r, row)) if r["phone"] else "")
                    for r in chain},
    })


# ---------------------------------------------------------------- служебное
@app.get("/manifest.webmanifest")
def manifest():
    r = config.ROOT_PATH
    return JSONResponse({
        "name": config.BRAND,
        "short_name": config.BRAND,
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
        "base": config.ROOT_PATH,
    })
