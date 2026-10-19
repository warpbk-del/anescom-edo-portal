"""API для 1С: накладная З-2 на подпись по цепочке менеджер → клиент → кладовщик/помощник (с 18.10.2026).

1С (расширение «ANESCOM: Подписание З-2») при проведении «Реализации товаров и услуг»
шлёт POST /api/z2 (Bearer EDO_API_TOKEN) с PDF печатной формы З-2.

Повторное проведение той же реализации:
  * PDF не изменился  → возвращается существующий документ (duplicate);
  * PDF изменился     → старый отменяется («документ в 1С изменён»), создаётся новый;
  * уже подписан всеми → already_signed, ничего не создаётся.
"""
import base64
import binascii
import json
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from . import config, db, workflow, b24people

router = APIRouter()


def require_api(authorization: Optional[str] = Header(None)):
    if authorization != f"Bearer {config.API_TOKEN}":
        raise HTTPException(401, "Неверный токен API")


class SignerIn(BaseModel):
    role: str = "other"
    role_title: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None


class Z2In(BaseModel):
    external_id: str = Field(..., description="GUID реализации в 1С")
    title: str = Field(..., description="Напр. «Накладная З-2 № 00НФ-001234 от 17.10.2026»")
    body_base64: str = Field(..., description="PDF печатной формы З-2 в base64")
    number: Optional[str] = Field(None, description="Номер реализации, напр. 00НФ-001234")
    order_no: Optional[str] = None
    deal_id: Optional[int] = None
    warehouse: Optional[str] = None
    manager_name: Optional[str] = None
    client_name: Optional[str] = None
    client_phone: Optional[str] = None       # телефоны клиента из 1С через «;»
    meta: Optional[dict] = None
    steps: Optional[List[List[SignerIn]]] = None  # явная цепочка вместо поиска в Bitrix
    start: bool = True                        # сразу разослать ссылку первому шагу


def resolve_steps(p: Z2In):
    """→ (steps, problems). Пустой шаг заменяется «заглушкой» без телефона — его заполняют в кабинете."""
    from . import chatapp
    problems = []
    if p.steps:
        return [[(s.model_dump() if hasattr(s, "model_dump") else s.dict()) for s in step] for step in p.steps if step], problems

    mgr, how = b24people.manager(p.order_no or "", p.deal_id, p.manager_name or "")
    if not mgr:
        mgr = {"role": "manager", "name": p.manager_name or None, "phone": ""}
        problems.append(f"Менеджер: {how}")
    elif not mgr.get("phone"):
        problems.append(f"Менеджер {mgr.get('name') or ''}: нет мобильного телефона ({how})")

    keepers, city = b24people.storekeepers(p.warehouse or "")
    if not keepers:
        keepers = [{"role": "storekeeper", "name": None, "phone": ""}]
        problems.append(f"Кладовщик: {city}")
    elif not any(k.get("phone") for k in keepers):
        problems.append(f"Кладовщики {city}: нет мобильных телефонов")

    client_phone = chatapp.first_phone(p.client_phone or "")
    src = ""
    if not client_phone and p.order_no:   # розница: телефон покупателя — из сделки Bitrix24 по заказу (19.10.2026)
        try:
            client_phone, src = b24people.order_contact_phone(p.order_no)
        except Exception as e:  # noqa
            src = f"Bitrix24: {str(e)[:150]}"
    client = {"role": "client", "name": p.client_name, "phone": client_phone}
    if not client_phone:
        problems.append("Клиент: нет мобильного телефона — указать в кабинете" + (f" ({src})" if src else ""))
    # порядок по решению пользователя 18.10.2026: менеджер → клиент → кладовщик/помощник
    return [[mgr], [client], keepers], problems


@router.post("/api/z2")
def api_z2(p: Z2In, request: Request, _=Depends(require_api)):
    try:
        raw = base64.b64decode("".join((p.body_base64 or "").split()), validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(400, "body_base64 не является корректным base64")
    if raw[:4] != b"%PDF":
        raise HTTPException(400, "Содержимое не похоже на PDF (нет сигнатуры %PDF)")
    doc_hash = db.sha256_bytes(raw)
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else "?")

    with db.conn() as c:
        workflow.init(c)
        prev = c.execute("SELECT * FROM documents WHERE external_id=? AND workflow=1 "
                         "AND status<>'cancelled' ORDER BY created_at DESC", (p.external_id,)).fetchall()
        for old in prev:
            if old["status"] == "signed":
                return {"status": "already_signed", "id": old["id"], "doc_uid": old["doc_uid"]}
            if old["doc_hash"] == doc_hash:
                return {"status": "duplicate", "id": old["id"], "doc_uid": old["doc_uid"],
                        "steps": workflow.summary(workflow.signers(c, old["id"]))}
        for old in prev:
            workflow.cancel(c, old["id"], "документ в 1С изменён — отправлена новая версия", ip)

    steps, problems = resolve_steps(p)

    doc_id = db.gen_token(8)
    doc_uid = db.gen_doc_uid()
    expires = (datetime.now(timezone.utc) + timedelta(days=config.LINK_TTL_DAYS)).isoformat()
    body_path = str(config.DOCS_DIR / f"{doc_id}.pdf")
    with open(body_path, "wb") as f:
        f.write(raw)
    meta = dict(p.meta or {})
    meta.update({"kind": "z2", "number": p.number, "order_no": p.order_no, "warehouse": p.warehouse,
                 "manager_name": p.manager_name, "problems": problems})
    client = next((s for st in steps for s in st if s.get("role") == "client"), {})

    with db.conn() as c:
        c.execute(
            """INSERT INTO documents(id, doc_uid, external_id, source, title, client_name,
               client_phone, body_kind, body_path, doc_hash, sign_token, sign_code, status,
               created_at, expires_at, meta)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (doc_id, doc_uid, p.external_id, "1C", p.title, p.client_name,
             client.get("phone") or None, "pdf", body_path, doc_hash,
             db.gen_token(24), db.gen_code(), "in_progress", db.now_iso(), expires,
             json.dumps(meta, ensure_ascii=False)),
        )
        db.add_event(c, doc_id, "created", ip=ip,
                     detail=f"1С: {p.title}; hash={doc_hash}")
        workflow.add_signers(c, doc_id, steps)
        for pr in problems:
            db.add_event(c, doc_id, "problem", ip=ip, detail=pr)
        first = workflow.start(c, doc_id, ip) if p.start else []

    sent = workflow.notify(first, ip) if first else []
    with db.conn() as c:
        summary = workflow.summary(workflow.signers(c, doc_id))
    return {"status": "created", "id": doc_id, "doc_uid": doc_uid, "problems": problems,
            "steps": summary, "sent": sent,
            "cabinet_url": f"{config.PUBLIC_BASE_URL}/cabinet/doc/{doc_id}"}
