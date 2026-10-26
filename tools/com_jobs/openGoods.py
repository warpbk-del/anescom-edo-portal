# 21-28 (только чтение): ввод остатков ТОВАРОВ — БП (ib_bp, 31.12.2024) против КА (ib, 01.01.2025) по номенклатуре и складу,
# плюс связь расхождений с «Оприходованиями излишков» и «Списаниями недостач» 2025 в КА.
import csv
from collections import defaultdict
def nk(x): return " ".join((x or "").upper().replace("Ё", "Е").replace('"', "").replace("«", "").replace("»", "").split())
SKIP = ("АВТОКОМП", "AVTOKOMP", "GREENTE", "ГРИНТ")
def okorg(o): return not any(w in (o or "").upper() for w in SKIP)
D0 = datetime.datetime(2025, 1, 1, 5, 0, 0)
def sub(i, base):
    t = f"Т.Субконто{i}"
    return (f"ВЫБОР КОГДА {t} ССЫЛКА Справочник.Номенклатура ТОГДА 1 КОГДА {t} ССЫЛКА Справочник.Склады ТОГДА 2 ИНАЧЕ 0 КОНЕЦ КАК Т{i}, {t} КАК С{i}")
TXT = ("ВЫБРАТЬ Т.Счет.Код КАК Сч, Т.Организация КАК О, " + ", ".join(sub(i, 0) for i in (1, 2, 3)) +
       ", Т.КоличествоОстатокДт - Т.КоличествоОстатокКт КАК К, Т.СуммаОстатокДт - Т.СуммаОстатокКт КАК Б "
       "ИЗ РегистрБухгалтерии.%s.Остатки(&Д, Счет.Код ПОДОБНО \"13%%\", , ) КАК Т")
def grab(base, regname, tag):
    z = base.NewObject("Запрос"); z.Текст = TXT % regname; z.УстановитьПараметр("Д", D0)
    sel = z.Выполнить().Выбрать(); R = defaultdict(lambda: [0.0, 0.0]); orgs = defaultdict(float); n = 0
    while sel.Следующий():
        o = base.String(sel.О); orgs[o[:25]] += sel.Б or 0
        if not okorg(o): continue
        it = wh = ""
        for i in (1, 2, 3):
            t = getattr(sel, f"Т{i}")
            if t == 1 and not it: it = nk(base.String(getattr(sel, f"С{i}")))
            if t == 2 and not wh: wh = nk(base.String(getattr(sel, f"С{i}")))
        if not it: continue
        x = R[(sel.Сч.strip(), it, wh)]; x[0] += sel.К or 0; x[1] += sel.Б or 0; n += 1
    print(f"{tag}: строк {n}, орг.: " + "; ".join(f"{k}={v/1e6:.1f}м" for k, v in orgs.items()))
    return R
BPR = grab(ib_bp, "Типовой", "БП 31.12.2024")
KAR2 = grab(ib, REG, "КА 01.01.2025")
# по номенклатуре (все счета 13xx и склады вместе) и по номенклатуре+складу
def agg(R, keyf):
    A = defaultdict(lambda: [0.0, 0.0])
    for k, (qn, sm) in R.items(): a = A[keyf(k)]; a[0] += qn; a[1] += sm
    return A
BPI, KAI = agg(BPR, lambda k: k[1]), agg(KAR2, lambda k: k[1])
BPW, KAW = agg(BPR, lambda k: (k[1], k[2])), agg(KAR2, lambda k: (k[1], k[2]))
print(f"итого сумма: БП {sum(v[1] for v in BPI.values()):,.2f} | КА {sum(v[1] for v in KAI.values()):,.2f}")
print(f"позиций: БП {len(BPI)} | КА {len(KAI)} | общих {len(set(BPI) & set(KAI))} | только БП {len(set(BPI) - set(KAI))} | только КА {len(set(KAI) - set(BPI))}")
DI = {k: (BPI.get(k, [0, 0]), KAI.get(k, [0, 0])) for k in set(BPI) | set(KAI)}
DI = {k: v for k, v in DI.items() if abs(v[1][0] - v[0][0]) > 0.0005 or abs(v[1][1] - v[0][1]) > 1}
print(f"позиций с расхождением (кол-во или сумма): {len(DI)}; КА−БП сумма {sum(v[1][1]-v[0][1] for v in DI.values()):,.2f}; "
      f"модуль {sum(abs(v[1][1]-v[0][1]) for v in DI.values()):,.2f}")
