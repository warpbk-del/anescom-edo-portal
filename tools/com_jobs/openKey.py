# Сверка ввода остатков БП↔КА по КЛЮЧАМ субконто: БИН/ИИН, номер счёта, артикул; иначе нормализованное имя.
from collections import defaultdict
MAP = {"1320": "1330", "1410": "1411", "3220": "3221", "2410": "2412", "2420": "2412"}
def nk(x): return (x or "").upper().replace("Ё", "Е").replace('"', "").replace("«", "").replace("»", "").replace(" ", "").strip()
_cache = {}
def key(base, ref):
    if ref is None:
        return "—"
    try:
        sref = base.String(ref)
    except Exception:
        sref = str(ref)
    ck = (id(base), sref)
    if ck in _cache:
        return _cache[ck]
    k = None
    for att, pre in (("ИдентификационныйКодЛичности", "ID:"), ("БИН", "ID:"), ("ИИН", "ID:"), ("НомерСчета", "СЧ:"), ("Артикул", "АРТ:")):
        try:
            v = str(getattr(ref, att) or "").strip()
            if v and len(v) >= 4:
                k = pre + v.replace(" ", "").upper(); break
        except Exception:
            pass
    if k is None:
        k = "ИМЯ:" + nk(sref)
    _cache[ck] = k
    return k
BPREG = "Типовой"
z = ib_bp.NewObject("Запрос")
z.Текст = "ВЫБРАТЬ Т.Счет.Код КАК С, Т.Организация КАК О, Т.Субконто1 КАК С1, Т.СуммаОстатокДт - Т.СуммаОстатокКт КАК Б ИЗ РегистрБухгалтерии.Типовой.Остатки(&Д, , , ) КАК Т"
z.УстановитьПараметр("Д", datetime.datetime(2025, 1, 1, 5, 0, 0))
sel = z.Выполнить().Выбрать()
BPK = defaultdict(float); BPN = {}
while sel.Следующий():
    o = ib_bp.String(sel.О)
    if "ANESCOM" not in o.upper():
        continue
    a = MAP.get(sel.С, sel.С); k = key(ib_bp, sel.С1)
    BPK[(a, k)] += sel.Б or 0; BPN[(a, k)] = ib_bp.String(sel.С1)
KAK = defaultdict(float); KAR = {}
for r in q("""ВЫБРАТЬ Т.Счет.Код КАК С, Т.Организация КАК О, Т.Субконто1 КАК С1, Т.СуммаНачальныйОстатокДт - Т.СуммаНачальныйОстатокКт КАК Б
ИЗ РегистрБухгалтерии.{REG}.ОстаткиИОбороты(&Н, &К, , , , , ) КАК Т""", Н=datetime.datetime(2025, 1, 1, 6), К=datetime.datetime(2025, 1, 31, 23)):
    if "ANESCOM" not in s(r["О"]).upper() or abs(r["Б"] or 0) < 0.005:
        continue
    k = (r["С"], key(ib, r["С1"])); KAK[k] += r["Б"]; KAR[k] = r["С1"]
KD = {k: (BPK.get(k, 0), KAK.get(k, 0)) for k in set(BPK) | set(KAK) if abs(KAK.get(k, 0) - BPK.get(k, 0)) > 0.5}
by = defaultdict(lambda: [0, 0.0, 0.0, 0])
for (a, k), (b, c) in KD.items():
    x = by[a]; x[0] += 1; x[1] += c - b; x[2] += abs(c - b); x[3] += (k[:3] in ("ID:", "СЧ:", "АРТ"))
print(f"строк с разницей {len(KD)} (было по именам 3578); итог {sum(c - b for b, c in KD.values()):,.2f}")
print("счёт | строк | КА−БП | модули | по ключу(ID/счёт/арт)")
for a, (n, d, ab, kk) in sorted(by.items(), key=lambda x: -x[1][2]):
    print(f"  {a:<7} {n:>5} {d:>16,.2f} {ab:>16,.2f} {kk:>5}")
