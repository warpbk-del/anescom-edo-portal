# Проект 19 (23.10.2026): какие реквизиты у Партнеров/Контрагентов в рабочей базе (из последней диагностики 1С)
# и чей GUID в ORIGIN_ID контактов Б24 — партнёра или контрагента. Только чтение. Итог: D:\anescom_edo\partners_diag.txt
import json, sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8")
c = sqlite3.connect(r"D:\anescom_edo\data\analytics.sqlite3")
out = []
r = c.execute("SELECT ts, body FROM an_meta WHERE body LIKE '%\"catalogs\"%' ORDER BY id DESC LIMIT 1").fetchone()
KEYS = ("Регион", "ИНН", "ИИН", "БИН", "ЮрФиз", "Клиент", "Поставщик", "Менеджер", "Контакт", "Телефон", "Партнер",
        "Вид", "Код", "Наименование", "Родитель", "ГоловнойКонтрагент", "Обособ")
if r:
    j = json.loads(r[1])
    out.append(f"диагностика {r[0]} {j.get('config')} {j.get('computer')}")
    for cat in j.get("catalogs", []):
        if cat.get("name") not in ("Партнеры", "Контрагенты"):
            continue
        out.append(f"== {cat['name']}")
        for a in cat.get("Реквизиты", []):
            if any(k in a for k in KEYS):
                out.append("  " + a[:150])
        for t in cat.get("ТабличныеЧасти", []):
            out.append("  ТЧ " + t[:200])
B = "0e51282f-5e51-11f0-876e-50ebf6b34e1f"  # контакт Б24 25449 Бармин В.В., ORIGIN_ID
for t, col, name in (("an_sales", "client_key", "client"), ("an_payments", "client_key", "client"),
                     ("an_debts", "client_key", "client"), ("an_purchases", "supplier_key", "supplier")):
    try:
        x = c.execute(f"SELECT {name}, COUNT(*) FROM {t} WHERE lower({col})=? GROUP BY {name}", (B,)).fetchall()
        n = c.execute(f"SELECT COUNT(DISTINCT {col}) FROM {t}").fetchone()[0]
        out.append(f"{t}.{col}: Бармин-GUID → {x}; всего ключей {n}")
    except Exception as e:
        out.append(f"{t}: {e}")
open(r"D:\anescom_edo\partners_diag.txt", "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out))
