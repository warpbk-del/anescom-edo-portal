# 21-30f GREENTE: настройки организации, влияющие на регл. учёт (сравнение с ANESCOM), только чтение.
m = ib.Метаданные.Справочники.Организации.Реквизиты
names = [m.Получить(i).Имя for i in range(m.Количество())]
orgs = {s(r["О"]): r["О"] for r in q("ВЫБРАТЬ О.Ссылка КАК О ИЗ Справочник.Организации КАК О")}
print("организации:", list(orgs))
g = [o for n, o in orgs.items() if "GREENTE" in n.upper()][0]; a = [o for n, o in orgs.items() if "ANESCOM" in n.upper() and "АСНФ" not in n][0]
for n in names:
    try:
        vg, va = s(getattr(g, n)), s(getattr(a, n))
        if vg != va and len(vg) < 80: print(f"  {n:<40} GREENTE={vg[:35]:<35} ANESCOM={va[:35]}")
    except Exception: pass
for rn in ("УчетнаяПолитикаОрганизаций", "НастройкиРеглУчета", "ПорядокОтраженияРасчетовСПартнерами"):
    try:
        rr = q(f"ВЫБРАТЬ * ИЗ РегистрСведений.{rn} КАК Р")
        for r in rr:
            if any("GREENTE" in s(v).upper() for v in r.values()): print(" ", rn, {k: s(v)[:25] for k, v in r.items()})
        print(" ", rn, "записей", len(rr))
    except Exception as e: print(" ", rn, "нет:", str(e)[-60:])
for r in q("""ВЫБРАТЬ Р.Статус КАК С, КОЛИЧЕСТВО(*) КАК Н ИЗ РегистрСведений.ОтражениеДокументовВРеглУчете КАК Р ГДЕ Р.Организация = &О СГРУППИРОВАТЬ ПО Р.Статус""", О=g):
    print("  GREENTE статусы отражения:", s(r["С"]), r["Н"])
