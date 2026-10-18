# Сводка по данным аналитики (без секретов). Запуск: .venv\Scripts\python.exe an_check.py
import sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8")
c = sqlite3.connect(r"D:\anescom_edo\data\analytics.sqlite3")
print("месяц | выручка | себестоимость | строк с cost<0")
for r in c.execute("SELECT substr(date,1,7), ROUND(SUM(sum)), ROUND(SUM(cost)), SUM(cost<0) FROM an_sales GROUP BY 1 ORDER BY 1 DESC LIMIT 9"):
    print(r)
print("крупнейшие |cost| в июле 2025:")
for r in c.execute("SELECT date, doc_no, substr(item,1,30), qty, sum, cost FROM an_sales WHERE date LIKE '2025-07%' ORDER BY ABS(cost) DESC LIMIT 5"):
    print(r)
print("долги: всего", c.execute("SELECT ROUND(SUM(debt)), ROUND(SUM(prepay)), COUNT(*) FROM an_debts").fetchone())
for r in c.execute("SELECT substr(client,1,30), ROUND(debt) FROM an_debts ORDER BY debt DESC LIMIT 5"):
    print(r)
