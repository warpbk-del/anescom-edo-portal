"""Проект 19 (23.10.2026): сверка контактов и компаний Bitrix24 с клиентами 1С. 1С — главная.

Данные 1С: снимок an_partners (вид partners: партнёры, контрагенты, контактные лица с телефонами/e-mail/регионом,
признаками sold/bought) и an_order_clients (клиент каждого заказа). Данные Б24: снимок b24_snap_contact/company
(refresh_b24 — только чтение) + сделки (ORIGIN_ID = GUID заказа).

analyze() ничего не меняет в Б24: строит отчёт расхождений (XLSX в DATA_DIR/reports + краткий итог).
Правки в Б24 (apply) — отдельным шагом, только после «да» пользователя.

Правила пользователя (archive/19): 1С главная; записи Б24, которых нет в 1С, не трогаем; юрлица и ИП — компании,
физлица — контакты; клиент = были наши реализации, поставщик = были его поступления к нам (оба → «Клиент» +
отметка «Также поставщик»); телефоны/e-mail как в 1С, лишние — удалить (по списку, после «да»); для организаций без
телефона/e-mail — поиск в интернете (отдельно, с источником), для частных лиц — нет.
"""
import json
import logging
import re
import time
from datetime import datetime, timezone

from . import config
from .analytics import conn
from .b24people import _b24

log = logging.getLogger("edo.contactsync")
REPORTS = config.DATA_DIR / "reports"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------- снимок Б24 (только чтение) ----------

def _dump(entity: str, select: list) -> list:
    rows, last = [], 0
    while True:
        for attempt in range(6):
            try:
                part = _b24(f"crm.{entity}.list", {"order": {"ID": "ASC"}, "filter": {">ID": last},
                                                    "select": select, "start": -1}) or []
                break
            except Exception as e:  # noqa: BLE001 — лимит запросов Б24
                if attempt == 5:
                    raise
                log.warning("%s: %s, повтор", entity, e)
                time.sleep(2 + attempt * 2)
        if not part:
            return rows
        rows += part
        last = int(part[-1]["ID"])
        if len(part) < 50:
            return rows


def _multi(lst) -> str:
    return "; ".join(x.get("VALUE", "") for x in (lst or []) if x.get("VALUE"))


def refresh_b24() -> dict:
    t0 = time.time()
    ct = _dump("contact", ["ID", "NAME", "LAST_NAME", "SECOND_NAME", "ORIGIN_ID", "ORIGINATOR_ID", "COMPANY_ID",
                           "PHONE", "EMAIL", "DATE_CREATE", "DATE_MODIFY"])
    co = _dump("company", ["ID", "TITLE", "ORIGIN_ID", "ORIGINATOR_ID", "COMPANY_TYPE", "PHONE", "EMAIL",
                           "DATE_CREATE", "DATE_MODIFY"])
    dl = _dump("deal", ["ID", "TITLE", "ORIGIN_ID", "CONTACT_ID", "COMPANY_ID", "CLOSED", "DATE_CREATE"])
    with conn() as c:
        c.executescript("""
DROP TABLE IF EXISTS b24_snap_contact; DROP TABLE IF EXISTS b24_snap_company; DROP TABLE IF EXISTS b24_snap_deal;
CREATE TABLE b24_snap_contact (id TEXT PRIMARY KEY, name TEXT, origin TEXT, originator TEXT, company_id TEXT,
  phones TEXT, emails TEXT, created TEXT, modified TEXT);
CREATE TABLE b24_snap_company (id TEXT PRIMARY KEY, name TEXT, origin TEXT, originator TEXT, ctype TEXT,
  phones TEXT, emails TEXT, created TEXT, modified TEXT);
CREATE TABLE b24_snap_deal (id TEXT PRIMARY KEY, title TEXT, origin TEXT, contact_id TEXT, company_id TEXT,
  closed TEXT, created TEXT);
""")
        c.executemany("INSERT INTO b24_snap_contact VALUES(?,?,?,?,?,?,?,?,?)", [
            (x["ID"], " ".join(filter(None, [x.get("LAST_NAME"), x.get("NAME"), x.get("SECOND_NAME")])),
             (x.get("ORIGIN_ID") or "").lower(), x.get("ORIGINATOR_ID") or "", x.get("COMPANY_ID") or "",
             _multi(x.get("PHONE")), _multi(x.get("EMAIL")), x.get("DATE_CREATE"), x.get("DATE_MODIFY")) for x in ct])
        c.executemany("INSERT INTO b24_snap_company VALUES(?,?,?,?,?,?,?,?,?)", [
            (x["ID"], x.get("TITLE") or "", (x.get("ORIGIN_ID") or "").lower(), x.get("ORIGINATOR_ID") or "",
             x.get("COMPANY_TYPE") or "", _multi(x.get("PHONE")), _multi(x.get("EMAIL")), x.get("DATE_CREATE"),
             x.get("DATE_MODIFY")) for x in co])
        c.executemany("INSERT INTO b24_snap_deal VALUES(?,?,?,?,?,?,?)", [
            (x["ID"], x.get("TITLE") or "", (x.get("ORIGIN_ID") or "").lower(), x.get("CONTACT_ID") or "",
             x.get("COMPANY_ID") or "", x.get("CLOSED") or "", x.get("DATE_CREATE")) for x in dl])
    return {"contacts": len(ct), "companies": len(co), "deals": len(dl), "sec": round(time.time() - t0)}


