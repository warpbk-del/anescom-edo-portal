# Проверка v4s: склад/закупки, отчёты PDF/Excel, Excel заказа, дебиторка, чат DEBT.
import sys, re
sys.path.insert(0, r"D:\anescom_edo")
from fastapi.testclient import TestClient
from app import main, b24auth, db, access, debtweek
sys.stdout.reconfigure(encoding="utf-8")
h = {"host": "edo.anescom.kz"}
def t(r):
    if "html" not in r.headers.get("content-type", ""):
        return f"{len(r.content)} байт"
    m = re.search(r'<h1[^>]*>([^<]+)', r.text); return m.group(1).strip()[:40] if m else r.text[:80]
with db.conn() as cn:
    pick = {r["role"]: r["b24_id"] for r in cn.execute("SELECT b24_id, role FROM users WHERE active=1")}
urls = ["/dash", "/dash/stock", "/dash/purchase", "/dash/report?tab=company", "/dash/report?tab=company&fmt=xlsx",
        "/dash/report?tab=branches&fmt=xlsx", "/dash/report?tab=stock", "/dash/report?tab=purchase&fmt=xlsx",
        "/dash/report?tab=money&fmt=xlsx", "/dash/report?tab=acc&fmt=xlsx", "/dash/purchase/order.xlsx?kind=buy",
        "/dash/purchase/order.xlsx?kind=move", "/dash/debtweek", "/dash/debtweek.xlsx"]
with TestClient(main.app) as c:
    c.cookies.set(b24auth.COOKIE, b24auth.make_session(355))
    for u in urls:
        r = c.get(u, headers=h); print(r.status_code, u, t(r))
    for role in ("manager", "storekeeper", "purchaser", "accountant"):
        if role in pick:
            c.cookies.set(access.AS_COOKIE, str(pick[role]))
            out = []
            for u in ("/dash", "/dash/stock", "/dash/purchase", "/dash/report?tab=stock&fmt=xlsx", "/dash/purchase/order.xlsx?kind=buy"):
                r = c.get(u, headers=h); out.append(f"{u.split('/')[-1][:18]}={r.status_code}:{t(r)[:22]}")
            print("как", role, " | ".join(out))
    c.cookies.delete(access.AS_COOKIE)
print("менеджеры:", [(u["name"], access.manager_1c_name(dict(u))) for u in db.conn().__enter__().execute("SELECT * FROM users WHERE role='manager'")])
try:
    print("чат:", debtweek.find_chat())
except Exception as e:
    print("чат: ошибка", e)
