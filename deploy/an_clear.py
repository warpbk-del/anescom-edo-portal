# Очистка данных аналитики на портале перед загрузкой из рабочей базы (копия файла сохраняется рядом).
import shutil, sqlite3, sys, time
sys.stdout.reconfigure(encoding="utf-8")
f = r"D:\anescom_edo\data\analytics.sqlite3"
bk = f + ".bak_" + time.strftime("%Y%m%d_%H%M%S")
shutil.copy2(f, bk)
c = sqlite3.connect(f)
for t in ("an_sales", "an_payments", "an_cashflow", "an_stock", "an_debts", "an_loads", "an_meta"):
    n = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    c.execute(f"DELETE FROM {t}")
    print(t, "удалено", n)
c.commit(); c.execute("VACUUM"); c.close()
print("копия:", bk)
