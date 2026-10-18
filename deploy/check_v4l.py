# Проверка v4l: вкладки «Склады и закупки» / «Мой склад», заказ поставщику CSV.
import sys, re
sys.path.insert(0, r"D:\anescom_edo")
from fastapi.testclient import TestClient
from app import main, b24auth, db, access
sys.stdout.reconfigure(encoding="utf-8")
h = {"host": "edo.anescom.kz"}
with db.conn() as cn:
    pick = {}
    for r in cn.execute("SELECT b24_id, name, role, dept_names FROM users WHERE active=1 ORDER BY name"):
        pick.setdefault(r["role"], (r["b24_id"], r["name"], r["dept_names"]))
def t(html):
    m = re.search(r'<h1 class="v3-h1">([^<]+)', html); return m.group(1).strip() if m else "?"
with TestClient(main.app) as c:
    c.cookies.set(b24auth.COOKIE, b24auth.make_session(355))
    r = c.get("/dash/stock", headers=h)
    print("админ /dash/stock", r.status_code, t(r.text), "| дозаказ:", re.search(r"Дозаказать</span>\s*<span class=\"v\">(\d+)", r.text).group(1) if "Дозаказать</span>" in r.text else "?")
    r = c.get("/dash/stock/order.csv", headers=h)
    print("CSV", r.status_code, len(r.text.splitlines()) - 1, "строк", r.headers.get("content-disposition"))
    for role in ("storekeeper", "purchaser", "manager", "staff"):
        if role not in pick: continue
        uid, name, dn = pick[role]
        c.cookies.set(access.AS_COOKIE, str(uid))
        r = c.get("/dash/stock", headers=h)
        r2 = c.get("/dash", headers=h, follow_redirects=False)
        print(f"как {role} {name} ({dn}): /dash/stock {r.status_code} «{t(r.text)}» | /dash -> {r2.status_code} {r2.headers.get('location') or t(r2.text)}")
    c.cookies.delete(access.AS_COOKIE)
