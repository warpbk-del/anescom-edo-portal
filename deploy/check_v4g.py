# Проверка после деплоя v4g (вход через Bitrix24). Секреты не печатает.
import sys
sys.path.insert(0, r"D:\anescom_edo")
from fastapi.testclient import TestClient
from app import main, config, b24auth, db
sys.stdout.reconfigure(encoding="utf-8")

with TestClient(main.app) as c:
    h = {"host": "edo.anescom.kz"}
    print("B24_DOMAIN:", config.B24_DOMAIN, "| client_id задан:", bool(config.B24_CLIENT_ID),
          "| secret задан:", bool(config.B24_CLIENT_SECRET), "| админы:", config.B24_ADMIN_IDS)
    r = c.get("/cabinet", headers=h)
    print("cabinet (без входа)", r.status_code, "кнопка Битрикс24:", "Войти через Битрикс24" in r.text)
    r = c.get("/b24/app", headers=h, follow_redirects=False)
    print("/b24/app без AUTH_ID ->", r.status_code, r.headers.get("location"))
    r = c.post("/b24/app", headers=h, data={"AUTH_ID": "bad", "DOMAIN": config.B24_DOMAIN}, follow_redirects=False)
    print("/b24/app с неверным AUTH_ID ->", r.status_code, "(ожидаем 401)")
    print("/b24/install", c.get("/b24/install", headers=h).status_code)
    c.cookies.set(main._COOKIE, main._make_cookie())
    print("cabinet (пароль)", c.get("/cabinet", headers=h).status_code, "| dash", c.get("/dash", headers=h).status_code)
with db.conn() as cn:
    print("users:", cn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
          "| access_log:", cn.execute("SELECT COUNT(*) FROM access_log").fetchone()[0])
