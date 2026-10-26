# 21-29e: разбор несовпадений 2209: банк без пары по видам/БИН, 1С без пары по контрагентам, пары с датой >7 дн.
import collections
CT = zlib.decompress(base64.b64decode(_CT)).decode().split("|")
NAMES = {"Д": "депозит", "В": "вознагр.", "И": "инкассация", "К": "карточки", "М": "комиссия", "З": "зарплата", "Н": "налоги/гос", "П": "прочее"}
g = collections.defaultdict(lambda: [0, 0, 0]); gb = collections.defaultdict(lambda: [0, 0])
for i in UB2:
    c = CT[i][0]; a = int(ST[i][5:]); sg = ST[i][4]
    g[c][0] += 1; g[c][1 if sg == "+" else 2] += a
    if c == "П": gb[(CT[i][1:], sg)][0] += 1; gb[(CT[i][1:], sg)][1] += a
print("БАНК без пары по видам:", "; ".join(f"{NAMES[c]} {v[0]} шт +{v[1]/100:,.0f} / -{v[2]/100:,.0f}" for c, v in sorted(g.items(), key=lambda x: -(x[1][1] + x[1][2]))))
bins = [b for b, _ in gb if b]
nm = {}
if bins:
    for r in q("ВЫБРАТЬ К.ИдентификационныйКодЛичности КАК Б, К.Наименование КАК Н ИЗ Справочник.Контрагенты КАК К ГДЕ К.ИдентификационныйКодЛичности В (&Б)", Б=bins) if False else []:
        nm[r["Б"]] = s(r["Н"])
print("БАНК «прочее» без пары, крупные по БИН:")
for (b, sg), v in sorted(gb.items(), key=lambda x: -x[1][1])[:15]:
    print(f"   {b or '-':<13} {sg} {v[0]:>3} шт {v[1]/100:>15,.2f}")
# 1С без пары — по контрагенту
c1 = collections.defaultdict(lambda: [0, 0]); refs = {}
for p, sg, a, rn in UN2:
    c1[(rn.split(" от ")[0][:45], sg)][0] += 1
k1 = collections.defaultdict(lambda: [0, 0])
for (rn, sg), v in AGG.items():
    pass
for p, sg, a, rn in UN2:
    r = AGG[(rn, sg)][2]
    try: kk = s(r.Контрагент)
    except Exception: kk = "?"
    k1[(kk[:30], sg)][0] += 1; k1[(kk[:30], sg)][1] += a
print("1С без пары по контрагентам (крупные):")
for (k, sg), v in sorted(k1.items(), key=lambda x: -x[1][1])[:15]:
    print(f"   {k:<30} {sg} {v[0]:>3} шт {v[1]/100:>15,.2f}")
# пары с той же суммой, но датой дальше 7 дней
bl = collections.defaultdict(list)
for i in UB2: bl[(ST[i][4], int(ST[i][5:]))].append(i)
far = 0; fs = 0
for p, sg, a, rn in UN2:
    if bl.get((sg, a)): far += 1; fs += a
print(f"той же суммой, но дата >7 дн.: {far} шт на {fs/100:,.2f}")