# ---------- нормализация ----------

def norm_phone(p: str) -> str:
    """Казахстан: 11 цифр, начинается с 7 (8XXXXXXXXXX → 7XXXXXXXXXX, 10 цифр → 7 + номер). Иначе ''."""
    d = re.sub(r"\D", "", p or "")
    if len(d) == 11 and d[0] in "78":
        return "7" + d[1:]
    if len(d) == 10 and d[0] == "7":
        return "7" + d
    return ""


EMAIL_RE = re.compile(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$")
JUNK_EMAIL = re.compile(r"(^(no|none|net|test|nomail|noemail|empty|xxx+|123+|a+|mail)@)|(@(test|example|mail\.mail|xxx)\.)")


def norm_email(e: str) -> str:
    e = (e or "").strip().lower()
    return e if EMAIL_RE.match(e) and not JUNK_EMAIL.search(e) else ""


def norm_name(s: str) -> str:
    s = (s or "").lower().replace("ё", "е")
    s = re.sub(r"\b(тоо|ип|ао|оао|зао|ооо|too|ip)\b", " ", s)
    return re.sub(r"[^0-9a-zа-яәіңғүұқөһ]+", "", s)


def same_name(a: str, b: str) -> bool:
    """«Бармин В.В.» = «БАРМИН ВЯЧЕСЛАВ ВАЛЕНТИНОВИЧ»: фамилия совпадает, инициалы — первые буквы остальных слов."""
    if norm_name(a) == norm_name(b):
        return True
    ta = [t for t in re.split(r"[\s.]+", (a or "").lower().replace("ё", "е")) if t]
    tb = [t for t in re.split(r"[\s.]+", (b or "").lower().replace("ё", "е")) if t]
    if not ta or not tb or ta[0] != tb[0]:
        return False
    ia, ib = [t[0] for t in ta[1:]], [t[0] for t in tb[1:]]
    n = min(len(ia), len(ib))
    return n > 0 and ia[:n] == ib[:n]


def split(v: str) -> list:
    return [x.strip() for x in (v or "").split(";") if x.strip()]


# ---------- анализ ----------

def analyze() -> dict:
    with conn() as c:
        p_rows = [dict(r) for r in c.execute("SELECT * FROM an_partners")]
        ct = [dict(r) for r in c.execute("SELECT * FROM b24_snap_contact")]
        co = [dict(r) for r in c.execute("SELECT * FROM b24_snap_company")]
        dl = [dict(r) for r in c.execute("SELECT * FROM b24_snap_deal")]
        oc = {r["order_key"].lower(): dict(r) for r in c.execute("SELECT * FROM an_order_clients")}
    if not p_rows:
        return {"error": "нет данных 1С: выгрузка partners ещё не приходила"}
    by_key = {r["key"].lower(): r for r in p_rows}
    partner = {k: r for k, r in by_key.items() if r["rec"] == "partner"}
    b24 = [("contact", x) for x in ct] + [("company", x) for x in co]
    by_origin = {}
    for kind, x in b24:
        if x["origin"]:
            by_origin.setdefault(x["origin"], []).append((kind, x))
    ids = {("contact", x["id"]) for x in ct} | {("company", x["id"]) for x in co}

    def owner_partner(k):
        r = by_key.get(k)
        if not r:
            return None
        return partner.get((r["partner_key"] or "").lower()) or (r if r["rec"] == "partner" else None)

    rep = {"key_types": {}, "missing_in_b24": [], "dup_origin": [], "name_diff": [], "phones": [], "type": [],
           "deal_wrong_client": [], "deal_dead_link": []}
    # какой вид GUID лежит в ORIGIN_ID
    for o in by_origin:
        r = by_key.get(o)
        rep["key_types"][r["rec"] if r else "нет в 1С"] = rep["key_types"].get(r["rec"] if r else "нет в 1С", 0) + 1
    # дубли GUID
    for o, lst in by_origin.items():
        # пара «компания + контакт» с одним GUID — штатная работа коннектора (контактное лицо компании), не дубль
        kinds = [k for k, _ in lst]
        if kinds.count("company") > 1 or kinds.count("contact") > 1:
            r = by_key.get(o)
            rep["dup_origin"].append({"guid": o, "1c": r["name"] if r else "", "b24": [f"{k} {x['id']} {x['name']}" for k, x in lst]})
    # клиенты/поставщики 1С без записи в Б24 (партнёр и ни один его контрагент не найден)
    found_partner = set()
    for o in by_origin:
        p = owner_partner(o)
        if p:
            found_partner.add(p["key"].lower())
    for k, p in partner.items():
        if p["deleted"] or not (p["sold"] or p["bought"]):
            continue
        if k not in found_partner:
            rep["missing_in_b24"].append({"guid": k, "name": p["name"], "legal": p["legal"], "region": p["region"],
                                          "sold": p["sold"], "bought": p["bought"], "last_sale": p["last_sale"]})
    # имя, тип, телефоны / e-mail у найденных
    for o, lst in by_origin.items():
        r = by_key.get(o)
        if not r:
            continue
        p = owner_partner(o) or r
        for kind, x in lst:
            if not same_name(x["name"], r["name"]) and not same_name(x["name"], r.get("full_name")):
                rep["name_diff"].append({"b24": f"{kind} {x['id']}", "b24_name": x["name"], "1c_name": r["name"], "rec": r["rec"]})
            legal = (p.get("legal") or r["legal"] or "").lower()
            want_company = r["rec"] != "person" and "частн" not in legal and legal not in ("физлицо", "физ. лицо", "физическое лицо")
            pair_ok = kind == "contact" and want_company and any(k == "company" for k, _ in lst)
            if (kind == "company") != want_company and not pair_ok:
                rep["type"].append({"b24": f"{kind} {x['id']}", "name": x["name"], "legal": r["legal"] or p["legal"],
                                    "want": "компания" if want_company else "контакт"})
            if kind == "company":
                want_t = "CUSTOMER" if p["sold"] else ("SUPPLIER" if p["bought"] else "")
                if want_t and x.get("ctype") != want_t:
                    rep["type"].append({"b24": f"company {x['id']}", "name": x["name"], "legal": "",
                                        "want": f"тип {want_t} (сейчас {x.get('ctype') or '—'})"
                                        + (" + «также поставщик»" if p["sold"] and p["bought"] else "")})
            own = r["phones"] + ";" + (p["phones"] if p is not r and r["rec"] == "contr" else "")
            ph1 = {norm_phone(v) for v in split(own)} - {""}
            ph2 = {norm_phone(v): v for v in split(x["phones"])}
            own_e = r["emails"] + ";" + (p["emails"] if p is not r and r["rec"] == "contr" else "")
            em1 = {norm_email(v) for v in split(own_e)} - {""}
            em2 = {(v or "").strip().lower(): v for v in split(x["emails"])}
            add_p = sorted(ph1 - set(ph2))
            del_p = [v for n, v in ph2.items() if not n or n not in ph1] if ph1 else [v for n, v in ph2.items() if not n]
            add_e = sorted(em1 - set(em2))
            del_e = [v for n, v in em2.items() if not norm_email(n) or n not in em1] if em1 else \
                [v for n, v in em2.items() if not norm_email(n)]
            if add_p or del_p or add_e or del_e or (not ph1 and not ph2):
                rep["phones"].append({"b24": f"{kind} {x['id']}", "name": x["name"], "add_phone": ", ".join(add_p),
                                      "del_phone": ", ".join(del_p), "add_email": ", ".join(add_e),
                                      "del_email": ", ".join(del_e),
                                      "no_contacts": "" if (ph1 or ph2 or em1 or em2) else "нет ни в 1С, ни в Б24",
                                      "org": "1" if want_company else ""})
    # сделки
    origin_of = {("contact", x["id"]): x["origin"] for x in ct} | {("company", x["id"]): x["origin"] for x in co}
    for d in dl:
        for kind, fid in (("contact", d["contact_id"]), ("company", d["company_id"])):
            if fid and fid != "0" and (kind, fid) not in ids:
                rep["deal_dead_link"].append({"deal": d["id"], "title": d["title"], "link": f"{kind} {fid}", "closed": d["closed"]})
        o = oc.get(d["origin"])
        if not o:
            continue
        want = {o["partner_key"].lower(), o["contr_key"].lower(), (o["person_key"] or "").lower()} - {""}
        have = {origin_of.get(("contact", d["contact_id"]), ""), origin_of.get(("company", d["company_id"]), "")} - {""}
        have_partners = {(owner_partner(h) or {}).get("key", "").lower() for h in have} - {""}
        if have and not (have & want) and o["partner_key"].lower() not in have_partners:
            p = partner.get(o["partner_key"].lower()) or {}
            rep["deal_wrong_client"].append({"deal": d["id"], "title": d["title"], "1c_client": p.get("name", ""),
                                             "b24_links": ", ".join(f"{k} {i}" for k, i in (("contact", d["contact_id"]), ("company", d["company_id"])) if i and i != "0")})
    summary = {k: (len(v) if isinstance(v, list) else v) for k, v in rep.items()}
    summary["ts"] = _now()
    summary["file"] = _xlsx(rep)
    with conn() as c:
        c.execute("CREATE TABLE IF NOT EXISTS contactsync_log (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, body TEXT)")
        c.execute("INSERT INTO contactsync_log(ts, body) VALUES(?,?)", (summary["ts"], json.dumps(summary, ensure_ascii=False)))
    return summary


SHEETS = [
    ("missing_in_b24", "Нет в Битриксе", [("name", "Клиент 1С"), ("legal", "Юр/физ"), ("region", "Бизнес-регион"),
                                          ("sold", "Продажи"), ("bought", "Закупки"), ("last_sale", "Посл. продажа"), ("guid", "GUID")]),
    ("deal_wrong_client", "Сделка не на том клиенте", [("deal", "Сделка"), ("title", "Название"), ("1c_client", "Клиент в 1С"),
                                                        ("b24_links", "Сейчас в Б24")]),
    ("deal_dead_link", "Удалённый контакт в сделке", [("deal", "Сделка"), ("title", "Название"), ("link", "Ссылка"), ("closed", "Закрыта")]),
    ("dup_origin", "Дубли", [("1c", "Клиент 1С"), ("b24", "Записи Б24"), ("guid", "GUID")]),
    ("name_diff", "Другое имя", [("b24", "Запись Б24"), ("b24_name", "Имя в Б24"), ("1c_name", "Имя в 1С"), ("rec", "Вид 1С")]),
    ("type", "Тип записи", [("b24", "Запись Б24"), ("name", "Имя"), ("legal", "Юр/физ 1С"), ("want", "Должно быть")]),
    ("phones", "Телефоны и e-mail", [("b24", "Запись Б24"), ("name", "Имя"), ("add_phone", "Добавить тел."),
                                     ("del_phone", "Удалить тел."), ("add_email", "Добавить e-mail"),
                                     ("del_email", "Удалить e-mail"), ("no_contacts", "Пусто"), ("org", "Организация")]),
]


def _xlsx(rep: dict) -> str:
    from openpyxl import Workbook
    from openpyxl.styles import Font
    REPORTS.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Итог"
    ws.append(["Сверка клиентов 1С ↔ Битрикс24", datetime.now().strftime("%d.%m.%Y %H:%M")])
    ws.append(["Чей GUID в ORIGIN_ID", json.dumps(rep["key_types"], ensure_ascii=False)])
    for key, title, cols in SHEETS:
        ws.append([title, len(rep[key])])
    for key, title, cols in SHEETS:
        s = wb.create_sheet(title[:31])
        s.append([h for _, h in cols])
        for cell in s[1]:
            cell.font = Font(bold=True)
        for r in rep[key]:
            s.append(["; ".join(r[k]) if isinstance(r.get(k), list) else r.get(k, "") for k, _ in cols])
        for i, (_, h) in enumerate(cols):
            s.column_dimensions[chr(65 + i)].width = 18 if i else 40
    path = REPORTS / f"contactsync_{datetime.now():%Y%m%d_%H%M}.xlsx"
    wb.save(path)
    return str(path)


# ---------- API (Bearer EDO_API_TOKEN; только чтение Б24) ----------
import threading

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from .analytics import require_api

router = APIRouter()
_LOCK = threading.Lock()


def run(refresh: bool = True) -> dict:
    if not _LOCK.acquire(blocking=False):
        return {"busy": True}
    try:
        snap = refresh_b24() if refresh else {}
        res = analyze()
        res["snapshot"] = snap
        return res
    finally:
        _LOCK.release()


@router.post("/api/contactsync/run")
async def api_run(refresh: bool = True, _=Depends(require_api)):
    return await run_in_threadpool(run, refresh)


@router.get("/api/contactsync/last")
def api_last(_=Depends(require_api)):
    with conn() as c:
        c.execute("CREATE TABLE IF NOT EXISTS contactsync_log (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, body TEXT)")
        r = c.execute("SELECT body FROM contactsync_log ORDER BY id DESC LIMIT 1").fetchone()
    return json.loads(r[0]) if r else {}


@router.get("/api/contactsync/file")
def api_file(_=Depends(require_api)):
    files = sorted(REPORTS.glob("contactsync_*.xlsx"))
    if not files:
        raise HTTPException(404, "отчёта ещё нет")
    return FileResponse(files[-1], filename=files[-1].name)
