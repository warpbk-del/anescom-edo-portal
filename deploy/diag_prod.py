# Поля документов/регистров переработчика из последней диагностики рабочей базы (для вкладки «Производство АВТОКОМП»).
import json, re, sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8")
c = sqlite3.connect(r"D:\anescom_edo\data\analytics.sqlite3")
want = sys.argv[1] if len(sys.argv) > 1 else "WIN"
for ts, body in c.execute("SELECT ts, body FROM an_meta WHERE body LIKE '%\"diagnostics\"%' ORDER BY id DESC"):
    d = json.loads(body)
    if want.lower() in (d.get("computer") or "").lower():
        break
else:
    sys.exit("нет диагностики " + want)
print(ts, d.get("computer"), d.get("config"))
nm = lambda xs: ", ".join(re.split(r"[ «]", x, 1)[0] for x in xs or [])
objs = [x for x in d.get("documents", []) if "Переработ" in x["name"]]
objs += [x for x in d.get("registers", []) if "Переработ" in x["name"]]
objs += [x for x in d.get("info_registers", []) if "Переработ" in x["name"]]
for o in objs:
    print("\n##", o["name"], "" if o.get("exists") else "— НЕТ")
    for k in ("Измерения", "Ресурсы", "Реквизиты"):
        if o.get(k):
            print(" ", k + ":", nm(o[k]))
    for t in o.get("ТабличныеЧасти") or []:
        if t.split(":")[0] in ("Товары", "Продукция", "Материалы", "ВозвратныеОтходы", "Сырье", "ТоварыКПередаче"):
            print("  ТЧ", t[:300])
    others = [t.split(":")[0] for t in (o.get("ТабличныеЧасти") or [])]
    if others:
        print("  все ТЧ:", ", ".join(others))
