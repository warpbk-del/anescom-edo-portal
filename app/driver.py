"""Кабинет водителя «Мои доставки» (поставлено 18.10.2026 23:13, к старту продаж 19.10).

Данные — смарт-процесс Bitrix24 «Доставки» (entityTypeId 1036, воронка 17). Водитель видит карточки, где он
в поле «Водитель» (ufCrm9Driver), открывает маршрут в 2ГИС / Яндекс.Картах, звонит клиенту, двигает стадию:
Назначен водитель → Взял в доставку → В пути → Доставлено (с фото подписанной накладной) / Клиент не принял / Перенос.
Руководители (админ, директор, РОП) выбирают водителя из списка. Всё пишется в Bitrix24 через вебхук портала.
"""
import base64
import logging
import re
import urllib.parse
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from . import b24people, config, db

log = logging.getLogger("edo.driver")
router = APIRouter()

ET = 1036            # смарт-процесс «Доставки»
CAT = 17             # «Общая воронка»
F_DRIVER, F_ADDR, F_ZONE = "ufCrm9Driver", "ufCrm9Address", "ufCrm9Zone"
F_FROM, F_TO, F_ORDER = "ufCrm9TimeFrom", "ufCrm9TimeTo", "ufCrm_9_ORDER_1C"
F_WH, F_INFO, F_PHONE = "ufCrm9Warehouse", "ufCrm9Info", "ufCrm9Phone"
F_PHOTO, F_FAIL = "ufCrm9WaybillPhoto", "ufCrm9FailReason"
STAGES = {  # код → (название, порядок)
    "NEW": ("Новая", 0), "PREPARATION": ("Назначен водитель", 1), "CLIENT": ("Взял в доставку", 2),
    "ON_WAY": ("В пути", 3), "DELIVERED": ("Доставлено", 4), "SUCCESS": ("Завершено", 5),
    "FAIL": ("Клиент не принял", 6), "RESCHEDULED": ("Перенос", 7),
}
ACTIVE = ("NEW", "PREPARATION", "CLIENT", "ON_WAY", "RESCHEDULED")
BOSS = ("admin", "director", "rop")
B24_TZ = timezone(timedelta(hours=3))      # время Bitrix24 — UTC+3
LOCAL_TZ = timezone(timedelta(hours=5))    # Алматы


def _stage(code: str) -> str:
    return (code or "").split(":")[-1]


def _hhmm(v: str) -> str:
    m = re.search(r"T(\d\d):(\d\d)", v or "")
    return f"{m.group(1)}:{m.group(2)}" if m else ""


def _date(v: str):
    try:
        return datetime.fromisoformat(v).date()
    except Exception:
        return None


