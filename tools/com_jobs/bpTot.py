# Чтение: БП — итоги по счетам на дату (контроль) + КА нач. остатки по счетам
from collections import defaultdict
BPREG = globals().get("BPREG_NAME", "Типовой")
for dd in (datetime.datetime(2025, 1, 1, 5, 0, 0), datetime.datetime(2024, 12, 31, 12, 0, 0)):
    z = ib_bp.NewObject("Запрос")
    z.Текст = "ВЫБРАТЬ Т.Счет.Код КАК С, СУММА(Т.СуммаОстатокДт - Т.СуммаОстатокКт) КАК Б ИЗ РегистрБухгалтерии." + BPREG + ".Остатки(&Д, , , ) КАК Т СГРУППИРОВАТЬ ПО Т.Счет.Код"
    z.УстановитьПараметр("Д", dd)
    sel = z.Выполнить().Выбрать(); tot = {}
    while sel.Следующий():
        tot[sel.С] = sel.Б
    print(dd, "БП счета:", {k: round(v / 1e6, 2) for k, v in sorted(tot.items()) if abs(v) > 1e5})
