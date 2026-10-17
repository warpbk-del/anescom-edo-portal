"""PDF заказа клиента по публичной ссылке — для робота ChatApp «Отправить файл».

Робот «Печатная форма заказа из 1С» кладёт PDF в генератор документов Bitrix24, но ссылка
на него внутренняя (нужна авторизация), и ChatApp не может его скачать («Unable to download file»).
Этот обработчик берёт последний документ сделки через вебхук EDO_B24_WEBHOOK и отдаёт PDF.

В роботе ChatApp «Отправить файл» → «Публичная ссылка на файл»:
  https://bot.anescom.kz/dogovor/b24/order-pdf/{{ID}}?k=<ORDER_PDF_KEY>
"""
import hmac
import logging
import re

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from . import config

log = logging.getLogger("edo.orderpdf")
router = APIRouter()


def _b24(method: str, params: dict) -> dict:
    r = httpx.post(f"{config.B24_WEBHOOK}/{method}.json", json=params, timeout=20)
    r.raise_for_status()
    js = r.json()
    if "error" in js:
        raise RuntimeError(f"{method}: {js.get('error_description') or js['error']}")
    return js.get("result") or {}


def latest_pdf(deal_id: int) -> bytes:
    res = _b24("crm.documentgenerator.document.list", {
        "select": ["id", "pdfId"],
        "filter": {"entityTypeId": 2, "entityId": deal_id},
        "order": {"id": "desc"},
    })
    docs = res.get("documents") or []
    for d in docs:
        doc = _b24("crm.documentgenerator.document.get", {"id": d["id"]}).get("document") or {}
        url = doc.get("pdfUrlMachine") or doc.get("pdfUrl")
        if not url:
            continue
        r = httpx.get(url, timeout=30, follow_redirects=True)
        if r.status_code == 200 and r.content[:4] == b"%PDF":
            return r.content
        log.warning("Документ %s сделки %s: PDF не получен (%s)", d["id"], deal_id, r.status_code)
    raise HTTPException(404, "PDF заказа ещё не готов")


@router.get("/b24/order-pdf/{deal_id}")
def order_pdf(deal_id: str, k: str = ""):
    if not config.ORDER_PDF_KEY or not hmac.compare_digest(k, config.ORDER_PDF_KEY):
        raise HTTPException(403, "Нет доступа")
    if not re.fullmatch(r"\d{1,10}", deal_id):
        raise HTTPException(400, "Неверный номер сделки")
    if not config.B24_WEBHOOK:
        raise HTTPException(503, "Не настроен вебхук Bitrix24")
    data = latest_pdf(int(deal_id))
    return Response(data, media_type="application/pdf", headers={
        "Content-Disposition": 'inline; filename="Zakaz_ANESCOM.pdf"',
        "Cache-Control": "no-store",
    })
