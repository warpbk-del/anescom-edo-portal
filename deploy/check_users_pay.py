# Пользователи Bitrix24 и журнал доступа; последние уведомления об оплате. Телефоны не печатает.
import sys, sqlite3
sys.stdout.reconfigure(encoding="utf-8")
c = sqlite3.connect(r"D:\anescom_edo\data\edo.sqlite3")
c.row_factory = sqlite3.Row
for r in c.execute("SELECT b24_id, name, position, dept_names, role, role_suggest, last_login FROM users"):
    print("user", dict(r))
for r in c.execute("SELECT ts, b24_id, name, action, ip, detail FROM access_log ORDER BY id DESC LIMIT 6"):
    print("log", dict(r))
try:
    for r in c.execute("SELECT created_at, doc_title, pay_kind, amount, status, detail, receipt_url IS NOT NULL AND receipt_url<>'' AS has_check "
                       "FROM pay_notifications ORDER BY created_at DESC LIMIT 8"):
        print("pay", dict(r))
except Exception as e:
    print("pay: ", e)
