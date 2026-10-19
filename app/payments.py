"""Уведомление клиенту в WhatsApp о поступлении оплаты: ПКО и эквайринг — с чеком,
безнал (поступление на расчётный счёт) — только текст.
Нет телефона в 1С (розница «Покупатель розница …»), но есть номер заказа — телефон берётся из контакта
сделки Bitrix24 «Заказ покупателя <номер>» (19.10.2026).

1С (расширение «ANESCOM: Уведомления об оплате») после пробития чека Webkassa
шлёт POST /api/payments/notify с Bearer EDO_API_TOKEN.
Сервер собирает ссылку на чек ОФД, отправляет текст через ChatApp и пишет журнал
(повторно по тому же документу 1С не отправляет).

Режим PAY_NOTIFY_MODE:
  off  — ничего не отправлять (только журнал);
  test — отправлять только на номера из PAY_TEST_PHONES;
  live — отправлять клиентам.
"""
import logging
import urllib.parse
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from . import config, db, chatapp

log = logging.getLogger("edo.payments")
router = APIRouter()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pay_notifications (
    doc_key      TEXT PRIMARY KEY,   -- уникальный ключ документа оплаты из 1С
    doc_title    TEXT,
    client_name  TEXT,
    phone        TEXT,
    amount       REAL,
    order_no     TEXT,
    pay_kind     TEXT,
    check_no     TEXT,
    receipt_url  TEXT,
    status       TEXT,               -- sent | skipped | error | off
    detail       TEXT,
    created_at   TEXT NOT NULL,
    sent_at      TEXT
);
"""


def _init():
    with db.conn() as c:
        c.executescript(_SCHEMA)


def require_api(authorization: Optional[str] = Header(None)):
    if authorization != f"Bearer {config.API_TOKEN}":
        raise HTTPException(401, "Неверный токен")


class PaymentIn(BaseModel):
    doc_key: str = Field(..., description="Уникальный идентификатор документа оплаты в 1С (GUID)")
    doc_title: str = Field(..., description="Напр. «Эквайринговая операция 00НФ-003719 от 17.10.2026»")
    pay_kind: str = Field(..., description="cash (ПКО) | card (эквайринг) | bank (безнал, без чека)")
    client_name: Optional[str] = None
    phone: Optional[str] = None
    amount: float
    order_no: Optional[str] = None
    check_no: Optional[str] = None        # номер чека (фискальный) из «Фискальные операции РК»
    check_datetime: Optional[str] = None  # ISO, напр. 2026-10-17T13:46:14
    rnk: Optional[str] = None             # регистрационный номер кассы
    offline: bool = False                 # автономный режим кассы — чек в ОФД может появиться позже


def fmt_amount(x: float) -> str:
    s = f"{x:,.2f}".replace(",", " ").replace(".", ",")
    return s[:-3] if s.endswith(",00") else s


def receipt_url(p: PaymentIn) -> str:
    if not (p.check_no and p.rnk and p.check_datetime and config.PAY_RECEIPT_URL):
        return ""
    try:
        t = datetime.fromisoformat(p.check_datetime).strftime("%Y%m%dT%H%M%S")
    except ValueError:
        return ""
    q = lambda v: urllib.parse.quote(str(v), safe="")
    return config.PAY_RECEIPT_URL.format(
        i=q(p.check_no), f=q(p.rnk), s=f"{p.amount:.2f}", t=t)


def build_text(p: PaymentIn, url: str) -> str:
    hello = f"Здравствуйте, {p.client_name}!" if p.client_name else "Здравствуйте!"
    how = {"cash": "наличными", "card": "картой", "bank": "по безналичному расчёту"}[p.pay_kind]
    no = p.order_no or ""
    if "-" in no:                      # 00НФ-007953 → 00НФ-7953, как в сообщениях о заказе
        a, b = no.rsplit("-", 1)
        no = f"{a}-{b.lstrip('0') or '0'}" if b.isdigit() else no
    order = f" по заказу {no}" if no else ""
    lines = [hello, "",
             f"Оплата {how} на сумму {fmt_amount(p.amount)} ₸{order} поступила. Спасибо!"]
    if url:
        lines += ["", f"Ваш чек: {url}"]
    elif p.check_no:
        lines += ["", f"Номер чека: {p.check_no}"]
    lines += ["", config.COMPANY]
    return "\n".join(lines)


def _allowed(phone: str) -> bool:
    if config.PAY_NOTIFY_MODE == "live":
        return True
    if config.PAY_NOTIFY_MODE == "test":
        n = chatapp.normalize_phone(phone)
        return n in {chatapp.normalize_phone(x) for x in config.PAY_TEST_PHONES}
    return False


@router.post("/api/payments/notify")
def notify_payment(p: PaymentIn, _=Depends(require_api)):
    _init()
    if p.pay_kind not in ("cash", "card", "bank"):
        raise HTTPException(400, "pay_kind должен быть cash, card или bank")
    with db.conn() as c:
        row = c.execute("SELECT status FROM pay_notifications WHERE doc_key=?",
                        (p.doc_key,)).fetchone()
        if row and row[0] == "sent":
            return {"status": "duplicate"}

    url = receipt_url(p)
    text = build_text(p, url)
    status, detail, sent_at = "off", "", None
    p.phone = chatapp.first_phone(p.phone)
    src = ""
    if not p.phone and p.order_no:      # розница: телефона в 1С нет — берём из сделки Bitrix24 по заказу
        try:
            from . import b24people
            p.phone, src = b24people.order_contact_phone(p.order_no)
        except Exception as e:  # noqa
            log.exception("Поиск телефона в Bitrix24")
            src = f"Bitrix24: {str(e)[:200]}"
    if not p.phone:
        status, detail = "skipped", "нет корректного телефона" + (f" ({src})" if src else "")
    elif not chatapp.is_configured():
        status, detail = "off", "ChatApp не настроен"
    elif not _allowed(p.phone):
        status, detail = "off", f"режим {config.PAY_NOTIFY_MODE}" + (f"; {src}" if src else "")
    else:
        try:
            chatapp.send_text(p.phone, text)
            status, sent_at, detail = "sent", db.now_iso(), src
        except Exception as e:  # noqa
            log.exception("Ошибка отправки уведомления об оплате")
            status, detail = "error", str(e)[:500]

    with db.conn() as c:
        c.execute(
            """INSERT INTO pay_notifications(doc_key, doc_title, client_name, phone, amount,
                   order_no, pay_kind, check_no, receipt_url, status, detail, created_at, sent_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(doc_key) DO UPDATE SET status=excluded.status,
                   detail=excluded.detail, sent_at=excluded.sent_at,
                   receipt_url=excluded.receipt_url, check_no=excluded.check_no""",
            (p.doc_key, p.doc_title, p.client_name, p.phone, p.amount, p.order_no,
             p.pay_kind, p.check_no, url, status, detail, db.now_iso(), sent_at))
    return {"status": status, "detail": detail, "receipt_url": url, "text": text}


@router.get("/api/payments/notify/{doc_key}")
def notify_status(doc_key: str, _=Depends(require_api)):
    _init()
    with db.conn() as c:
        row = c.execute("SELECT status, detail, sent_at, receipt_url FROM pay_notifications "
                        "WHERE doc_key=?", (doc_key,)).fetchone()
    if not row:
        raise HTTPException(404, "нет записи")
    return dict(zip(("status", "detail", "sent_at", "receipt_url"), row))
