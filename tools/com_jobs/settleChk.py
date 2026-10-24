# Чтение (21-14): остатки расчётов с клиентами/поставщиками по объектам; контрагенты, у которых долг на одном объекте и аванс на другом.
import csv
from collections import defaultdict
M = ib.Метаданные.РегистрыНакопления
for reg in ("РасчетыСКлиентами", "РасчетыСПоставщиками"):
    r = M.Найти(reg)
    if r is None: print("нет регистра", reg); continue
    print(reg, "| изм:", ",".join(r.Измерения.Получить(j).Имя for j in range(r.Измерения.Количество())),
          "| рес:", ",".join(r.Ресурсы.Получить(j).Имя for j in range(r.Ресурсы.Количество())))
OBJ = {"РасчетыСКлиентами": "ЗаказКлиента", "РасчетыСПоставщиками": "ЗаказПоставщику"}
out = r"D:\anescom_edo\data\reports\21-14_расчеты_долг_и_аванс.csv"
with open(out, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["Регистр", "Организация", "Контрагент", "Объект расчётов", "Остаток", "Итог по контрагенту", "Долг", "Аванс"])
    for reg, obj in OBJ.items():
        try:
            rows = q(f"""ВЫБРАТЬ Р.АналитикаУчетаПоПартнерам.Организация КАК Орг, Р.АналитикаУчетаПоПартнерам.Контрагент КАК Кт,
             Р.{obj} КАК Об, СУММА(Р.СуммаОстаток) КАК Ост
            ИЗ РегистрНакопления.{reg}.Остатки КАК Р СГРУППИРОВАТЬ ПО Р.АналитикаУчетаПоПартнерам.Организация, Р.АналитикаУчетаПоПартнерам.Контрагент, Р.{obj}
            ИМЕЮЩИЕ СУММА(Р.СуммаОстаток) <> 0""")
        except Exception as e:
            print("ОШИБКА запроса", reg, str(e)[-200:]); continue
        by = defaultdict(list)
        for x in rows:
            by[(s(x["Орг"]), s(x["Кт"]))].append((s(x["Об"]), float(x["Ост"] or 0)))
        mixed = {k: v for k, v in by.items() if any(a > 0.5 for _, a in v) and any(a < -0.5 for _, a in v)}
        tot_pos = sum(a for v in by.values() for _, a in v if a > 0); tot_neg = sum(a for v in by.values() for _, a in v if a < 0)
        m_pos = sum(a for v in mixed.values() for _, a in v if a > 0); m_neg = sum(a for v in mixed.values() for _, a in v if a < 0)
        print(f"{reg}: контрагентов {len(by)}, объектов {len(rows)}; + {tot_pos:,.0f} / − {tot_neg:,.0f}; "
              f"смешанных (долг и аванс одновременно) {len(mixed)}: + {m_pos:,.0f} / − {m_neg:,.0f}")
        types = defaultdict(lambda: [0, 0.0])
        for v in by.values():
            for o, a in v:
                t = o.split(" ")[0] if o else "(пусто)"; types[t][0] += 1; types[t][1] += a
        for t, (n, a) in sorted(types.items(), key=lambda z: -abs(z[1][1]))[:8]:
            print(f"   объект «{t}»: {n} шт, {a:,.0f}")
        for k, v in sorted(mixed.items(), key=lambda z: -min(sum(a for _, a in z[1] if a > 0), -sum(a for _, a in z[1] if a < 0))):
            tot = sum(a for _, a in v); d = sum(a for _, a in v if a > 0); av = sum(a for _, a in v if a < 0)
            for o, a in v:
                w.writerow([reg, k[0], k[1], o, f"{a:.2f}".replace(".", ","), f"{tot:.2f}".replace(".", ","), f"{d:.2f}".replace(".", ","), f"{av:.2f}".replace(".", ",")])
print("файл:", out)
