# 21-28c (только чтение, после openGoods/openGoods2): ПЛАН исправления ввода остатков вместо оприходований/списаний 2025.
# Оприходование 2025 товара X на складе W при недовводе X (КА<БП): ввод на W += r, оприходование −= r, r = min(недоввод, кол-во строки).
# Списание 2025 X со склада W при переводе X (КА>БП): ввод на W −= r, списание −= r, r ≤ перевод, ≤ ввода на W и ≤ минимального остатка W
# с 01.01.2025 до даты списания (чтобы не уйти в минус).
import csv
from collections import defaultdict
N, K = datetime.datetime(2025, 1, 1, 5), datetime.datetime(2026, 1, 1, 4, 59, 59)
# 1) чем введены остатки товаров в КА
_vv = q("""ВЫБРАТЬ Т.Регистратор КАК Р, КОЛИЧЕСТВО(*) КАК С ИЗ РегистрНакопления.ТоварыНаСкладах КАК Т ГДЕ Т.Период < &Н СГРУППИРОВАТЬ ПО Т.Регистратор""", Н=N)
print("ввод товаров: документов", len(_vv), "| строк", sum(r["С"] for r in _vv), "|", "; ".join(s(r["Р"])[-45:] for r in _vv[:6]))
KAW2 = defaultdict(float)
for (a, it, wh), (qn, sm) in KAR2.items(): KAW2[(it, wh)] += qn
NEED = {k: v[0][0] - v[1][0] for k, v in DI2.items()}          # >0 недоввод, <0 перевод (по номенклатуре, с учётом сопоставления имён)
rows = {"ОприходованиеИзлишковТоваров": [], "СписаниеНедостачТоваров": []}
for dname in rows:
    for r in q(f"""ВЫБРАТЬ Т.Ссылка КАК Д, Т.Ссылка.Дата КАК Дт, Т.НомерСтроки КАК НС, Т.Номенклатура КАК Н, Т.Количество КАК Кл,
 {'Т.Сумма' if dname.startswith('Оприх') else '0'} КАК См, Т.Ссылка.Склад КАК Ск, Т.Ссылка.Организация КАК О
ИЗ Документ.{dname}.Товары КАК Т ГДЕ Т.Ссылка.Проведен И Т.Ссылка.Дата МЕЖДУ &Н И &К УПОРЯДОЧИТЬ ПО Т.Ссылка.Дата""", Н=N, К=K):
        if not okorg(s(r["О"])): continue
        rows[dname].append([nk(s(r["Н"])), nk(s(r["Ск"])), r["Кл"] or 0, r["См"] or 0, s(r["Д"])[-40:], r["Дт"], r["НС"]])
left = dict(NEED); PLAN = []
for it, wh, qn, sm, dn, dt, ns in rows["ОприходованиеИзлишковТоваров"]:
    nd = left.get(it, 0)
    if nd > 0.0005 and qn > 0:
        rr = min(nd, qn); left[it] = nd - rr
        PLAN.append(["оприходование", it, wh, dn, str(dt)[:10], ns, qn, rr, round(sm * rr / qn, 2)])
# списания: нужен минимальный остаток склада между 01.01.2025 и датой списания
cand = [x for x in rows["СписаниеНедостачТоваров"] if left.get(x[0], 0) < -0.0005]
items = sorted({x[0] for x in cand})
MOV = defaultdict(list)
if items:
    for r in q("""ВЫБРАТЬ Т.Номенклатура КАК Н, Т.Склад КАК Ск, Т.Период КАК П, Т.ВНаличии КАК Кл, Т.ВидДвижения КАК ВД
ИЗ РегистрНакопления.ТоварыНаСкладах КАК Т ГДЕ Т.Период МЕЖДУ &Н И &К И Т.Номенклатура В (ВЫБРАТЬ РАЗЛИЧНЫЕ С.Номенклатура ИЗ Документ.СписаниеНедостачТоваров.Товары КАК С ГДЕ С.Ссылка.Проведен И С.Ссылка.Дата МЕЖДУ &Н И &К) УПОРЯДОЧИТЬ ПО Т.Период""", Н=N, К=K):
        it = nk(s(r["Н"]))
        if it in left and left[it] < -0.0005:
            sg = 1 if "Приход" in s(r["ВД"]) else -1
            MOV[(it, nk(s(r["Ск"])))].append((r["П"], sg * (r["Кл"] or 0)))
for it, wh, qn, sm, dn, dt, ns in cand:
    ov = -left.get(it, 0)
    if ov <= 0.0005 or qn <= 0: continue
    bal = KAW2.get((it, wh), 0); mn = bal
    for p, d in MOV.get((it, wh), []):
        if p >= dt: break
        bal += d; mn = min(mn, bal)
    rr = min(ov, qn, max(mn, 0), KAW2.get((it, wh), 0))
    if rr > 0.0005:
        left[it] = left[it] + rr; KAW2[(it, wh)] -= rr
        PLAN.append(["списание", it, wh, dn, str(dt)[:10], ns, qn, rr, 0])
po = [x for x in PLAN if x[0] == "оприходование"]; ps = [x for x in PLAN if x[0] == "списание"]
def full(lst): return len({x[3] for x in lst if abs(x[6] - x[7]) < 0.0005})
print(f"ПЛАН оприходования: строк {len(po)}, док. {len({x[3] for x in po})}, кол-во {sum(x[7] for x in po):,.3f}, сумма {sum(x[8] for x in po):,.2f}; "
      f"строк убирается целиком {sum(1 for x in po if abs(x[6]-x[7])<0.0005)}")
print(f"ПЛАН списания: строк {len(ps)}, док. {len({x[3] for x in ps})}, кол-во {sum(x[7] for x in ps):,.3f}; "
      f"строк убирается целиком {sum(1 for x in ps if abs(x[6]-x[7])<0.0005)}")
print(f"ввод остатков 31.12.2024: + {sum(x[7] for x in po):,.3f} ед. по {len({(x[1],x[2]) for x in po})} поз./складам; − {sum(x[7] for x in ps):,.3f} ед. по {len({(x[1],x[2]) for x in ps})}")
P = r"D:\anescom_edo\data\reports\plan_vvod_vmesto_oprih_spisan_2025.csv"
with open(P, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";"); w.writerow(["Что", "Номенклатура", "Склад", "Документ", "Дата", "Строка", "Кол-во в строке", "Убрать кол-во", "Убрать сумма"])
    for x in PLAN: w.writerow(x)
print("CSV:", P)
GPLAN = PLAN
log(f"21-28c план: оприходования {len(po)} строк/{sum(x[8] for x in po):,.0f}; списания {len(ps)} строк; ввод +{sum(x[7] for x in po):,.0f}/−{sum(x[7] for x in ps):,.0f} ед.")
