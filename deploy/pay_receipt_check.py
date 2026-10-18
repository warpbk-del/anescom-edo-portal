# Тест уведомления об оплате с реальным чеком ОФД на тестовый номер (PAY_TEST_PHONES[0]).
# Шлёт в портал POST /api/payments/notify так же, как расширение 1С. Секреты и номер не печатает.
# Данные чека — из «Фискальные операции РК» рабочей базы (ПКО, 17.10.2026 13:43:47, 30 ₸, Основная касса).
import sys, time, re
sys.path.insert(0, r"D:\anescom_edo")
import httpx
from app import config
sys.stdout.reconfigure(encoding="utf-8")

body = {
    "doc_key": f"test-receipt-{int(time.time())}",
    "doc_title": "Тест: Приходный кассовый ордер от 17.10.2026",
    "pay_kind": "cash",
    "client_name": "Тест чека",
    "phone": config.PAY_TEST_PHONES[0] if config.PAY_TEST_PHONES else "",
    "amount": 30.0,
    "order_no": "ТЕСТ",
    "check_no": "907346408095",
    "check_datetime": "2026-10-17T13:43:47",
    "rnk": "061804580719",
}
print("режим:", config.PAY_NOTIFY_MODE, "| тестовых номеров:", len(config.PAY_TEST_PHONES))
r = httpx.post("http://127.0.0.1:8096/api/payments/notify", json=body, timeout=60,
               headers={"Authorization": f"Bearer {config.API_TOKEN}"})
js = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"raw": r.text[:300]}
print("HTTP", r.status_code, "| статус:", js.get("status"), "|", re.sub(r"\d{9,}(?!\d)", lambda m: m.group(0) if len(m.group(0)) == 12 else "…", str(js.get("detail", "")))[:200])
print("ссылка на чек:", js.get("receipt_url"))
