"""Проект 19 (24.10.2026, «Да» пользователя 11:28): ежедневная проверка задвоенных товаров в сделках Б24.

Коннектор 1С→Б24 иногда отправляет список товаров заказа дважды — сумма сделки становится вдвое больше заказа 1С.
Проверяются сделки, изменённые за последние DAYS дней (ORIGIN_ID = GUID заказа 1С).
Исправляется ТОЛЬКО строгий случай: каждая строка товара встречается чётное число раз и половина строк даёт ровно
сумму заказа 1С (an_order_clients). Лишние копии удаляются (crm.item.productrow.delete), итог сделки сверяется.
Остальные расхождения сумм — только в отчёт.
Запуск: задача «ANESCOM deal dup daily» (06:30 и 15:30). Отчёт: data\\reports\\deal_dup_daily_YYYYMMDD_HHMM.json.
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from app.analytics import conn  # noqa: E402
from app.b24people import _b24  # noqa: E402

DAYS = 3
LIMIT = 200          # больше исправлений за раз — аномалия: только отчёт
REP = os.path.join(BASE, "data", "reports")


def call(method, params, tries=5):
    for i in range(tries):
        try:
            return _b24(method, params)
        except Exception:  # noqa: BLE001 — лимиты Б24
            if i == tries - 1:
                raise
            time.sleep(2 + 2 * i)


def deals_changed():
    since = (datetime.now(timezone.utc) - timedelta(days=DAYS)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    out, last = [], 0
    while True:
        part = call("crm.deal.list", {"order": {"ID": "ASC"}, "start": -1,
                                      "filter": {">ID": last, ">=DATE_MODIFY": since, "!ORIGIN_ID": ""},
                                      "select": ["ID", "TITLE", "ORIGIN_ID", "OPPORTUNITY", "CLOSED"]}) or []
        out += part
        if len(part) < 50:
            return out
        last = int(part[-1]["ID"])


def key(p):
    return "|".join(str(p.get(k)) for k in ("PRODUCT_ID", "PRODUCT_NAME", "QUANTITY", "PRICE", "DISCOUNT_SUM", "TAX_RATE"))


def main():
    with conn() as c:
        orders = {r["order_key"].lower(): (r["order_no"], float(r["sum"] or 0))
                  for r in c.execute("SELECT order_key, order_no, sum FROM an_order_clients")}
    deals = deals_changed()
    rep = {"ts": datetime.now().isoformat(timespec="seconds"), "checked": len(deals), "no_order": 0, "match": 0,
           "double_found": [], "fixed": [], "fix_failed": [], "other_diff": []}
    todo = []
    for d in deals:
        o = orders.get((d.get("ORIGIN_ID") or "").lower())
        if not o:
            rep["no_order"] += 1
            continue
        opp, one = float(d.get("OPPORTUNITY") or 0), o[1]
        if abs(opp - one) < 1:
            rep["match"] += 1
            continue
        rows = call("crm.deal.productrows.get", {"id": d["ID"]}) or []
        tot = {}
        for p in rows:
            tot[key(p)] = tot.get(key(p), 0) + 1
        half = 0.0
        seen = {}
        for p in rows:
            k = key(p)
            seen[k] = seen.get(k, 0) + 1
            if seen[k] <= tot[k] / 2:
                half += float(p["PRICE"]) * float(p["QUANTITY"])
        if rows and all(v % 2 == 0 for v in tot.values()) and abs(half - one) <= 2:
            rep["double_found"].append(int(d["ID"]))
            todo.append((d, rows, tot, one, o[0]))
        else:
            rep["other_diff"].append({"deal": int(d["ID"]), "order": o[0], "b24": opp, "c1": one})
    if len(todo) > LIMIT:
        rep["stopped"] = f"задвоенных {len(todo)} > {LIMIT} — ничего не менял, проверить вручную"
        todo = []
    for d, rows0, tot, one, no in todo:
        target = len(rows0) // 2
        for _ in range(4):
            rows = call("crm.deal.productrows.get", {"id": d["ID"]}) or []
            if len(rows) <= target:
                break
            seen = {}
            for p in rows:
                k = key(p)
                seen[k] = seen.get(k, 0) + 1
                if seen[k] > tot.get(k, 0) / 2:
                    try:
                        call("crm.item.productrow.delete", {"id": p["ID"]})
                    except Exception:  # noqa: BLE001
                        pass
        opp = float((call("crm.deal.get", {"id": d["ID"]}) or {}).get("OPPORTUNITY") or 0)
        (rep["fixed"] if abs(opp - one) <= 2 else rep["fix_failed"]).append(
            {"deal": int(d["ID"]), "order": no, "rows_before": len(rows0), "sum_now": opp, "sum_1c": one})
    name = os.path.join(REP, f"deal_dup_daily_{datetime.now():%Y%m%d_%H%M}.json")
    with open(name, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in rep.items()}, ensure_ascii=True))


if __name__ == "__main__":
    main()
