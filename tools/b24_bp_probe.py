"""Разведка бизнес-процессов ленты Bitrix24 (6н, заявки на оплату). Запуск из D:\\anescom_edo:
.venv\\Scripts\\python.exe tools\\b24_bp_probe.py   — печатает списки процессов, поля «оплат…» и 3 примера."""
import json, sys
sys.path.insert(0, ".")
import httpx
from app import config
H = config.B24_WEBHOOK
sys.stdout.reconfigure(encoding="utf-8")


def call(m, p):
    js = httpx.post(f"{H}/{m}.json", json=p, timeout=30).json()
    if "error" in js:
        return {"_err": js.get("error_description") or js["error"]}
    return js


ls = call("lists.get", {"IBLOCK_TYPE_ID": "bitrix_processes"})
if "_err" in ls:
    print("lists.get:", ls["_err"]); sys.exit()
for l in ls.get("result", []):
    print(f"процесс {l['ID']}: {l['NAME']}")
for l in ls.get("result", []):
    if "оплат" not in l["NAME"].lower() and "расход" not in l["NAME"].lower():
        continue
    iid = l["ID"]
    f = call("lists.field.get", {"IBLOCK_TYPE_ID": "bitrix_processes", "IBLOCK_ID": iid}).get("result", {})
    print(f"== {l['NAME']} (ID {iid}) поля:")
    for k, v in f.items():
        extra = ""
        if v.get("DISPLAY_VALUES_FORM"):
            extra = " варианты: " + "; ".join(list(v["DISPLAY_VALUES_FORM"].values())[:12])
        print(f"  {k} | {v.get('NAME')} | {v.get('TYPE')}{extra}")
    e = call("lists.element.get", {"IBLOCK_TYPE_ID": "bitrix_processes", "IBLOCK_ID": iid,
                                    "ELEMENT_ORDER": {"ID": "DESC"}})
    print(f"  заявок всего: {e.get('total')}")
    for x in (e.get("result") or [])[:3]:
        print("  пример:", json.dumps(x, ensure_ascii=False)[:700])
