# Проверка v4q: «Деньги и расходы», «Менеджер» с выбором.
import sys, re
sys.path.insert(0, r"D:\anescom_edo")
from fastapi.testclient import TestClient
from app import main, b24auth, db, access
sys.stdout.reconfigure(encoding="utf-8")
h = {"host": "edo.anescom.kz"}
def t(x):
    m = re.search(r'<h1 class="v3-h1">([^<]+)', x); return m.group(1).strip() if m else "?"
with db.conn() as cn:
    pick = {r["role"]: r["b24_id"] for r in cn.execute("SELECT b24_id, role FROM users WHERE active=1")}
with TestClient(main.app) as c:
    c.cookies.set(b24auth.COOKIE, b24auth.make_session(355))
    for u in ("/dash/money", "/dash/money?p=year", "/dash/money?p=today", "/dash/mgr", "/dash/mgr?p=year", "/dash", "/dash/acc", "/dash/stock"):
        r = c.get(u, headers=h); print(u, r.status_code, t(r.text))
    for role in ("accountant", "manager", "rop"):
        if role in pick:
            c.cookies.set(access.AS_COOKIE, str(pick[role]))
            print("как", role, "money", t(c.get("/dash/money", headers=h).text), "| mgr", t(c.get("/dash/mgr", headers=h).text))
    c.cookies.delete(access.AS_COOKIE)
