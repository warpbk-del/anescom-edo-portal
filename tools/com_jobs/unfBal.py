# Чтение: остатки расчётов в УНФ по контрагентам на дату (регистры накопления с «Расчет» в имени) + сравнение с БП/КА (NET2).
import re as _re
from collections import defaultdict
D = globals().get("UNF_DATE", datetime.datetime(2025, 1, 1, 5))
MD = ib_unf.Метаданные.РегистрыНакопления
UN = defaultdict(float); used = []
for i in range(MD.Количество()):
    m = MD.Получить(i)
    if not m.Имя.startswith("Расчеты"):
        continue
    dims = [m.Измерения.Получить(j).Имя for j in range(m.Измерения.Количество())]
    res = [m.Ресурсы.Получить(j).Имя for j in range(m.Ресурсы.Количество())]
    if "Контрагент" not in dims or not res:
        continue
    r0 = "Сумма" if "Сумма" in res else res[0]
    sign = -1 if "Поставщик" in m.Имя else 1   # долг поставщику — со знаком минус (как кредит)
    z = ib_unf.NewObject("Запрос")
    z.Текст = f"ВЫБРАТЬ Т.Контрагент КАК К, СУММА(Т.{r0}Остаток) КАК С ИЗ РегистрНакопления.{m.Имя}.Остатки(&Д, ) КАК Т СГРУППИРОВАТЬ ПО Т.Контрагент"
    z.УстановитьПараметр("Д", D)
    try:
        sel = z.Выполнить().Выбрать()
    except Exception as e:
        print("пропуск", m.Имя, str(e)[-80:]); continue
    n = 0
    while sel.Следующий():
        UN[fz(ib_unf.String(sel.К))] += sign * (sel.С or 0); n += 1
    used.append(f"{m.Имя}({r0},{n})")
print("регистры УНФ:", used)
print(f"контрагентов с остатком в УНФ: {sum(1 for v in UN.values() if abs(v) > 1)}, нетто {sum(UN.values()):,.2f}")
# сравнение: для разниц БП↔КА — объясняет ли УНФ
expl = notexp = 0; rows_ = []
for n, b, c, ab_, ak_ in NET2:
    u = UN.get(fz(n), 0.0)
    ok = abs(c - u) <= 1 and abs(u) > 0.5
    expl += ok; notexp += not ok
    rows_.append((n, b, c, u, ok))
print(f"из {len(NET2)} расхождений БП↔КА: КА = УНФ у {expl}; не объясняется УНФ: {notexp}")
for n, b, c, u, ok in sorted(rows_, key=lambda x: -abs(x[2] - x[1]))[:25]:
    print(f"  {n[:32]:<32} | БП {b:>14,.0f} | КА {c:>14,.0f} | УНФ {u:>14,.0f} | {'КА=УНФ' if ok else ''}")
UNFCMP = rows_
