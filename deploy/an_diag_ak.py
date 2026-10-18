# Последняя диагностика 1С (любой базы): источник, ошибки, счётчики, пример prod_out.
import json, sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8")
c = sqlite3.connect(r"D:\anescom_edo\data\analytics.sqlite3")
n = 0
for ts, body in c.execute("SELECT ts, body FROM an_meta ORDER BY id DESC LIMIT 60"):
    j = json.loads(body)
    if j.get("kind") != "diagnostics":
        continue
    print(ts, j.get("source"), j.get("computer"), j.get("config"))
    print("ошибки:", j.get("test_errors"))
    tc = j.get("test_counts", {})
    print({k: v for k, v in tc.items() if not k.endswith("_пример")})
    print("prod_out пример:", tc.get("prod_out_пример"))
    n += 1
    if n >= 2:
        break
for t in ("an_prod_out_avtokomp", "an_stock_avtokomp", "an_sales_avtokomp"):
    try:
        print(t, c.execute(f"SELECT COUNT(*), MIN(date), MAX(date) FROM {t}").fetchone() if t != "an_stock_avtokomp" else c.execute(f"SELECT COUNT(*) FROM {t}").fetchone())
    except Exception as e:
        print(t, e)
