# Проверка дашборда после деплоя (без вывода секретов). Запуск: .venv\Scripts\python.exe check_v4b.py
import sys
sys.path.insert(0, r"D:\anescom_edo")
from fastapi.testclient import TestClient
from app import main
sys.stdout.reconfigure(encoding="utf-8")

c = TestClient(main.app)
h = {"host": "edo.anescom.kz"}
c.cookies.set(main._COOKIE, main._make_cookie())
print("cabinet", c.get("/cabinet", headers=h).status_code)
for p in ("today", "week", "month", "year"):
    r = c.get("/dash?p=" + p, headers=h)
    t = r.text
    i = t.find("Выручка</span>")
    print("dash", p, r.status_code, "Компания" in t, t[i:i + 160].replace("\n", " ") if i > 0 else "")
for p in ("month", "year"):
    r = c.get("/dash/branches?p=" + p, headers=h)
    print("branches", p, r.status_code, "Сравнение филиалов" in r.text)
