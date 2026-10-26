# 21-28b (только чтение, после openGoods): нечёткое сопоставление позиций «только в БП» ↔ «только в КА» (переименования),
# затем пересчёт связи «ввод занижен → оприходование 2025» / «ввод завышен → списание 2025» с учётом сопоставленных имён.
import re, csv, difflib
from collections import defaultdict
ART = re.compile(r"[A-ZА-Я]{0,4}\d+[\d.,/\-]*\d|\d{2,}")
def arts(x): return set(a.replace(",", ".") for a in ART.findall(x))
def core(x): return " ".join(w for w in re.sub(r"[()\[\],;]", " ", x).split() if w not in ("ТАТПРОФ", "TATPROF", "ТП"))
OB = sorted(set(BPI) - set(KAI)); OK = sorted(set(KAI) - set(BPI))
cand = []
for b in OB:
    ab, cb = arts(b), core(b)
    best = (0, None)
    for k in OK:
        ak = arts(k)
        if ab and ak and not (ab & ak): continue
        r = difflib.SequenceMatcher(None, cb, core(k)).ratio()
        if ab and ak and ab == ak: r += 0.1
        if r > best[0]: best = (r, k)
    if best[1] and best[0] >= 0.80: cand.append((best[0], b, best[1]))
cand.sort(reverse=True)
used, MAPN = set(), {}
for r, b, k in cand:
    if k in used: continue
    used.add(k); MAPN[b] = (k, r)
print(f"только БП {len(OB)} | только КА {len(OK)} | сопоставлено пар (≥0,80): {len(MAPN)} на БП {sum(BPI[b][1] for b in MAPN):,.2f} / КА {sum(KAI[k][1] for k, _ in MAPN.values()):,.2f}")
for b, (k, r) in list(MAPN.items())[:12]:
    print(f"  {r:.2f} | {b[:48]:<48} → {k[:48]}")
# объединённые остатки: имя БП заменяем на имя КА
BPI2 = defaultdict(lambda: [0.0, 0.0])
for b, v in BPI.items():
    x = BPI2[MAPN[b][0] if b in MAPN else b]; x[0] += v[0]; x[1] += v[1]
DI2 = {k: (BPI2.get(k, [0, 0]), KAI.get(k, [0, 0])) for k in set(BPI2) | set(KAI)}
low2 = {k: v for k, v in DI2.items() if v[1][0] < v[0][0] - 0.0005}
high2 = {k: v for k, v in DI2.items() if v[1][0] > v[0][0] + 0.0005}
L2 = [(k, v, OPR[k]) for k, v in low2.items() if k in OPR and OPR[k][0] > 0]
H2 = [(k, v, SPS[k]) for k, v in high2.items() if k in SPS and SPS[k][0] > 0]
oq = sum(min(v[0][0] - v[1][0], o[0]) for k, v, o in L2); osum = sum(o[1] * min(1, (v[0][0] - v[1][0]) / o[0]) for k, v, o in L2)
sq = sum(min(v[1][0] - v[0][0], o[0]) for k, v, o in H2)
print(f"после сопоставления: ввод меньше БП {len(low2)} поз., больше {len(high2)} поз.")
print(f"ОПРИХОДОВАНИЯ 2025, объяснимые недовводом: {len(L2)} поз., кол-во {oq:,.3f}, сумма ≈ {osum:,.2f} (из {sum(v[1] for v in OPR.values()):,.2f})")
print(f"СПИСАНИЯ 2025, объяснимые перевводом: {len(H2)} поз., кол-во {sq:,.3f} (из {sum(v[0] for v in SPS.values()):,.3f} ед.)")
P = r"D:\anescom_edo\data\reports\vvod_tovary_sopostavlenie_imen.csv"
with open(P, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";"); w.writerow(["Сходство", "Номенклатура БП", "Номенклатура КА", "БП кол", "БП сумма", "КА кол", "КА сумма"])
    for b, (k, r) in MAPN.items(): w.writerow([round(r, 2), b, k, BPI[b][0], round(BPI[b][1], 2), KAI[k][0], round(KAI[k][1], 2)])
print("CSV:", P)
log(f"21-28b сопоставление имён БП↔КА: пар {len(MAPN)}; оприходований объяснимо недовводом {len(L2)} поз. ≈{osum:,.0f}; списаний объяснимо перевводом {len(H2)} поз.")
