# Последняя диагностика 1С из базы аналитики: ошибки, счётчики, пример строки долгов.
import json, sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8")
c = sqlite3.connect(r"D:\anescom_edo\data\analytics.sqlite3")
for ts, body in c.execute("SELECT ts, body FROM an_meta ORDER BY id DESC LIMIT 40"):
    j = json.loads(body)
    if j.get("kind") == "diagnostics":
        print(ts, j.get("computer"), j.get("config"))
        print("ошибки:", j.get("test_errors"))
        tc = j.get("test_counts", {})
        print({k: v for k, v in tc.items() if not k.endswith("_пример")})
        print("пример долга:", tc.get("debts_пример"))
        break
