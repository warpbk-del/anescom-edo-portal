# Проверка закрытия сделок Bitrix24 (23.10.2026): счётчики последней диагностики 1С и последние запуски deals_close.
import json, sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8")
c = sqlite3.connect(r"D:\anescom_edo\data\analytics.sqlite3")
r = c.execute("SELECT ts, body FROM an_meta WHERE body LIKE '%diagnostics%' ORDER BY id DESC LIMIT 1").fetchone()
if r:
    j = json.loads(r[1])
    t = j.get("test_counts", {})
    print("диагностика", r[0], j.get("computer"), "ошибки:", j.get("test_errors"))
    print({k: v for k, v in t.items() if "deals" in k})
for ts, mode, body in c.execute("SELECT ts, mode, body FROM b24_deal_sync_log ORDER BY id DESC LIMIT 3"):
    b = json.loads(body)
    print(ts, mode, {k: (v if not isinstance(v, list) else (len(v), v[:10])) for k, v in b.items()})
