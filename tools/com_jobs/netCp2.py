# Нетто по контрагенту по ВСЕМ расчётным счетам, сопоставление по «нечёткому» имени (без ТОО/ИП/ООО/кавычек, порядок слов не важен).
import re as _re
from collections import defaultdict
PFX = ("121", "171", "331", "351", "338", "336", "125", "128", "335")
LEG = r"\b(ТОВАРИЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ|ИНДИВИДУАЛЬНЫЙ ПРЕДПРИНИМАТЕЛЬ|ТОО|ИП|ООО|АО|TOO|LLP|LTD|CO|ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ)\b"
TR = str.maketrans("ҰҮҚҒӘӨҢҺІЁ", "УУКГАОНХИЕ")
def fz(x):
    x = (x or "").upper().translate(TR)
    x = _re.sub(r"\(.*?\)", " ", x)
    x = _re.sub(LEG, " ", x)
    x = _re.sub(r"[^0-9A-ZА-Я ]+", " ", x)
    return " ".join(sorted(t for t in x.split() if len(t) > 1))
bp = defaultdict(float); ka = defaultdict(float); nm = {}; ab = defaultdict(set); ak = defaultdict(set)
for (a, k), v in BPK.items():
    if a.startswith(PFX) and abs(v) > 0.005:
        f = fz(BPN.get((a, k), k)); bp[f] += v; nm.setdefault(f, BPN.get((a, k), k)); ab[f].add(a)
for (a, k), v in KAK.items():
    if a.startswith(PFX) and abs(v) > 0.005:
        n = s(KAR[(a, k)]) if (a, k) in KAR else k
        f = fz(n); ka[f] += v; nm.setdefault(f, n); ak[f].add(a)
keys = set(bp) | set(ka)
same = [k for k in keys if abs(bp[k] - ka[k]) <= 1]
diff = sorted([k for k in keys if abs(bp[k] - ka[k]) > 1], key=lambda k: -abs(ka[k] - bp[k]))
only_bp = [k for k in diff if abs(ka[k]) < 0.01]; only_ka = [k for k in diff if abs(bp[k]) < 0.01]
print(f"контрагентов {len(keys)}: нетто совпадает {len(same)} (переложены между счетами: {sum(1 for k in same if ab[k] != ak[k])}); разное {len(diff)} (только в БП {len(only_bp)}, только в КА {len(only_ka)})")
print(f"итог разниц КА−БП {sum(ka[k] - bp[k] for k in diff):,.2f}; только в БП: {sum(-bp[k] for k in only_bp):,.2f}; только в КА: {sum(ka[k] for k in only_ka):,.2f}; в обеих, но разное: {sum(ka[k] - bp[k] for k in diff if k not in only_bp and k not in only_ka):,.2f}")
print("== топ-30 разниц")
for k in diff[:30]:
    print(f"  {nm[k][:34]:<34} | БП {bp[k]:>15,.2f} {','.join(sorted(ab[k]))[:14]:<14} | КА {ka[k]:>15,.2f} {','.join(sorted(ak[k]))[:14]:<14} | {ka[k] - bp[k]:>14,.2f}")
NET2 = [(nm[k], bp[k], ka[k], ','.join(sorted(ab[k])), ','.join(sorted(ak[k]))) for k in diff]
