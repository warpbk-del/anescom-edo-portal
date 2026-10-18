# Проверка отправки PDF через API ChatApp на тестовый номер (PAY_TEST_PHONES[0]).
# PDF — заказ из Bitrix24 по публичной ссылке портала /b24/order-pdf/<сделка>. Секреты и номер не печатает.
# Запуск: .venv\Scripts\python.exe chatapp_pdf_check.py [ID_сделки]
import sys, time, datetime, re
sys.path.insert(0, r"D:\anescom_edo")
import httpx
from app import config, chatapp
sys.stdout.reconfigure(encoding="utf-8")

deal = sys.argv[1] if len(sys.argv) > 1 else "79531"
url = f"{config.PUBLIC_BASE_URL}/b24/order-pdf/{deal}?k={config.ORDER_PDF_KEY}"
print("база ссылок:", config.PUBLIC_BASE_URL, "| ключ задан:", bool(config.ORDER_PDF_KEY),
      "| тестовых номеров:", len(config.PAY_TEST_PHONES), "| appId:", config.CHATAPP_APP_ID)
t0 = time.time()
try:
    r = httpx.get(url, timeout=60, follow_redirects=True)
    print(f"1) PDF по ссылке: {r.status_code}, {r.headers.get('content-type')}, {len(r.content)} байт, "
          f"начало {r.content[:5]!r}, {time.time() - t0:.1f} с")
    if r.status_code != 200 or not r.content.startswith(b"%PDF"):
        print("   СТОП: ссылка не отдаёт PDF:", r.text[:200]); sys.exit(1)
except Exception as e:
    print("1) СТОП: ссылка недоступна:", type(e).__name__, e); sys.exit(1)
if not config.PAY_TEST_PHONES:
    print("СТОП: PAY_TEST_PHONES пуст"); sys.exit(1)
phone = config.PAY_TEST_PHONES[0]
now = datetime.datetime.now(datetime.timezone.utc)
t0 = time.time()
try:
    js = chatapp.send_file(phone, url, "Zakaz_ANESCOM.pdf", f"Тест API: PDF заказа (сделка {deal})")
    txt = re.sub(r"\d{6,}", "…", str(js))
    print(f"2) {now:%H:%M:%S} UTC ({(now + datetime.timedelta(hours=5)):%H:%M:%S} Алматы) отправка PDF: OK за {time.time() - t0:.1f} с")
    print("   ответ:", txt[:300])
except Exception as e:
    print(f"2) {now:%H:%M:%S} UTC ({(now + datetime.timedelta(hours=5)):%H:%M:%S} Алматы) отправка PDF: ОШИБКА за {time.time() - t0:.1f} с")
    print("  ", re.sub(r"\d{9,}", "…", str(e))[:400])
