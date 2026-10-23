"""Проект 19 (23.10.2026): поле «Бизнес-регион» в компаниях и контактах Битрикс24 (как справочник 1С «Бизнес-регионы»).

Решение пользователя 23.10 09:38 + «да» 12:50: поле-список «Бизнес-регион» в компаниях и контактах, значения — бизнес-регионы
партнёров 1С, заполнение по клиентам 1С (ORIGIN_ID записи Б24 = GUID партнёра / его контрагента / контактного лица).
Поле создаётся вебхуком (нужно право администратора CRM); если нет — пользователь создаёт вручную с кодом ANU_REGION.
Заполнение: сначала dry (сколько изменится), потом live — пакетами batch по 50, только где значение отличается.
"""
import logging

from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from .analytics import conn, require_api
from .b24people import _b24

log = logging.getLogger("edo.contactfix")
router = APIRouter()
FIELD = "ANU_REGION"
UF = "UF_CRM_" + FIELD
LABEL = "Бизнес-регион"


def _regions() -> list:
    with conn() as c:
        return sorted({(r["region"] or "").strip() for r in c.execute("SELECT region FROM an_partners WHERE rec='partner'")}
                      - {""})


def _field(entity: str):
    lst = _b24(f"crm.{entity}.userfield.list", {"filter": {"FIELD_NAME": UF}}) or []
    return lst[0] if lst else None


def ensure_field() -> dict:
    """Создаёт поле (или добавляет недостающие значения списка) в компаниях и контактах. Возвращает {entity: {значение: id}}."""
    vals = _regions()
    out = {}
    for entity in ("company", "contact"):
        f = _field(entity)
        if not f:
            _b24(f"crm.{entity}.userfield.add", {"fields": {
                "FIELD_NAME": FIELD, "USER_TYPE_ID": "enumeration", "MULTIPLE": "N", "SHOW_FILTER": "Y",
                "EDIT_FORM_LABEL": LABEL, "LIST_COLUMN_LABEL": LABEL, "LIST_FILTER_LABEL": LABEL,
                "LIST": [{"VALUE": v, "SORT": (i + 1) * 10} for i, v in enumerate(vals)]}})
            f = _field(entity)
        else:
            have = {x["VALUE"] for x in (f.get("LIST") or [])}
            add = [v for v in vals if v not in have]
            if add:
                _b24(f"crm.{entity}.userfield.update", {"id": f["ID"], "fields": {
                    "LIST": [{"ID": x["ID"]} for x in f.get("LIST") or []] + [{"VALUE": v} for v in add]}})
                f = _field(entity)
        out[entity] = {x["VALUE"]: str(x["ID"]) for x in (f.get("LIST") or [])}
    return out


def _want() -> dict:
    """(entity, id) → регион 1С для записей Б24, привязанных к клиентам 1С."""
    with conn() as c:
        P = {r["key"].lower(): dict(r) for r in c.execute("SELECT rec, key, partner_key, region FROM an_partners")}
        ct = [dict(r) for r in c.execute("SELECT id, origin FROM b24_snap_contact")]
        co = [dict(r) for r in c.execute("SELECT id, origin FROM b24_snap_company")]

    def region(o):
        r = P.get(o or "")
        if not r:
            return ""
        if r["rec"] != "partner":
            r = P.get((r["partner_key"] or "").lower()) or {}
        return (r.get("region") or "").strip()

    out = {}
    for entity, rows in (("contact", ct), ("company", co)):
        for x in rows:
            reg = region(x["origin"])
            if reg:
                out[(entity, x["id"])] = reg
    return out


def _current(entity: str, ids: list) -> dict:
    cur = {}
    for i in range(0, len(ids), 50):
        part = ids[i:i + 50]
        rows = _b24(f"crm.{entity}.list", {"filter": {"@ID": part}, "select": ["ID", UF], "start": -1}) or []
        for r in rows:
            cur[str(r["ID"])] = str(r.get(UF) or "")
    return cur


def fill(dry: bool = True) -> dict:
    enum = ensure_field() if not dry else {e: {x["VALUE"]: str(x["ID"]) for x in ((_field(e) or {}).get("LIST") or [])}
                                           for e in ("company", "contact")}
    want = _want()
    res = {"dry": dry, "records": len(want), "change": 0, "same": 0, "no_value": 0, "errors": [],
           "field": {e: bool(enum.get(e)) for e in enum}}
    for entity in ("company", "contact"):
        ids = [i for (e, i) in want if e == entity]
        cur = _current(entity, ids) if enum.get(entity) else {}
        cmds = {}
        for i in ids:
            vid = enum.get(entity, {}).get(want[(entity, i)])
            if not vid:
                res["no_value"] += 1
                continue
            if cur.get(i) == vid:
                res["same"] += 1
                continue
            res["change"] += 1
            cmds[f"u{i}"] = f"crm.{entity}.update?id={i}&fields[{UF}]={vid}&params[REGISTER_SONET_EVENT]=N"
        if dry:
            continue
        keys = list(cmds)
        for k in range(0, len(keys), 50):
            try:
                r = _b24("batch", {"halt": 0, "cmd": {kk: cmds[kk] for kk in keys[k:k + 50]}}) or {}
                errs = r.get("result_error") or {}
                if errs and len(res["errors"]) < 20:
                    res["errors"] += [f"{kk}: {v}" for kk, v in list(errs.items())[:5]]
            except Exception as e:  # noqa: BLE001
                res["errors"].append(f"batch {entity} {k}: {e}")
    log.info("contactfix region fill: %s", res)
    return res


@router.post("/api/contactsync/region/field")
async def api_region_field(_=Depends(require_api)):
    r = await run_in_threadpool(ensure_field)
    return {e: len(v) for e, v in r.items()}


@router.post("/api/contactsync/region/fill")
async def api_region_fill(dry: bool = True, _=Depends(require_api)):
    return await run_in_threadpool(fill, dry)
