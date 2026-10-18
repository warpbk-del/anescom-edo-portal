# Из последней диагностики 1С: регистры сведений (Фискальные операции РК, переработка) и документы переработчика.
import json, sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8")
c = sqlite3.connect(r"D:\anescom_edo\data\analytics.sqlite3")
for ts, body in c.execute("SELECT ts, body FROM an_meta ORDER BY id DESC LIMIT 60"):
    j = json.loads(body)
    if j.get("kind") != "diagnostics":
        continue
    print(ts, j.get("computer"), j.get("config"))
    for r in j.get("info_registers") or []:
        print("\n== РС", r.get("name"))
        for k in ("Измерения", "Ресурсы", "Реквизиты"):
            for f in r.get(k) or []:
                print("  ", k[:3], f)
    for d in j.get("documents") or []:
        if "Переработ" in d.get("name", ""):
            print("\n== Док", d.get("name"), "есть" if d.get("exists") else "НЕТ")
            for k in ("Реквизиты", "ТабличныеЧасти"):
                for f in d.get(k) or []:
                    print("  ", k[:3], f)
    for r in j.get("registers") or []:
        if "Переработ" in r.get("name", ""):
            print("\n== РН", r.get("name"), r.get("Измерения"), r.get("Ресурсы"))
    if "info_registers" not in j:
        print("в этой диагностике нет info_registers — расширение ещё старое")
    break
