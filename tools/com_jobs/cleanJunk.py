# 21-15 чистка: номенклатура и контрагенты, на которые нет НИ ОДНОЙ ссылки в базе (НайтиПоСсылкам), -> пометка удаления.
# Для контрагента не считаются ссылками его собственные договоры/банковские счета (тогда помечаются и они).
# Окончательное удаление — пользователь («Удаление помеченных объектов»). DRY=True по умолчанию — только список.
import csv, os
DRY = globals().get("DRY", True)
OUT = r"D:\anescom_edo\data\reports\21-15"; os.makedirs(OUT, exist_ok=True)
OWN = ("ДоговорыКонтрагентов", "БанковскиеСчетаКонтрагентов")

def refs(lst):
    arr = ib.NewObject("Массив")
    for x in lst: arr.Добавить(x)
    t = ib.НайтиПоСсылкам(arr)
    used = {}
    for i in range(t.Количество()):
        row = t.Получить(i)
        used.setdefault(s(row.Ссылка), []).append((row.Метаданные.Имя, row.Данные))
    return used

for cat in ("Номенклатура", "Контрагенты"):
    items = q(f"ВЫБРАТЬ К.Ссылка КАК С, К.Наименование КАК Н ИЗ Справочник.{cat} КАК К ГДЕ НЕ К.ПометкаУдаления И НЕ К.ЭтоГруппа")
    print(cat, "всего не помеченных:", len(items))
    junk = []
    for b in range(0, len(items), 20000):
        part = items[b:b + 20000]
        used = refs([x["С"] for x in part])
        for x in part:
            u = used.get(s(x["С"]), [])
            if cat == "Контрагенты":
                own = [d for m, d in u if m in OWN]
                other = [m for m, d in u if m not in OWN]
                if not other:
                    junk.append((x, own))
            elif not u:
                junk.append((x, []))
        if b % 3000 == 0: print("  ...", b + len(part), "проверено, мусора", len(junk))
    if cat == "Контрагенты":
        # собственные договоры/счета кандидатов не должны нигде использоваться (один проход)
        owns = [d for _, own in junk for d in own]
        if owns:
            used2 = refs(owns)
            bad = {k for k, v in used2.items() if v}
            junk = [(x, own) for x, own in junk if not any(s(d) in bad for d in own)]
    with open(os.path.join(OUT, f"7_мусор_{cat}.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";"); w.writerow(["Наименование", "Подчинённых договоров/счетов"])
        for x, own in junk: w.writerow([x["Н"], len(own)])
    print(cat, "без единой ссылки:", len(junk))
    if DRY: continue
    n = 0
    for x, own in junk:
        try:
            for d in own:
                d.ПолучитьОбъект().УстановитьПометкуУдаления(True)
            x["С"].ПолучитьОбъект().УстановитьПометкуУдаления(True); n += 1
        except Exception as e:
            print("ОШИБКА", x["Н"][:40], str(e)[-120:])
    log(f"21-15 {cat}: помечено на удаление {n} (без ссылок в базе)")
