# Проверка POST /v1/tokens ChatApp с сервера (для поддержки ChatApp). Секреты не печатает.
# Запуск: .venv\Scripts\python.exe chatapp_token_check.py
import sys, time, datetime, re
sys.path.insert(0, r"D:\anescom_edo")
import httpx
from app import config
sys.stdout.reconfigure(encoding="utf-8")

url = "https://api.chatapp.online/v1/tokens"
body = {"email": config.CHATAPP_EMAIL, "password": config.CHATAPP_PASSWORD, "appId": config.CHATAPP_APP_ID}
print("email задан:", bool(config.CHATAPP_EMAIL), "| пароль задан:", bool(config.CHATAPP_PASSWORD), "| appId:", config.CHATAPP_APP_ID)
for i in (1, 2):
    t0 = time.time()
    now = datetime.datetime.now(datetime.timezone.utc)
    try:
        r = httpx.post(url, timeout=60, headers={"Lang": "ru", "Accept": "application/json"}, json=body)
        txt = re.sub(r'("(?:accessToken|refreshToken)"\s*:\s*")[^"]+', r'\1***', r.text)
        print(f"#{i} {now:%Y-%m-%d %H:%M:%S} UTC ({(now + datetime.timedelta(hours=5)):%H:%M:%S} Алматы) "
              f"-> {r.status_code} за {time.time() - t0:.1f} с; x-request-id={r.headers.get('x-request-id', '-')}")
        print("   ответ:", txt[:300])
    except Exception as e:
        print(f"#{i} {now:%H:%M:%S} UTC -> ошибка {type(e).__name__}: {e} за {time.time() - t0:.1f} с")
    time.sleep(3)
try:
    import socket
    print("IP api.chatapp.online:", socket.gethostbyname("api.chatapp.online"))
    print("внешний IP сервера:", httpx.get("https://api.ipify.org", timeout=10).text)
except Exception as e:
    print("IP: ошибка", e)
