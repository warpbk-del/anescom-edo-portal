# Смарт-процессы Bitrix24: список, поля и стадии процесса доставок, пример карточек (для кабинета водителя).
import json, sys
sys.path.insert(0, r"D:\anescom_edo")
sys.stdout.reconfigure(encoding="utf-8")
from app import b24people as b

types = b._b24("crm.type.list", {}) or {}
types = types.get("types", types) if isinstance(types, dict) else types
for t in types:
    print("ТИП", t.get("entityTypeId"), "|", t.get("title"), "| id", t.get("id"))
want = [t for t in types if any(x in (t.get("title") or "").lower() for x in ("достав", "водит", "логист", "рейс", "отгруз"))]
for t in want or types[:3]:
    et = t["entityTypeId"]
    print("\n=== ", et, t.get("title"))
    f = b._b24("crm.item.fields", {"entityTypeId": et}) or {}
    for k, v in (f.get("fields") or {}).items():
        print("  поле", k, "|", v.get("title"), "|", v.get("type"), "| список" if v.get("items") else "",
              json.dumps([i.get("VALUE") for i in (v.get("items") or [])][:8], ensure_ascii=False) if v.get("items") else "")
    for cat in (b._b24("crm.category.list", {"entityTypeId": et}) or {}).get("categories", []):
        st = b._b24("crm.status.list", {"filter": {"ENTITY_ID": f"DYNAMIC_{et}_STAGE_{cat['id']}"}}) or []
        print("  воронка", cat["id"], cat.get("name"), "→", [(s["STATUS_ID"], s["NAME"]) for s in st])
    items = (b._b24("crm.item.list", {"entityTypeId": et, "order": {"id": "DESC"}, "select": ["*"], "limit": 3}) or {}).get("items", [])
    for it in items[:3]:
        print("  ПРИМЕР", json.dumps({k: v for k, v in it.items() if v not in (None, "", [], 0, "N")}, ensure_ascii=False)[:1500])
