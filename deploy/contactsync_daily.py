"""Проект 19 (23.10.2026, «Делай» 21:33): ежедневная проверка сделок Б24 по 1С — всё как в заказе 1С.

Запуск: задача планировщика «ANESCOM contactsync daily» (05:00 и 14:30, после выгрузок аналитики 1С 20:00/13:00).
Шаги: снимок Б24 → строгий план (plan_deals(strict=True)) → создание недостающих клиентов (частное лицо → контакт,
организация → компания; ORIGIN_ID = GUID партнёра) → применение плана (сделка перечитывается, старые значения
сохраняются в contactsync_plan → откат POST /api/contactsync/apply?revert=true).
Защита: если правок больше LIMIT — ничего не пишем, только отчёт (аномалия: проверить вручную).
Отчёт: data\\reports\\contactsync_daily_YYYYMMDD_HHMM.json + строка в contactsync_log.
"""
import collections
import json
import os
import sys
import time
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from app.analytics import conn  # noqa: E402
from app.b24people import _b24  # noqa: E402
from app import contactsync as cs  # noqa: E402

LIMIT = 1500
REP = os.path.join(BASE, "data", "reports")
LOCK = os.path.join(REP, "contactsync_daily.lock")


def create_missing(rep):
    with conn() as db:
        rows = [dict(r) for r in db.execute("""SELECT p.deal, lower(o.partner_key) pk FROM contactsync_plan p
            JOIN b24_snap_deal d ON d.id=p.deal JOIN an_order_clients o ON lower(o.order_key)=d.origin
            WHERE p.kind='нет записи в Б24' AND p.status='план'""")]
        P = {r["key"].lower(): dict(r) for r in db.execute("SELECT * FROM an_partners")}
    made = {}
    for pk in sorted({r["pk"] for r in rows if r["pk"]}):
        p = P.get(pk) or {}
        if not p:
            continue
        phones = [{"VALUE": "+" + n, "VALUE_TYPE": "WORK"} for n in dict.fromkeys(cs.norm_phone(v) for v in cs.split(p.get("phones"))) if n]
        emails = [{"VALUE": e, "VALUE_TYPE": "WORK"} for e in dict.fromkeys(cs.norm_email(v) for v in cs.split(p.get("emails"))) if e]
        if cs._is_private(p):
            ex = _b24("crm.contact.list", {"filter": {"ORIGIN_ID": pk}, "select": ["ID"]}) or []
            if ex:
                made[pk] = ("contact", ex[0]["ID"])
                continue
            w = (p.get("name") or "").split()
            f = {"LAST_NAME": w[0] if w else "", "NAME": w[1] if len(w) > 1 else "", "SECOND_NAME": " ".join(w[2:]),
                 "TYPE_ID": "CLIENT", "ORIGIN_ID": pk, "ORIGINATOR_ID": "ONE_C", "OPENED": "Y", "PHONE": phones, "EMAIL": emails}
            made[pk] = ("contact", str(_b24("crm.contact.add", {"fields": f, "params": {"REGISTER_SONET_EVENT": "N"}})))
        else:
            ex = _b24("crm.company.list", {"filter": {"ORIGIN_ID": pk}, "select": ["ID"]}) or []
            if ex:
                made[pk] = ("company", ex[0]["ID"])
                continue
            f = {"TITLE": p.get("name") or "", "COMPANY_TYPE": "CUSTOMER", "ORIGIN_ID": pk, "ORIGINATOR_ID": "ONE_C",
                 "OPENED": "Y", "PHONE": phones, "EMAIL": emails}
            made[pk] = ("company", str(_b24("crm.company.add", {"fields": f, "params": {"REGISTER_SONET_EVENT": "N"}})))
        rep["created"].append({"client": p.get("name"), "kind": made[pk][0], "id": made[pk][1]})
    for r in rows:
        t = made.get(r["pk"])
        if not t:
            continue
        try:
            d = _b24("crm.deal.get", {"id": r["deal"]}) or {}
            fields = {"CONTACT_IDS": [t[1]]} if t[0] == "contact" else {"COMPANY_ID": t[1]}
            co = d.get("COMPANY_ID")
            if t[0] == "contact" and co and co != "0":
                try:
                    _b24("crm.company.get", {"id": co})
                except Exception:  # noqa: BLE001 — удалённая компания
                    fields["COMPANY_ID"] = 0
            _b24("crm.deal.update", {"id": r["deal"], "fields": fields, "params": {"REGISTER_SONET_EVENT": "N"}})
            with conn() as db:
                db.execute("UPDATE contactsync_plan SET status='сделано', applied=?, new_contact=?, new_company=? WHERE deal=?",
                           (cs._now(), t[1] if t[0] == "contact" else "", t[1] if t[0] == "company" else "", r["deal"]))
            rep["linked_new"] += 1
            time.sleep(0.4)
        except Exception as e:  # noqa: BLE001
            rep["errors"].append(f"{r['deal']}: {e}")


def main():
    os.makedirs(REP, exist_ok=True)
    if os.path.exists(LOCK) and time.time() - os.path.getmtime(LOCK) < 6 * 3600:
        print("уже идёт")
        return
    open(LOCK, "w").write(str(os.getpid()))
    rep = {"start": cs._now(), "created": [], "linked_new": 0, "applied": 0, "skipped": 0, "errors": [], "deals": []}
    try:
        rep["snapshot"] = cs.refresh_b24()
        st = cs.plan_deals(strict=True)
        rep["plan"] = {k: v for k, v in st.items() if k != "file"}
        with conn() as db:
            ids = [r[0] for r in db.execute("SELECT deal FROM contactsync_plan WHERE status='план' AND (new_contact<>'' OR new_company<>'')")]
            nt = db.execute("SELECT count(*) FROM contactsync_plan WHERE status='план' AND kind='нет записи в Б24'").fetchone()[0]
        if len(ids) + nt > LIMIT:
            rep["stopped"] = f"правок {len(ids) + nt} > {LIMIT}: ничего не записано, нужна ручная проверка"
        else:
            for i in range(0, len(ids), 200):
                res = cs.apply_deals(ids[i:i + 200])
                rep["applied"] += res["done"]
                rep["skipped"] += len(res["skipped"])
                rep["errors"] += res["errors"]
            rep["deals"] = ids[:300]
            create_missing(rep)
    except Exception as e:  # noqa: BLE001
        rep["errors"].append(f"сбой: {e}")
    finally:
        rep["end"] = cs._now()
        f = os.path.join(REP, "contactsync_daily_" + datetime.now().strftime("%Y%m%d_%H%M") + ".json")
        json.dump(rep, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        with conn() as db:
            db.execute("CREATE TABLE IF NOT EXISTS contactsync_log (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, body TEXT)")
            db.execute("INSERT INTO contactsync_log(ts, body) VALUES(?,?)",
                       (rep["end"], json.dumps({"daily": True, **{k: (len(v) if isinstance(v, list) else v) for k, v in rep.items()}}, ensure_ascii=False)))
        os.remove(LOCK)
        print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in rep.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
