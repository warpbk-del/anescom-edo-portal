# Проверка вкладки «Товары и группы» на рабочих данных (22.10.2026): итоги по GEZE и пробный PDF/Excel в D:\ANESCOM_Claude.
import sys
from datetime import date
sys.path.insert(0, r"D:\anescom_edo")
from app import itemrep as I, analytics
with analytics.conn() as c:
    for t in ("an_sales", "an_purchases", "an_cost_month", "an_stock"):
        print(t, c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
R = I.build("name", "GEZE", date(2026, 1, 1), date(2026, 10, 22), date(2025, 12, 31))
T = R["T"]
print("позиций", T["n"], "продано", round(T["qs"]), "выручка", round(T["rev"]), "себест", round(T["cost_used"]),
      "прибыль", round(T["margin"]), "маржа", round(T["mpct"] or 0, 1), "остаток", round(T["q1"]), round(T["c1"]))
print([g["group"] for g in R["groups"]])
for t in R["notes"]:
    print("*", t)
open(r"D:\ANESCOM_Claude\test_items_GEZE.pdf", "wb").write(I.pdf(R, "проверка"))
open(r"D:\ANESCOM_Claude\test_items_GEZE.xlsx", "wb").write(I.xlsx(R, "проверка"))
print("ok")
