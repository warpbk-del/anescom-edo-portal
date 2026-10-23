# Проект 19: последние приёмы аналитики и объём partners / order_clients (только чтение).
import sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8")
c = sqlite3.connect(r"D:\anescom_edo\data\analytics.sqlite3")
for r in c.execute("SELECT ts, kind, rows, ip FROM an_loads ORDER BY rowid DESC LIMIT 14"):
    print(r)
for t in ("an_partners", "an_order_clients"):
    try:
        print(t, c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
    except Exception as e:
        print(t, e)
print(c.execute("SELECT rec, COUNT(*), SUM(sold='1'), SUM(bought='1') FROM an_partners GROUP BY rec").fetchall())
