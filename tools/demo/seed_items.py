"""Демо для вкладки «Товары и группы»: группа GEZE по реальным итогам анализа 22.10.2026 (tools/demo/geze)
кладётся в an_cost_month / an_purchases / an_sales (со скидками) / an_stock. Аргументы: папка данных, geze2.json."""
import json, os, sqlite3, sys
sys.path.insert(0, ".")
from app import analytics
DATA, SRC = sys.argv[1], sys.argv[2]
A = sqlite3.connect(os.path.join(DATA, "analytics.sqlite3"))
A.executescript(analytics._schema())
for base, cols, nums, dated in analytics.KINDS.values():   # миграция колонок, как в analytics.init()
    have = {r[1] for r in A.execute(f"PRAGMA table_info({base})")}
    for col in cols:
        if col not in have:
            A.execute(f"ALTER TABLE {base} ADD COLUMN {col} {'REAL' if col in nums else 'TEXT'}")
d = json.load(open(SRC))
grp = "Доводчики и фурнитура GEZE"
for i, x in enumerate(d):
    key = f"GEZE{i}"; name = x["name"]
    A.execute("DELETE FROM an_cost_month WHERE item_key=?", (key,))
    # остаток на 31.12.2025 — строка декабря; приход 2026 — март и июнь пополам
    A.execute("INSERT INTO an_cost_month (date,org,item,item_key,item_group,qty_beg,cost_beg,qty_in,cost_in,extra_in,qty_out,cost_out,qty_end,cost_end) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
              ("2025-12-01", "ТОО ANESCOM", name, key, grp, x["q0"], x["c0"], 0, 0, 0, 0, 0, x["q0"], x["c0"]))
    if x["qin"]:
        extra = x["cin"] - x["pin"]
        A.execute("INSERT INTO an_cost_month (date,org,item,item_key,item_group,qty_beg,cost_beg,qty_in,cost_in,extra_in,qty_out,cost_out,qty_end,cost_end) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  ("2026-03-01", "ТОО ANESCOM", name, key, grp, x["q0"], x["c0"], x["qin"], x["pin"], extra, 0, 0, x["q0"] + x["qin"], x["c0"] + x["cin"]))
        A.execute("INSERT INTO an_purchases (date,doc_key,doc_no,org,supplier,supplier_key,warehouse,item,item_key,item_group,qty,currency,sum_cur,sum) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  ("2026-03-10", f"P{i}", f"ПТ-{i:04d}", "ТОО ANESCOM", "GEZE GmbH", "geze", "Склад Актобе", name, key, grp, x["qin"], "EUR", x["pin"] / 600, x["pin"]))
    if x["qs"]:
        A.execute("INSERT INTO an_sales (date,doc_key,doc_no,org,branch,warehouse,manager,client,client_key,item,item_key,item_group,qty,sum,cost,disc_auto,disc_manual,vat) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  ("2026-06-15", f"S{i}", f"00НФ-{i:05d}", "ТОО ANESCOM", "Актобе", "Склад Актобе", "Ахметов Ерлан", "ТОО «СтройМастер»", "c1",
                   name, key, grp, x["qs"], x["rev"], x["scost"], x["disc"], 0, 0))
    if x["q1"]:
        A.execute("INSERT INTO an_stock (org,branch,warehouse,item,item_key,item_group,unit,qty,cost_sum,last_sale,sold_30,sold_90) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                  ("", "Актобе", "Склад Актобе", name, key, grp, "шт", x["q1"], x["c1"], "2026-06-15" if x["qs"] else "", 0, 0))
A.commit(); print("ok", len(d))
