# Проверка портала после деплоя (без вывода секретов). Запуск: .venv\Scripts\python.exe deploy\check_v3s2.py
import sys
sys.path.insert(0, r"D:\anescom_edo")
from fastapi.testclient import TestClient
from app import main, config, db
sys.stdout.reconfigure(encoding="utf-8")

c = TestClient(main.app)
h = {"host": "edo.anescom.kz"}
print("landing", c.get("/", headers=h).status_code)
c.cookies.set(main._COOKIE, main._make_cookie())
print("cabinet", c.get("/cabinet", headers=h).status_code)
with db.conn() as con:
    r = con.execute("SELECT id FROM documents WHERE workflow=1 ORDER BY created_at DESC LIMIT 1").fetchone()
    print("doc", r[0], "card", c.get("/cabinet/doc/" + r[0], headers=h).status_code)
    for s in con.execute("SELECT step, role, status, wa_status, substr(wa_detail,1,40) FROM signers "
                         "WHERE document_id=? ORDER BY step", (r[0],)):
        print(tuple(s))
    for e in con.execute("SELECT substr(ts,12,8), kind, substr(detail,1,70) FROM events "
                         "WHERE document_id=? ORDER BY id DESC LIMIT 6", (r[0],)):
        print(tuple(e))
print("PUBLIC_BASE_URL =", config.PUBLIC_BASE_URL, "| SIGN_NOTIFY_MODE =", config.SIGN_NOTIFY_MODE)
