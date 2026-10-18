# Совпадают ли ключи клиентов в долгах, продажах и оплатах.
import sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8")
c = sqlite3.connect(r"D:\anescom_edo\data\analytics.sqlite3")
q = lambda s, a=(): c.execute(s, a).fetchall()
print("долгов:", q("SELECT COUNT(*), COUNT(DISTINCT client_key) FROM an_debts"))
print("ключ есть в продажах:", q("SELECT COUNT(*) FROM an_debts d WHERE EXISTS (SELECT 1 FROM an_sales s WHERE s.client_key=d.client_key)"))
print("имя есть в продажах:", q("SELECT COUNT(*) FROM an_debts d WHERE EXISTS (SELECT 1 FROM an_sales s WHERE s.client=d.client)"))
print("ключ есть в оплатах:", q("SELECT COUNT(*) FROM an_debts d WHERE EXISTS (SELECT 1 FROM an_payments p WHERE p.client_key=d.client_key)"))
for t in ("an_debts", "an_sales", "an_payments"):
    print(t, q(f"SELECT client, client_key FROM {t} WHERE client LIKE ? LIMIT 2", ("%MORROW%",)))
print("продажи: даты", q("SELECT MIN(date), MAX(date), COUNT(*) FROM an_sales"))
print("продажи без филиала:", q("SELECT COUNT(*) FROM an_sales WHERE branch=''"))
print("филиалы:", q("SELECT branch, COUNT(*) FROM an_sales GROUP BY branch"))
