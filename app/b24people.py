"""Подписанты из Bitrix24 через вебхук (EDO_B24_WEBHOOK): менеджер сделки и кладовщики склада.

Менеджер  = ответственный (ASSIGNED_BY_ID) сделки по заказу: по deal_id, иначе поиск сделки
            по номеру заказа (поле Z2_DEAL_ORDER_FIELD или вхождение в название), иначе
            по ФИО менеджера из 1С (user.search).
Кладовщики = активные сотрудники подразделения «Склад <город>», в должности есть «кладовщ»
            (кладовщик и помощник кладовщика — любой из них подписывает шаг).
            Переопределение: Z2_STOREKEEPERS = {"Актобе": ["Фамилия Имя", …], …} в config.env.
Город склада 1С — по вхождению названия города в наименование склада.
"""
import logging

import httpx

from . import config, chatapp

log = logging.getLogger("edo.b24people")

CITIES = ["Актобе", "Уральск", "Атырау", "Актау"]


def _b24(method: str, params: dict):
    if not config.B24_WEBHOOK:
        raise RuntimeError("Не настроен вебхук Bitrix24 (EDO_B24_WEBHOOK)")
    r = httpx.post(f"{config.B24_WEBHOOK}/{method}.json", json=params, timeout=20)
    r.raise_for_status()
    js = r.json()
    if "error" in js:
        raise RuntimeError(f"{method}: {js.get('error_description') or js['error']}")
    return js.get("result")


def city_of(warehouse: str) -> str:
    w = (warehouse or "").lower()
    for c in CITIES + list(config.Z2_STOREKEEPERS.keys()):
        if c.lower() in w:
            return c
    return ""


def user_phone(u: dict) -> str:
    for f in ("PERSONAL_MOBILE", "WORK_PHONE", "PERSONAL_PHONE"):
        n = chatapp.first_phone(u.get(f) or "")
        if n:
            return n
    return ""


def user_name(u: dict) -> str:
    return " ".join(x for x in (u.get("LAST_NAME"), u.get("NAME")) if x).strip()


def person(u: dict, role: str) -> dict:
    return {"role": role, "name": user_name(u), "phone": user_phone(u), "b24_user_id": u.get("ID"),
            "position": u.get("WORK_POSITION") or ""}


def user_by_id(uid) -> dict:
    res = _b24("user.get", {"ID": uid}) or []
    return res[0] if res else {}


def user_by_name(name: str) -> dict:
    name = (name or "").strip()
    if not name:
        return {}
    res = _b24("user.search", {"FIND": name, "ACTIVE": True}) or []
    if not res:  # «Фамилия Имя Отчество» → пробуем «Фамилия Имя»
        parts = name.split()
        if len(parts) > 2:
            res = _b24("user.search", {"FIND": " ".join(parts[:2]), "ACTIVE": True}) or []
    return res[0] if len(res) == 1 else ({} if not res else res[0])


def find_deal(order_no: str = "", deal_id=None) -> dict:
    if deal_id:
        return _b24("crm.deal.get", {"id": deal_id}) or {}
    if not order_no:
        return {}
    flt = ({config.Z2_DEAL_ORDER_FIELD: order_no} if config.Z2_DEAL_ORDER_FIELD
           else {"%TITLE": order_no})
    res = _b24("crm.deal.list", {"filter": flt, "select": ["ID", "TITLE", "ASSIGNED_BY_ID"],
                                 "order": {"ID": "DESC"}}) or []
    return res[0] if res else {}


def manager(order_no="", deal_id=None, manager_name="") -> tuple:
    """→ (person | None, откуда/проблема)."""
    try:
        deal = find_deal(order_no, deal_id)
        if deal.get("ASSIGNED_BY_ID"):
            u = user_by_id(deal["ASSIGNED_BY_ID"])
            if u:
                return person(u, "manager"), f"ответственный сделки {deal.get('ID')}"
    except Exception as e:  # noqa
        log.warning("Поиск сделки: %s", e)
    try:
        u = user_by_name(manager_name)
        if u:
            return person(u, "manager"), "по ФИО менеджера из 1С"
    except Exception as e:  # noqa
        log.warning("Поиск менеджера по ФИО: %s", e)
    if manager_name:
        return {"role": "manager", "name": manager_name, "phone": ""}, "в Bitrix не найден — телефон указать в кабинете"
    return None, "менеджер не найден"


