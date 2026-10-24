# Чтение: полный ввод остатков — БП (ib_bp, 31.12.2024) против КА (нач. остаток 01.2025) по счёт + субконто1. Только ANESCOM.
from collections import defaultdict
MAP = {"1320": "1330", "1410": "1411", "3220": "3221", "2410": "2412", "2420": "2412"}
def nk(x): return (x or "").upper().replace("Ё", "Е").replace('"', "").replace("«", "").replace("»", "").replace("  ", " ").strip()
BPREG = ib_bp.Метаданные.РегистрыБухгалтерии.Получить(0).Имя
z = ib_bp.NewObject("Запрос")
z.Текст = """ВЫБРАТЬ Т.Счет.Код КАК С, Т.Организация КАК О, Т.Субконто1 КАК С1, Т.СуммаОстатокДт - Т.СуммаОстатокКт КАК Б ИЗ РегистрБухгалтерии.""" + BPREG + """.Остатки(&Д, , , ) КАК Т"""
z.УстановитьПараметр("Д", datetime.datetime(2025, 1, 1, 5, 0, 0))
sel = z.Выполнить().Выбрать()
BP = defaultdict(float); orgs = defaultdict(float)
while sel.Следующий():
    o = ib_bp.String(sel.О); orgs[o] += abs(sel.Б or 0)
    if "ANESCOM" not in o.upper() and "АНЕСКОМ" not in o.upper():
        continue
    a = MAP.get(sel.С, sel.С)
    BP[(a, nk(ib_bp.String(sel.С1)))] += sel.Б or 0
print("орг. в БП:", {k[:25]: round(v / 1e6, 1) for k, v in orgs.items()})
KA = defaultdict(float); KAREF = {}
for r in q("""ВЫБРАТЬ Т.Счет.Код КАК С, Т.Организация КАК О, Т.Субконто1 КАК С1, Т.СуммаНачальныйОстатокДт - Т.СуммаНачальныйОстатокКт КАК Б
ИЗ РегистрБухгалтерии.{REG}.ОстаткиИОбороты(&Н, &К, , , , , ) КАК Т""", Н=datetime.datetime(2025, 1, 1, 6), К=datetime.datetime(2025, 1, 31, 23)):
    o = s(r["О"])
    if "ANESCOM" not in o.upper() and "АНЕСКОМ" not in o.upper():
        continue
    if abs(r["Б"] or 0) > 0.005:
        k = (r["С"], nk(s(r["С1"]))); KA[k] += r["Б"]; KAREF[k] = r["С1"]
D = {k: (BP.get(k, 0), KA.get(k, 0)) for k in set(BP) | set(KA) if abs(KA.get(k, 0) - BP.get(k, 0)) > 0.5}
byacc = defaultdict(lambda: [0, 0.0, 0.0])
for (a, sb), (b, k) in D.items():
    x = byacc[a]; x[0] += 1; x[1] += k - b; x[2] += abs(k - b)
print(f"строк с расхождением: {len(D)}; итог КА−БП по всем: {sum(k - b for b, k in D.values()):,.2f}")
print("счёт | строк | КА−БП | сумма модулей")
for a, (n, d, ab) in sorted(byacc.items(), key=lambda x: -x[1][2]):
    print(f"  {a:<7} {n:>5} {d:>17,.2f} {ab:>17,.2f}")
OPEN_D = D
