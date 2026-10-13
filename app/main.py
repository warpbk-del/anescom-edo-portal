"""Портал ЭДО АНЕСКОМ — приём документов из 1С и подписание клиентом (ПЭП).

Запуск:  uvicorn app.main:app --host 127.0.0.1 --port 8096
"""
import base64
import binascii
import json
import hmac
import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Request, Form, HTTPException, Depends, Header
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

from . import config, db, pdfcert

# root_path НЕ задаём: caddy срезает префикс /dogovor (handle_path), приложение
# обслуживает чистые пути (/static, /cabinet, /s, ...). Префикс для ссылок в
# шаблонах берётся из config.ROOT_PATH (относительные URL), а абсолютные ссылки
# клиентам — из PUBLIC_BASE_URL.
app = FastAPI(title="ЭДО АНЕСКОМ", docs_url=None, redoc_url=None)
templates = Jinja2Templates(directory=str(config.BASE_DIR / "app" / "templates"))
app.mount("/static", StaticFiles(directory=str(config.BASE_DIR / "app" / "static")), name="static")


@app.on_event("startup")
def _startup():
    db.init()


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
        events = db.get_events(c, doc_id)
    pdf = pdfcert.build_certificate(row, events)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="protokol_{doc_id}.pdf"'})


# ---------------------------------------------------------------- Подписание (клиент)
@app.get("/s/{token}", response_class=HTMLResponse)
def sign_page(token: str, request: Request):
    with db.conn() as c:
        row = db.get_doc_by_token(c, token)
        if not row:
            raise HTTPException(404, "Документ не найден")
        # отметка первого просмотра
        if row["status"] in ("created", "sent"):
            c.execute("UPDATE documents SET status='viewed', viewed_at=COALESCE(viewed_at,?) WHERE id=?",
                      (db.now_iso(), row["id"]))
            db.add_event(c, row["id"], "viewed", ip=client_ip(request),
                         ua=request.headers.get("user-agent"))
            row = db.get_doc_by_token(c, token)

    expired = False
    if row["expires_at"]:
        try:
            expired = datetime.now(timezone.utc) > datetime.fromisoformat(row["expires_at"])
        except Exception:
            expired = False

    return templates.TemplateResponse("sign.html", {
        "request": request, "d": row, "brand": config.BRAND, "company": config.COMPANY,
        "fmt_dt": fmt_dt, "expired": expired, "base": config.ROOT_PATH,
        "token": token,
    })


@app.get("/s/{token}/view")
def sign_view(token: str):
    with db.conn() as c:
        row = db.get_doc_by_token(c, token)
        if not row:
            raise HTTPException(404, "Документ не найден")
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
    with db.conn() as c:
        row = db.get_doc_by_token(c, token)
        if not row:
            raise HTTPException(404, "Документ не найден")
        if row["status"] == "signed":
            return RedirectResponse(f"{config.ROOT_PATH}/s/{token}", status_code=303)

        if row["expires_at"]:
            try:
                if datetime.now(timezone.utc) > datetime.fromisoformat(row["expires_at"]):
                    db.add_event(c, row["id"], "sign_rejected", ip=client_ip(request),
                                 detail="срок ссылки истёк")
                    raise HTTPException(410, "Срок действия ссылки истёк")
            except HTTPException:
                raise
            except Exception:
                pass

        errors = []
        if not signer_name.strip():
            errors.append("Укажите ФИО")
        if code.strip() != row["sign_code"]:
            errors.append("Неверный код подтверждения")
            db.add_event(c, row["id"], "code_failed", ip=client_ip(request),
                         detail=f"введён код: {code.strip()[:8]}")
        if not agree:
            errors.append("Нужно согласие с подписанием")

        if errors:
            # вернуть на страницу с ошибкой
            expired = False
            return templates.TemplateResponse("sign.html", {
                "request": request, "d": row, "brand": config.BRAND,
                "company": config.COMPANY, "fmt_dt": fmt_dt, "expired": expired,
                "base": config.ROOT_PATH, "token": token,
                "errors": errors, "signer_name": signer_name,
            }, status_code=400)

        signed_at = db.now_iso()
        ip = client_ip(request)
        ua = request.headers.get("user-agent", "")
        c.execute(
            "UPDATE documents SET status='signed', signed_at=?, signer_name=?, "
            "signer_ip=?, signer_ua=? WHERE id=?",
            (signed_at, signer_name.strip(), ip, ua, row["id"]),
        )
        db.add_event(c, row["id"], "signed", ip=ip, ua=ua,
                     detail=f"ФИО: {signer_name.strip()}; код подтверждён; хэш={row['doc_hash']}")
    return RedirectResponse(f"{config.PUBLIC_BASE_URL}/s/{token}", status_code=303)


@app.get("/s/{token}/certificate")
def sign_certificate(token: str):
    with db.conn() as c:
        row = db.get_doc_by_token(c, token)
        if not row:
            raise HTTPException(404, "Документ не найден")
        if row["status"] != "signed":
            raise HTTPException(409, "Документ ещё не подписан")
        events = db.get_events(c, row["id"])
    pdf = pdfcert.build_certificate(row, events)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="protokol_{row["id"]}.pdf"'})


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


# ---------------------------------------------------------------- служебное
@app.get("/health")
def health():
    return {"ok": True, "brand": config.BRAND}


@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("landing.html", {
        "request": request, "brand": config.BRAND, "company": config.COMPANY,
        "base": config.ROOT_PATH,
    })
