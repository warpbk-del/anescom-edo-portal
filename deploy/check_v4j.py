# Проверка v4j: панель с именем, страница ролей (под сессией админа 355), загрузка сотрудников из Bitrix24.
import sys
sys.path.insert(0, r"D:\anescom_edo")
from fastapi.testclient import TestClient
from app import main, b24auth, db
sys.stdout.reconfigure(encoding="utf-8")
h = {"host": "edo.anescom.kz"}
with TestClient(main.app) as c:
    c.cookies.set(b24auth.COOKIE, b24auth.make_session(355))
    r = c.get("/cabinet", headers=h); print("cabinet", r.status_code, "имя в панели:", "Болат" in r.text, "| ссылка Роли:", "Роли и доступ" in r.text)
    r = c.get("/dash", headers=h); print("dash", r.status_code, "имя:", "Болат" in r.text)
    r = c.get("/cabinet/roles", headers=h); print("roles", r.status_code)
    if "--sync" in sys.argv:
        r = c.post("/cabinet/roles/sync", headers=h, follow_redirects=False); print("sync ->", r.headers.get("location"))
with db.conn() as cn:
    print("users:", cn.execute("SELECT COUNT(*) FROM users").fetchone()[0])
    for row in cn.execute("SELECT role, COUNT(*) n FROM users GROUP BY role ORDER BY n DESC"):
        print("  ", row[0], row[1])
