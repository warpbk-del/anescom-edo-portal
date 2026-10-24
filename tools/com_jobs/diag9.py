# Диагностика 9 неуменьшенных оприходований: товары, совпавшие расходы (склад), мин. остаток на складе оприходования после его даты.
import re as _re
from collections import defaultdict
okd, fail = set(), []
for ln in open(LOG, encoding="utf-8"):
    mm = _re.search(r"21-9 (.+?): (уменьшено|все строки)", ln)
    if mm: okd.add(mm.group(1))
    mm = _re.search(r"21-9 ОШИБКА (.+?): ", ln)
    if mm: fail.append(mm.group(1))
REST = sorted(set(f for f in fail if f not in okd))
info = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0, set()]))  # r -> item -> [same, cross, Ys]
rr = {}
for t, o, r, m, k in MATCH:
    rn = s(r["Р"])
    if rn in REST:
        x = info[rn][k]; rr[rn] = r
        if s(o["С"]) == s(r["С"]): x[0] += m
        else: x[1] += m; x[2].add(s(o["С"])[:14])
for rn in REST:
    r = rr[rn]
    print(f"== {rn[-42:]} | склад {s(r['С'])[:22]} | товаров {len(info[rn])}")
    for k, (same, cross, ys) in sorted(info[rn].items(), key=lambda x: -(x[1][0] + x[1][1]))[:6]:
        mb = q("""ВЫБРАТЬ МИНИМУМ(Т.КоличествоКонечныйОстаток) КАК М ИЗ РегистрНакопления.ТоварыОрганизаций.ОстаткиИОбороты(&Н, , Регистратор, ,
          АналитикаУчетаНоменклатуры.Номенклатура.Наименование = &И И АналитикаУчетаНоменклатуры.Склад = &С) КАК Т""", Н=r["П"], И=k, С=r["С"])
        print(f"   {k[:40]:<40} тот же склад {same:>9.2f} | др.склад {cross:>9.2f} {','.join(ys)[:30]:<30} | мин.остаток после {mb[0]['М'] if mb else '?'}")
