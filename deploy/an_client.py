# Что пришло из 1С по клиенту: долги, продажи, оплаты. Запуск: python an_client.py "Диаман"
import sys, sqlite3
sys.stdout.reconfigure(encoding="utf-8")
q = "%" + (sys.argv[1] if len(sys.argv) > 1 else "Диаман") + "%"
c = sqlite3.connect(r"D:\anescom_edo\data\analytics.sqlite3")
c.row_factory = sqlite3.Row
c.create_function("LOW", 1, lambda s: (s or "").lower())
ql = q.lower()
print("== долги (an_debts)")
for r in c.execute("SELECT org, client, manager, debt, prepay FROM an_debts WHERE LOW(client) LIKE ?", (ql,)):
    print("  ", dict(r))
print("== продажи (an_sales) по документам")
for r in c.execute("SELECT org, doc_no, MIN(date) d, SUM(sum) s FROM an_sales WHERE LOW(client) LIKE ? GROUP BY org, doc_no ORDER BY d", (ql,)):
    print("  ", dict(r))
print("== оплаты (an_payments)")
for r in c.execute("SELECT org, date, doc_no, kind, sum FROM an_payments WHERE LOW(client) LIKE ? ORDER BY date", (ql,)):
    print("  ", dict(r))
print("== итоги по всем: долг", c.execute("SELECT ROUND(SUM(debt)), ROUND(SUM(prepay)), COUNT(*) FROM an_debts").fetchone())
print("== последняя загрузка долгов", c.execute("SELECT ts, rows FROM an_loads WHERE kind='debts' ORDER BY id DESC LIMIT 1").fetchone())
# клиенты с долгом, но без единой продажи
n = c.execute("""SELECT COUNT(*), ROUND(SUM(d.debt)) FROM an_debts d WHERE d.debt>0 AND NOT EXISTS
                 (SELECT 1 FROM an_sales s WHERE s.client_key=d.client_key)""").fetchone()
print("== клиентов с долгом без продаж в выгрузке:", n)
