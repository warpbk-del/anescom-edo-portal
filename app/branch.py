"""«Моя компания» сделки по подразделению менеджера — чтобы печатная форма заказа шла с реквизитами
своего филиала, а не филиала по умолчанию (Костанай).

Продажи идут через головное ТОО, деление по городам — по подразделениям. Правило:
  ответственный сделки → его подразделения в Bitrix (и родительские) → город в названии →
  «Моя компания» (IS_MY_COMPANY=Y), в названии которой этот город → crm.deal.update MY_COMPANY_ID.

Вызов из робота Bitrix «Исходящий вебхук» в первой стадии, ДО робота «Печатная форма заказа из 1С»:
  https://bot.anescom.kz/dogovor/b24/set-branch/{{ID}}?k=<ORDER_PDF_KEY>
Ручное соответствие (если названия не совпадают): BRANCH_MAP = {"Актобе": 12, …} в config.env
(город → ID «Моей компании»).
"""
import hmac
import logging
import re

from fastapi import APIRouter, HTTPException

from . import config
from .b24people import _b24

log = logging.getLogger("edo.branch")
router = APIRouter()

CITIES = ["Актобе", "Уральск", "Атырау", "Актау", "Костанай", "Алматы", "Астана",
          "Шымкент", "Караганда", "Павлодар", "Кызылорда", "Тараз", "Петропавловск",
          "Семей", "Усть-Каменогорск", "Кокшетау", "Талдыкорган", "Туркестан", "Жезказган"]


def city_in(text: str) -> str:
    t = (text or "").lower()
    for c in CITIES:
        if c.lower() in t:
            return c
    return ""


def departments() -> dict:
    return {str(d["ID"]): d for d in (_b24("department.get", {}) or [])}


def user_city(uid) -> tuple:
    """→ (город, название подразделения). Идём вверх по дереву подразделений."""
    users = _b24("user.get", {"ID": uid}) or []
    if not users:
        return "", ""
    deps = departments()
    for dep_id in users[0].get("UF_DEPARTMENT") or []:
        d = deps.get(str(dep_id))
        seen = set()
        while d and d["ID"] not in seen:
            seen.add(d["ID"])
            c = city_in(d.get("NAME"))
            if c:
                return c, d.get("NAME")
            d = deps.get(str(d.get("PARENT") or ""))
    return "", ""


def my_company_for(city: str):
    if city in config.BRANCH_MAP:
        return str(config.BRANCH_MAP[city]), "BRANCH_MAP"
    res = _b24("crm.company.list", {"filter": {"IS_MY_COMPANY": "Y"},
                                    "select": ["ID", "TITLE"]}) or []
    hits = [r for r in res if city_in(r.get("TITLE")) == city]
    if len(hits) == 1:
        return str(hits[0]["ID"]), hits[0]["TITLE"]
    return None, f"«Моих компаний» с городом {city}: {len(hits)}"


def set_branch(deal_id: int) -> dict:
    deal = _b24("crm.deal.get", {"id": deal_id}) or {}
    if not deal:
        raise HTTPException(404, "Сделка не найдена")
    city, dep = user_city(deal.get("ASSIGNED_BY_ID"))
    if not city:
        return {"status": "skipped", "reason": "город не найден в подразделении ответственного"}
    comp_id, how = my_company_for(city)
    if not comp_id:
        return {"status": "skipped", "city": city, "reason": how}
    if str(deal.get("MY_COMPANY_ID") or "") == comp_id:
        return {"status": "ok", "city": city, "my_company_id": comp_id, "changed": False}
    _b24("crm.deal.update", {"id": deal_id, "fields": {"MY_COMPANY_ID": comp_id}})
    log.info("Сделка %s: Моя компания %s (%s, подразделение %s)", deal_id, comp_id, city, dep)
    return {"status": "ok", "city": city, "department": dep, "my_company_id": comp_id, "changed": True}


@router.api_route("/b24/set-branch/{deal_id}", methods=["GET", "POST"])
def set_branch_route(deal_id: str, k: str = ""):
    if not config.ORDER_PDF_KEY or not hmac.compare_digest(k, config.ORDER_PDF_KEY):
        raise HTTPException(403, "Нет доступа")
    if not re.fullmatch(r"\d{1,10}", deal_id):
        raise HTTPException(400, "Неверный номер сделки")
    if not config.B24_WEBHOOK:
        raise HTTPException(503, "Не настроен вебхук Bitrix24")
    return set_branch(int(deal_id))