low = {k: v for k, v in DI.items() if v[1][0] < v[0][0] - 0.0005}
high = {k: v for k, v in DI.items() if v[1][0] > v[0][0] + 0.0005}
print(f"  ввод в КА МЕНЬШЕ БП по кол-ву: {len(low)} поз.; БОЛЬШЕ: {len(high)} поз.")
# оприходования излишков и списания недостач 2025 (текущее состояние базы)
N, K = datetime.datetime(2025, 1, 1, 5), datetime.datetime(2026, 1, 1, 4, 59, 59)
OPR, SPS = defaultdict(lambda: [0.0, 0.0, set()]), defaultdict(lambda: [0.0, 0.0, set()])
for dname, T in (("ОприходованиеИзлишковТоваров", OPR), ("СписаниеНедостачТоваров", SPS)):
    for r in q(f"""ВЫБРАТЬ Т.Номенклатура КАК Н, Т.Количество КАК Кл, Т.Сумма КАК См, Т.Ссылка.Склад КАК Ск, Т.Ссылка КАК Д, Т.Ссылка.Организация КАК О
ИЗ Документ.{dname}.Товары КАК Т ГДЕ Т.Ссылка.Проведен И Т.Ссылка.Дата МЕЖДУ &Н И &К""", Н=N, К=K):
        if not okorg(s(r["О"])): continue
        x = T[nk(s(r["Н"]))]; x[0] += r["Кл"] or 0; x[1] += r["См"] or 0; x[2].add(s(r["Д"])[-30:])
print(f"2025: оприходований излишков по {len(OPR)} поз. на {sum(v[1] for v in OPR.values()):,.2f}; списаний недостач по {len(SPS)} поз. на {sum(v[1] for v in SPS.values()):,.2f}")
def cover(a, b): return min(a, b)
m_low = [(k, v, OPR[k]) for k, v in low.items() if k in OPR]
m_high = [(k, v, SPS[k]) for k, v in high.items() if k in SPS]
ql = sum(cover(v[0][0] - v[1][0], o[0]) for k, v, o in m_low)
print(f"СВЯЗЬ: ввод занижен И есть оприходование 2025: {len(m_low)} поз. (кол-во, закрываемое оприходованием: {ql:,.3f}); "
      f"ввод завышен И есть списание 2025: {len(m_high)} поз.")
print("ТОП-15 занижен ввод + оприходование (позиция | БП кол | КА кол | разница | оприх. 2025 кол):")
for k, v, o in sorted(m_low, key=lambda x: -abs(x[1][0][1] - x[1][1][1]))[:15]:
    print(f"  {k[:55]:<55} | {v[0][0]:>10,.3f} | {v[1][0]:>10,.3f} | {v[0][0]-v[1][0]:>10,.3f} | {o[0]:>10,.3f}")
P = r"D:\anescom_edo\data\reports\vvod_tovary_BP_KA_01-01-2025.csv"
with open(P, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["Уровень", "Номенклатура", "Склад", "БП кол", "БП сумма", "КА кол", "КА сумма", "КА−БП кол", "КА−БП сумма",
                "Оприх. 2025 кол", "Оприх. 2025 сумма", "Оприх. документы", "Списание 2025 кол", "Списание 2025 сумма", "Списание документы"])
    for k, (b, a) in sorted(DI.items(), key=lambda x: -abs(x[1][1][1] - x[1][0][1])):
        o, sp = OPR.get(k, [0, 0, set()]), SPS.get(k, [0, 0, set()])
        w.writerow(["номенклатура", k, "", b[0], round(b[1], 2), a[0], round(a[1], 2), round(a[0] - b[0], 4), round(a[1] - b[1], 2),
                    o[0], round(o[1], 2), ", ".join(sorted(o[2]))[:400], sp[0], round(sp[1], 2), ", ".join(sorted(sp[2]))[:400]])
    for kw in sorted(set(BPW) | set(KAW)):
        b, a = BPW.get(kw, [0, 0]), KAW.get(kw, [0, 0])
        if kw[0] in DI and (abs(a[0] - b[0]) > 0.0005 or abs(a[1] - b[1]) > 1):
            w.writerow(["номенклатура+склад", kw[0], kw[1], b[0], round(b[1], 2), a[0], round(a[1], 2), round(a[0] - b[0], 4), round(a[1] - b[1], 2)])
print("CSV:", P)
log(f"21-28 сверка ввода остатков товаров БП↔КА: расхождений {len(DI)} поз., занижен+оприходование {len(m_low)}, завышен+списание {len(m_high)}")
