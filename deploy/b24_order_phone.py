"""Диагностика: найдётся ли сделка Bitrix24 по номеру заказа 1С и есть ли телефон у контакта (телефоны не печатает).
Запуск из D:\\anescom_edo: .venv\\Scripts\\python.exe legacy\\py\\b24_order_phone.py 00НФ-7953"""
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")
from app import b24people as B, config

for no in sys.argv[1:] or ["00НФ-7953"]:
    variants = [no]
    if "-" in no:
        p, n = no.split("-", 1)
        variants += [f"{p}-{n.lstrip('0')}", f"{p}-{n.zfill(6)}"]
    for v in dict.fromkeys(variants):
        try:
            deals = B._b24("crm.deal.list", {"filter": {"%TITLE": v}, "select": ["ID", "TITLE", "CONTACT_ID", "COMPANY_ID"],
                                             "order": {"ID": "DESC"}}) or []
        except Exception as e:
            print(v, "ошибка:", e); continue
        print(v, "сделок:", len(deals), [(d["ID"], d["TITLE"][:60], d.get("CONTACT_ID"), d.get("COMPANY_ID")) for d in deals[:3]])
        for d in deals[:1]:
            if d.get("CONTACT_ID"):
                c = B._b24("crm.contact.get", {"id": d["CONTACT_ID"]}) or {}
                ph = c.get("PHONE") or []
                print("   контакт", c.get("NAME"), c.get("LAST_NAME"), "телефонов:", len(ph), [p.get("VALUE_TYPE") for p in ph])
print("Z2_DEAL_ORDER_FIELD =", config.Z2_DEAL_ORDER_FIELD or "(нет)")
