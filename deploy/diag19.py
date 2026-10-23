# Проект 19: итог последней диагностики 1С по видам partners / order_clients (только чтение).
import json, sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8")
c = sqlite3.connect(r"D:\anescom_edo\data\analytics.sqlite3")
ts, body = c.execute("SELECT ts, body FROM an_meta WHERE body LIKE '%diagnostics%' ORDER BY id DESC LIMIT 1").fetchone()
j = json.loads(body)
t = j.get("test_counts", {})
print(ts, j.get("computer"), j.get("config"))
print("ошибки:", [e[:200] for e in j.get("test_errors", [])])
for k in ("partners", "order_clients"):
    print(k, t.get(k), json.dumps(t.get(k + "_пример"), ensure_ascii=False)[:600])
