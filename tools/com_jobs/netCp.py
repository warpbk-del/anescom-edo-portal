# Куда перенесли: по каждому контрагенту (ключ БИН/ИИН/имя) — нетто по ВСЕМ расчётным счетам (121x,171x,331x,351x,338x,336x) в БП и в КА.
# Если нетто совпадает — суммы просто переложены между счетами (не ошибка). Иначе — реальная разница.
from collections import defaultdict
PFX = ("121", "171", "331", "351", "338", "336", "125", "128", "335")
bp = defaultdict(float); ka = defaultdict(float); nm = {}; accs = defaultdict(lambda: [set(), set()])
for (a, k), v in BPK.items():
    if a.startswith(PFX):
        bp[k] += v; nm.setdefault(k, BPN.get((a, k), k)); accs[k][0].add(a) if abs(v) > 0.5 else None
for (a, k), v in KAK.items():
    if a.startswith(PFX):
        ka[k] += v; nm.setdefault(k, s(KAR[(a, k)]) if (a, k) in KAR else k); accs[k][1].add(a) if abs(v) > 0.5 else None
keys = set(bp) | set(ka)
same = [k for k in keys if abs(bp[k] - ka[k]) <= 1]
moved = [k for k in same if accs[k][0] != accs[k][1]]
diff = sorted([k for k in keys if abs(bp[k] - ka[k]) > 1], key=lambda k: -abs(ka[k] - bp[k]))
print(f"контрагентов: {len(keys)}; нетто совпадает: {len(same)} (из них переложены между счетами: {len(moved)}); разное нетто: {len(diff)}")
print(f"сумма |разниц| нетто: {sum(abs(ka[k] - bp[k]) for k in diff):,.2f}; итог КА−БП: {sum(ka[k] - bp[k] for k in keys):,.2f}")
mv = sum(abs(bp[k]) for k in moved)
print(f"переложено между счетами (без ошибки), сумма: {mv:,.2f}")
print("== топ-25 реальных разниц (КА−БП) | счета БП → счета КА")
for k in diff[:25]:
    print(f"  {nm[k][:34]:<34} | БП {bp[k]:>15,.2f} | КА {ka[k]:>15,.2f} | разн {ka[k] - bp[k]:>14,.2f} | {','.join(sorted(accs[k][0]))[:18]} → {','.join(sorted(accs[k][1]))[:18]}")
NETDIFF = [(k, nm[k], bp[k], ka[k]) for k in diff]
