# Проверка v4n: вкладка «Бухгалтер», отчёт для печати, склад — «есть на других складах».
import sys, re
sys.path.insert(0, r"D:\anescom_edo")
from fastapi.testclient import TestClient
from app import main, b24auth, db, access
sys.stdout.reconfigure(encoding="utf-8")
h = {"host": "edo.anescom.kz"}
with db.conn() as cn:
    pick = {r["role"]: r["b24_id"] for r in cn.execute("SELECT b24_id, role FROM users WHERE active=1 ORDER BY name DESC")}
with TestClient(main.app) as c:
    c.cookies.set(b24auth.COOKIE, b24auth.make_session(355))
    r = c.get("/dash/acc", headers=h); print("acc", r.status_code, "Дебиторка по филиалам" in r.text, len(r.text))
    r = c.get("/dash/acc/report?p=month", headers=h); print("report", r.status_code, "Отчёт готов к печати" in r.text, len(r.text))
    r = c.get("/dash/stock", headers=h); print("stock", r.status_code, "Есть на других складах" in r.text)
    print("csv", c.get("/dash/stock/order.csv", headers=h).text.splitlines()[0][:120])
    for role in ("accountant", "storekeeper", "manager"):
        if role in pick:
            c.cookies.set(access.AS_COOKIE, str(pick[role]))
            r = c.get("/dash/acc", headers=h)
            print("как", role, "/dash/acc", r.status_code, "Нет доступа" in r.text and "нет доступа" or "есть доступ")
    c.cookies.delete(access.AS_COOKIE)
