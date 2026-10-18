# Проверка дашборда после деплоя v4e (свои компании отдельно). Без вывода секретов.
# Запуск: .venv\Scripts\python.exe check_v4e.py
import sys
sys.path.insert(0, r"D:\anescom_edo")
from fastapi.testclient import TestClient
from app import main, config
sys.stdout.reconfigure(encoding="utf-8")

c = TestClient(main.app)
h = {"host": "edo.anescom.kz"}
c.cookies.set(main._COOKIE, main._make_cookie())
print("свои компании:", config.INTERNAL_CLIENTS)
print("cabinet", c.get("/cabinet", headers=h).status_code)
for p in ("today", "month", "year"):
    r = c.get("/dash?p=" + p, headers=h)
    t = r.text
    i = t.find("Нам должны</span>")
    print("dash", p, r.status_code, "блок «Свои компании»:", "Свои компании</h2>" in t,
          t[i:i + 170].replace("\n", " ") if i > 0 else "")
r = c.get("/dash/branches?p=month", headers=h)
print("branches", r.status_code, "Сравнение филиалов" in r.text)
