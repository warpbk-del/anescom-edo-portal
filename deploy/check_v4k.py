# Проверка v4k (видимость по ролям): админ 355 смотрит «как» по одному сотруднику каждой роли.
import sys, re
sys.path.insert(0, r"D:\anescom_edo")
from fastapi.testclient import TestClient
from app import main, b24auth, db, access
sys.stdout.reconfigure(encoding="utf-8")
h = {"host": "edo.anescom.kz"}
with db.conn() as cn:
    pick = {}
    for r in cn.execute("SELECT b24_id, name, role FROM users WHERE active=1 ORDER BY name"):
        pick.setdefault(r["role"], (r["b24_id"], r["name"]))
with TestClient(main.app) as c:
    c.cookies.set(b24auth.COOKIE, b24auth.make_session(355))
    def show(label):
        r = c.get("/cabinet?view=all", headers=h)
        n = re.search(r"Все документы <span class=\"n\">(\d+)", r.text)
        d = c.get("/dash", headers=h)
        what = "компания" if "Компания" in d.text and "Мои продажи" not in d.text else ("мои продажи" if "Мои продажи" in d.text else "заглушка")
        print(f"{label:38} кабинет {r.status_code} документов {n.group(1) if n else '?'} | аналитика {d.status_code} {what}"
              f" | филиалы {c.get('/dash/branches', headers=h).status_code} | роли {c.get('/cabinet/roles', headers=h, follow_redirects=False).status_code}")
    show("админ (сам)")
    for role, (uid, name) in pick.items():
        if role == "admin":
            continue
        c.cookies.set(access.AS_COOKIE, str(uid))
        show(f"как {role}: {name}")
    c.cookies.delete(access.AS_COOKIE)
with db.conn() as cn:
    for r in cn.execute("SELECT * FROM users WHERE role='manager' AND active=1"):
        print("менеджер", r["name"], "→ 1С:", access.manager_1c_name(dict(r)) or "НЕ НАЙДЕН")
