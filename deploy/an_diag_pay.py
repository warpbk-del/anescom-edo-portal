# Из последней диагностики 1С (с info_registers): поля документов оплат для расширения уведомлений об оплате.
import json, sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8")
c = sqlite3.connect(r"D:\anescom_edo\data\analytics.sqlite3")
row = c.execute("SELECT body FROM an_meta WHERE body LIKE '%info_registers%' ORDER BY id DESC LIMIT 1").fetchone()
j = json.loads(row[0])
want = ("ХозяйственнаяОперация", "Контрагент", "СуммаДокумента", "Партнер", "Касса", "Организация")
for d in j["documents"]:
    if d["name"] in ("ПриходныйКассовыйОрдер", "ОперацияПоПлатежнойКарте", "ЭквайринговаяОперация",
                     "ПоступлениеБезналичныхДенежныхСредств"):
        rek = [x.split(" ")[0] for x in d.get("Реквизиты", [])]
        print(d["name"], "есть" if d.get("exists") else "НЕТ", [w for w in want if w in rek])
        for t in d.get("ТабличныеЧасти", []):
            print("   ТЧ", t[:140])
for r in j.get("info_registers", []):
    if r["name"] == "ФискальныеОперацииРК":
        for k in ("Измерения", "Ресурсы", "Реквизиты"):
            print("РК", k, [x.split(" ")[0] for x in r.get(k) or []])
