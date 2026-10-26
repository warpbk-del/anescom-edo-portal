# 21-29d: повторная сверка 1030/2209 — 1С суммируется по документу (расшифровка платежа делит сумму на строки), затем допуск по дате ±7 дн.
import collections
AGG = collections.defaultdict(lambda: [0, None])
for dm, sg, a, r, p in C1:
    k = (ib.String(r), sg); AGG[k][0] += a; AGG[k][1] = p; AGG[k].append(r) if len(AGG[k]) < 3 else None
D1 = [(v[1], sg, v[0], v[2], rn) for (rn, sg), v in AGG.items()]
BL = [(datetime.date(2026, int(x[2:4]), int(x[:2])), x[4], int(x[5:]), i) for i, x in enumerate(ST)]
byk = collections.defaultdict(list)
for d, sg, a, i in BL: byk[(sg, a)].append((d, i))
used = set(); un = []
for p, sg, a, r, rn in sorted(D1, key=lambda x: x[0]):
    d = p.date() if hasattr(p, "date") else p
    c = [(abs((bd - d).days), i) for bd, i in byk.get((sg, a), []) if i not in used and abs((bd - d).days) <= 7]
    if c: used.add(min(c)[1])
    else: un.append((p, sg, a, rn))
ub = [i for i in range(len(ST)) if i not in used]
print(f"1С документов {len(D1)}; совпало {len(used)}; 1С без пары {len(un)} (+{sum(a for p,s,a,_ in un if s=='+')/100:,.2f} / -{sum(a for p,s,a,_ in un if s=='-')/100:,.2f}); "
      f"банк без пары {len(ub)} (+{sum(int(ST[i][5:]) for i in ub if ST[i][4]=='+')/100:,.2f} / -{sum(int(ST[i][5:]) for i in ub if ST[i][4]=='-')/100:,.2f})")
tp = collections.Counter(); ts = collections.Counter()
for p, sg, a, rn in un:
    t = rn.split(" 00")[0].split(" АС")[0][:40]; tp[(t, sg)] += 1; ts[(t, sg)] += a
print("1С без пары по видам:", "; ".join(f"{k[0]} {k[1]} {tp[k]} шт {ts[k]/100:,.0f}" for k in sorted(ts, key=lambda k: -ts[k])[:8]))
UN2 = un; UB2 = ub
open(r"D:\anescom_edo\data\reports\bank2209_unmatched_1c.txt", "w", encoding="utf-8").write("\n".join(f"{p}\t{sg}\t{a/100:.2f}\t{rn}" for p, sg, a, rn in un))
print("индексы банка без пары:", ",".join(map(str, ub)))
