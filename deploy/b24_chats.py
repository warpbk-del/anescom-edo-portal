# Чаты, видимые вебхуку Bitrix24 (для DEBT_CHAT_ID), и сопоставление менеджеров с 1С.
import sys
sys.path.insert(0, r"D:\anescom_edo")
sys.stdout.reconfigure(encoding="utf-8")
from app import debtweek, db, access
for m, p in (("im.search.chat.list", {"FIND": "DEBT"}), ("im.search.chat.list", {"FIND": "ANESCOM"}), ("im.recent.list", {"SKIP_DIALOG": "Y", "SKIP_OPENLINES": "Y"})):
    try:
        res = debtweek._hook(m, p)
        items = res.get("items", res) if isinstance(res, dict) else res
        print(m, p, "→", len(items or []))
        for it in (items or [])[:40]:
            ch = it.get("chat") if isinstance(it.get("chat"), dict) else it
            print("   ", it.get("type", ""), ch.get("id"), "|", ch.get("name") or ch.get("title") or it.get("title"))
    except Exception as e:
        print(m, "ошибка:", e)
with db.conn() as c:
    for u in c.execute("SELECT * FROM users WHERE role='manager'"):
        print("менеджер", u["name"], "→", access.manager_1c_name(dict(u)) or "НЕ НАЙДЕН")
