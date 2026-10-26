# 21-29f: групповая сверка остатка несовпадений 2209: (знак, БИН/вид, дата±3) — снимает «один платёж = несколько документов».
import collections
def kbin(r):
    try: return (s(r.Контрагент.ИНН) or "").strip()
    except Exception: return ""
G1 = collections.defaultdict(lambda: [0, []]); 
for p, sg, a, rn in UN2:
    r = AGG[(rn, sg)][2]; b = kbin(r)
    key = (sg, b if b else "~"); d = (p.date() if hasattr(p, "date") else p)
    G1[(key, d)][0] += a; G1[(key, d)][1].append(rn)
GB = collections.defaultdict(lambda: [0, []])
for i in UB2:
    c = CT[i]; b = c[1:] if c[0] == "П" and c[1:] else "~"
    d = datetime.date(2026, int(ST[i][2:4]), int(ST[i][:2]))
    GB[((ST[i][4], b), d)][0] += int(ST[i][5:]); GB[((ST[i][4], b), d)][1].append(i)
usedB = set(); ok1 = set()
for (k, d), (a, lst) in sorted(G1.items(), key=lambda x: x[0][1]):
    for dd in sorted(GB, key=lambda x: abs((x[1] - d).days)):
        if dd in usedB or dd[0] != k or abs((dd[1] - d).days) > 3: continue
        if GB[dd][0] == a: usedB.add(dd); ok1.add((k, d)); break
# по дню и знаку (без БИН) — суммы за день
R1 = [x for x in G1 if x not in ok1]; RB = [x for x in GB if x not in usedB]
d1 = collections.defaultdict(int); db = collections.defaultdict(int)
for (k, d) in R1: d1[(k[0], d)] += G1[(k, d)][0]
for (k, d) in RB: db[(k[0], d)] += GB[(k, d)][0]
okd = {x for x in d1 if d1[x] == db.get(x)}
r1 = [(k, d) for (k, d) in R1 if (k[0], d) not in okd]; rb = [(k, d) for (k, d) in RB if (k[0], d) not in okd]
s1p = sum(G1[x][0] for x in r1 if x[0][0] == "+"); s1m = sum(G1[x][0] for x in r1 if x[0][0] == "-")
sbp = sum(GB[x][0] for x in rb if x[0][0] == "+"); sbm = sum(GB[x][0] for x in rb if x[0][0] == "-")
print(f"после групп (БИН±3дн): закрыто групп 1С {len(ok1)}, по дневным суммам {len(okd)} дн.; ОСТАЛОСЬ 1С {sum(len(G1[x][1]) for x in r1)} док. +{s1p/100:,.2f} / -{s1m/100:,.2f}; банк {sum(len(GB[x][1]) for x in rb)} стр. +{sbp/100:,.2f} / -{sbm/100:,.2f}")
print("  разница (1С−банк): поступления", f"{(s1p-sbp)/100:,.2f}", "списания", f"{(s1m-sbm)/100:,.2f}", "| влияние на остаток", f"{((s1p-sbp)-(s1m-sbm))/100:,.2f}")
L = []
for x in r1:
    for rn in G1[x][1]: L.append(("1С", x[1], x[0][0], AGG[(rn, x[0][0])][0], rn))
for x in rb:
    for i in GB[x][1]: L.append(("БАНК", x[1], x[0][0], int(ST[i][5:]), f"#{i} {CT[i][0]} {CT[i][1:]}"))
L.sort(key=lambda z: -z[3])
for z in L[:40]: print(f"  {z[0]:<4} {z[1].strftime('%d.%m')} {z[2]}{z[3]/100:>14,.2f} {z[4][-60:]}")
open(r"D:\anescom_edo\data\reports\bank2209_ostatok.txt", "w", encoding="utf-8").write("\n".join(f"{z[0]}\t{z[1]}\t{z[2]}\t{z[3]/100:.2f}\t{z[4]}" for z in L))
REST = L