def storekeepers(warehouse: str) -> tuple:
    """→ (список кандидатов, город/проблема)."""
    city = city_of(warehouse)
    if not city:
        return [], f"город склада не определён: {warehouse or '—'}"
    names = config.Z2_STOREKEEPERS.get(city)
    out = []
    try:
        if names:
            for n in names:
                u = user_by_name(n)
                out.append(person(u, "storekeeper") if u else
                           {"role": "storekeeper", "name": n, "phone": ""})
        else:
            deps = _b24("department.get", {"NAME": f"Склад {city}"}) or []
            for d in deps:
                users = _b24("user.get", {"FILTER": {"UF_DEPARTMENT": d["ID"], "ACTIVE": True}}) or []
                for u in users:
                    if "кладовщ" in (u.get("WORK_POSITION") or "").lower():
                        out.append(person(u, "storekeeper"))
    except Exception as e:  # noqa
        log.warning("Кладовщики %s: %s", city, e)
        return out, f"ошибка Bitrix: {e}"
    return out, city if out else f"кладовщики склада «{city}» не найдены"



def order_contact_phone(order_no: str) -> tuple:
    """Телефон клиента по номеру заказа 1С из сделки Bitrix24 (19.10.2026: для розницы «Покупатель розница …»
    телефона в 1С нет, а сообщение о заказе Bitrix24 шлёт по контакту сделки). Сделку ищем по названию
    «Заказ покупателя 00НФ-7953»; в 1С номер может быть с нулями (00НФ-007953). → (телефон, откуда)."""
    if not order_no or not config.B24_WEBHOOK:
        return "", ""
    variants = [order_no]
    if "-" in order_no:
        p, n = order_no.rsplit("-", 1)
        variants.insert(0, f"{p}-{n.lstrip('0') or '0'}")
    for v in dict.fromkeys(variants):
        deals = _b24("crm.deal.list", {"filter": {"%TITLE": v}, "select": ["ID", "TITLE", "CONTACT_ID"],
                                       "order": {"ID": "DESC"}}) or []
        deals = [d for d in deals if v in (d.get("TITLE") or "").split()] or deals
        for d in deals[:1]:
            if not d.get("CONTACT_ID") or str(d["CONTACT_ID"]) == "0":
                return "", f"сделка {d['ID']} без контакта"
            c = _b24("crm.contact.get", {"id": d["CONTACT_ID"]}) or {}
            phones = sorted(c.get("PHONE") or [], key=lambda x: x.get("VALUE_TYPE") != "MOBILE")
            for ph in phones:
                n = chatapp.normalize_phone(ph.get("VALUE") or "")
                if n:
                    return n, f"телефон из Bitrix24, сделка {d['ID']}"
            return "", f"сделка {d['ID']}: у контакта нет телефона"
    return "", "сделка по заказу не найдена в Bitrix24"


def dept_head(u: dict) -> tuple:
    """Начальник подразделения сотрудника в Bitrix24 (6п, 19.10.2026): UF_HEAD его отдела; если начальник —
    он сам или не задан, поднимаемся к родительскому отделу. → (пользователь | {}, откуда)."""
    uid = str(u.get("ID") or "")
    for dep in (u.get("UF_DEPARTMENT") or [])[:3]:
        cur, hops = dep, 0
        while cur and hops < 6:
            d = (_b24("department.get", {"ID": cur}) or [{}])[0]
            head = str(d.get("UF_HEAD") or "")
            if head and head != "0" and head != uid:
                h = user_by_id(head)
                if h:
                    return h, f"начальник «{d.get('NAME')}»"
            cur, hops = d.get("PARENT"), hops + 1
    return {}, "начальник подразделения в Bitrix24 не найден"
