# Совпадают ли ключи клиентов в долгах, продажах и оплатах (быстро, через множества).
import sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8")
c = sqlite3.connect(r"D:\anescom_edo\data\analytics.sqlite3")
q = lambda s, a=(): c.execute(s, a).fetchall()
n = lambda s: (s or "").strip().upper()
dk = q("SELECT client_key, client FROM an_debts")
sk = set(x for (x,) in q("SELECT DISTINCT client_key FROM an_sales"))
sn = set(n(x) for (x,) in q("SELECT DISTINCT client FROM an_sales"))
pk = set(x for (x,) in q("SELECT DISTINCT client_key FROM an_payments"))
pn = set(n(x) for (x,) in q("SELECT DISTINCT client FROM an_payments"))
print("долгов", len(dk), "| ключ в продажах", sum(k in sk for k, _ in dk), "| имя в продажах", sum(n(m) in sn for _, m in dk),
      "| ключ в оплатах", sum(k in pk for k, _ in dk), "| имя в оплатах", sum(n(m) in pn for _, m in dk))
for t in ("an_debts", "an_sales", "an_payments"):
    print(t, q(f"SELECT client, client_key FROM {t} WHERE client LIKE ? LIMIT 1", ("%MORROW%",)))
print("продажи:", q("SELECT MIN(date), MAX(date), COUNT(*), SUM(branch='') FROM an_sales"))