def _items(driver_id: int, days_back: int = 7) -> list:
    since = (datetime.now(B24_TZ) - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00+03:00")
    flt = {F_DRIVER: driver_id, "categoryId": CAT, ">=updatedTime": since}
    res, start = [], 0
    while True:
        r = b24people._b24("crm.item.list", {"entityTypeId": ET, "filter": flt, "order": {"begindate": "ASC", "id": "ASC"},
                                             "select": ["*"], "start": start}) or {}
        res += r.get("items", [])
        if len(r.get("items", [])) < 50 or start > 500:
            break
        start += 50
    return res


def _view(it: dict) -> dict:
    st = _stage(it.get("stageId"))
    addr = (it.get(F_ADDR) or "").strip()
    q = urllib.parse.quote(addr)
    tf, tt = _hhmm(it.get(F_FROM)), _hhmm(it.get(F_TO))
    d = _date(it.get("begindate") or "")
    return {"id": it["id"], "title": it.get("title") or "Доставка", "stage": st, "stage_name": STAGES.get(st, (st, 9))[0],
            "order": it.get(F_ORDER) or "", "addr": addr, "zone": it.get(F_ZONE) or "", "wh": it.get(F_WH) or "",
            "info": it.get(F_INFO) or "", "phone": re.sub(r"[^\d+]", "", it.get(F_PHONE) or ""),
            "time": f"{tf}–{tt}" if tf and tt else (tf or tt), "date": d, "sum": it.get("opportunity") or 0,
            "fail": it.get(F_FAIL) or "", "has_photo": bool(it.get(F_PHOTO)),
            "map_2gis": f"https://2gis.kz/search/{q}" if addr else "",
            "map_yandex": f"https://yandex.kz/maps/?text={q}" if addr else "",
            "active": st in ACTIVE}


def _z2_status(orders: list) -> dict:
    """Номер заказа 1С → состояние накладной З-2 на портале (подписал ли клиент)."""
    out = {}
    if not orders:
        return out
    try:
        with db.conn() as c:
            for r in c.execute("SELECT id, status, meta FROM documents WHERE workflow=1 AND status<>'cancelled' "
                               "ORDER BY created_at DESC LIMIT 3000"):
                import json
                try:
                    m = json.loads(r["meta"] or "{}")
                except Exception:
                    m = {}
                o = (m.get("order_no") or "").strip()
                if o in orders and o not in out:
                    out[o] = {"id": r["id"], "status": r["status"]}
    except Exception as e:  # noqa
        log.warning("З-2 для доставок: %s", e)
    return out


def _who(request: Request):
    from . import access, main as m
    if not m.is_staff(request):
        return None, None
    s = access.scope(request)
    return s, (s.user or {})


def _drivers() -> list:
    """Водители, у которых есть доставки за 30 дней (для выбора руководителем)."""
    since = (datetime.now(B24_TZ) - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00+03:00")
    ids = {}
    try:
        r = b24people._b24("crm.item.list", {"entityTypeId": ET, "filter": {"categoryId": CAT, ">=updatedTime": since},
                                             "select": ["id", F_DRIVER]}) or {}
        for it in r.get("items", []):
            if it.get(F_DRIVER):
                ids[int(it[F_DRIVER])] = ids.get(int(it[F_DRIVER]), 0) + 1
    except Exception as e:  # noqa
        log.warning("Список водителей: %s", e)
    names = {}
    with db.conn() as c:
        for u in c.execute("SELECT b24_id, name FROM users"):
            names[u["b24_id"]] = u["name"]
    return sorted(({"id": i, "name": names.get(i) or f"Сотрудник {i}", "n": n} for i, n in ids.items()),
                  key=lambda x: x["name"])


@router.get("/driver", response_class=HTMLResponse)
def driver_page(request: Request, u: int = 0, msg: str = ""):
    from . import main as m
    s, me = _who(request)
    if s is None:
        return m.templates.TemplateResponse("login.html", {"request": request, "brand": config.BRAND,
                                                           "company": config.COMPANY, "base": m._root(), "b24": True})
    boss = s.password or s.role in BOSS
    my_id = int(me.get("b24_id") or 0)
    drivers = _drivers() if boss else []
    did = u if (boss and u) else my_id
    if boss and not did and drivers:
        did = drivers[0]["id"]
    err, items = "", []
    if did:
        try:
            items = [_view(x) for x in _items(did)]
        except Exception as e:  # noqa
            err = f"Bitrix24 не ответил: {e}"
    today = datetime.now(LOCAL_TZ).date()
    active = sorted([x for x in items if x["active"]], key=lambda x: (str(x["date"] or ""), x["time"] or "99", x["id"]))
    done = [x for x in items if not x["active"] and x["date"] and (today - x["date"]).days <= 1]
    z2 = _z2_status([x["order"] for x in items if x["order"]])
    name = next((d["name"] for d in drivers if d["id"] == did), me.get("name") or "")
    return m.templates.TemplateResponse("driver.html", {
        "request": request, "brand": config.BRAND, "company": config.COMPANY, "base": m._root(),
        "active": active, "done": done, "z2": z2, "err": err, "msg": msg, "boss": boss, "drivers": drivers,
        "did": did, "name": name, "today": today, "stages": STAGES})


def _can_edit(request: Request, item_id: int):
    s, me = _who(request)
    if s is None:
        return None, "Войдите через Битрикс24"
    it = (b24people._b24("crm.item.get", {"entityTypeId": ET, "id": item_id}) or {}).get("item") or {}
    if not it:
        return None, "Доставка не найдена"
    if not (s.password or s.role in BOSS or int(it.get(F_DRIVER) or 0) == int(me.get("b24_id") or -1)):
        return None, "Это не ваша доставка"
    return it, ""


def _back(request: Request, it: dict, msg: str):
    from . import main as m
    q = {"msg": msg}
    if request.query_params.get("u"):
        q["u"] = request.query_params["u"]
    return RedirectResponse(f"{m._root()}/driver?" + urllib.parse.urlencode(q) + f"#d{it.get('id', '')}", status_code=303)


@router.post("/driver/{item_id}/stage")
def driver_stage(request: Request, item_id: int, to: str = Form(...), reason: str = Form("")):
    it, err = _can_edit(request, item_id)
    if not it:
        return _back(request, {}, err)
    if to not in ("CLIENT", "ON_WAY", "FAIL", "RESCHEDULED"):
        return _back(request, it, "Неизвестное действие")
    if to in ("FAIL", "RESCHEDULED") and len(reason.strip()) < 3:
        return _back(request, it, "Напишите причину")
    fields = {"stageId": f"DT{ET}_{CAT}:{to}"}
    if reason.strip():
        fields[F_FAIL] = reason.strip()[:500]
    try:
        b24people._b24("crm.item.update", {"entityTypeId": ET, "id": item_id, "fields": fields})
    except Exception as e:  # noqa
        return _back(request, it, f"Не сохранилось в Битрикс24: {e}")
    return _back(request, it, f"Готово: {STAGES[to][0]}")


@router.post("/driver/{item_id}/delivered")
async def driver_delivered(request: Request, item_id: int, photo: UploadFile = File(None)):
    it, err = _can_edit(request, item_id)
    if not it:
        return _back(request, {}, err)
    fields = {"stageId": f"DT{ET}_{CAT}:DELIVERED"}
    if photo is not None and photo.filename:
        data = await photo.read()
        if len(data) > 15 * 1024 * 1024:
            return _back(request, it, "Фото слишком большое (больше 15 МБ)")
        ext = (photo.filename.rsplit(".", 1)[-1] or "jpg").lower()[:5]
        fname = f"nakladnaya_{item_id}_{datetime.now(LOCAL_TZ):%Y%m%d_%H%M}.{ext}"
        try:   # копия на диске D сервера
            pdir = config.DATA_DIR / "driver_photos"
            pdir.mkdir(parents=True, exist_ok=True)
            (pdir / fname).write_bytes(data)
        except Exception as e:  # noqa
            log.warning("Копия фото: %s", e)
        fields[F_PHOTO] = [fname, base64.b64encode(data).decode()]
    elif not it.get(F_PHOTO):
        return _back(request, it, "Сфотографируйте подписанную накладную — без фото «Доставлено» не ставится")
    try:
        b24people._b24("crm.item.update", {"entityTypeId": ET, "id": item_id, "fields": fields})
    except Exception as e:  # noqa
        return _back(request, it, f"Не сохранилось в Битрикс24: {e}")
    return _back(request, it, "Доставлено ✓ Фото накладной прикреплено")
