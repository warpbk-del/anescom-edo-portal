# Чтение: ввод остатков — БП (31.12.2024, D:\anescom_edo\legacy\bp\acc_Типовой.tsv) против КА (начальный остаток января 2025) по счетам 3381, 3360, 3350, 1030, 1010, 0000 с субконто.
import csv
from collections import defaultdict
ACCS = globals().get("OPEN_ACCS", ("3381", "3360", "3350", "1030", "1010", "0000"))
P = r"D:\anescom_edo\legacy\bp\acc_Типовой.tsv"
with open(P, encoding="utf-8-sig", errors="replace", newline="") as f:
    rd = csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
    head = next(rd)
    print("колонки БП:", head[:20])
    ix = {h: i for i, h in enumerate(head)}
    bp = defaultdict(float)
    for ln in rd:
        g = lambda h: ln[ix[h]] if h in ix and ix[h] < len(ln) else ""
        if g("Период")[:10] > "2024-12-31":
            continue
        try:
            sm = float(g("Сумма") or 0)
        except ValueError:
            continue
        d, k = g("СчетДт"), g("СчетКт")
        if d in ACCS:
            bp[(d, g("СубконтоДт1"))] += sm
        if k in ACCS:
            bp[(k, g("СубконтоКт1"))] -= sm
ka = defaultdict(float)
for r in q("""ВЫБРАТЬ Т.Счет.Код КАК С, Т.Субконто1 КАК С1, Т.СуммаНачальныйОстатокДт - Т.СуммаНачальныйОстатокКт КАК Б
ИЗ РегистрБухгалтерии.{REG}.ОстаткиИОбороты(&Н, &К, , , , , ) КАК Т""", Н=datetime.datetime(2025, 1, 1, 6), К=datetime.datetime(2025, 1, 31, 23)):
    if r["С"] in ACCS and abs(r["Б"] or 0) > 0.005:
        ka[(r["С"], s(r["С1"]))] += r["Б"]
def nk(x): return x.upper().replace("Ё", "Е").replace('"', "").replace("«", "").replace("»", "").strip()
allk = defaultdict(lambda: [0.0, 0.0])
for (a, sb), v in bp.items(): allk[(a, nk(sb))][0] += v
for (a, sb), v in ka.items(): allk[(a, nk(sb))][1] += v
OPEN = allk
for a in ACCS:
    rows_ = [(k[1], v) for k, v in allk.items() if k[0] == a and abs(v[1] - v[0]) > 0.5]
    tb = sum(v[0] for k, v in allk.items() if k[0] == a); tk = sum(v[1] for k, v in allk.items() if k[0] == a)
    print(f"== {a}: БП {tb:,.2f} | КА {tk:,.2f} | разница {tk - tb:,.2f} | строк с разницей {len(rows_)}")
    for sb, (b, k) in sorted(rows_, key=lambda x: -abs(x[1][1] - x[1][0]))[:8]:
        print(f"    {sb[:45]:<45} БП {b:>15,.2f} КА {k:>15,.2f} разн {k - b:>14,.2f}")
