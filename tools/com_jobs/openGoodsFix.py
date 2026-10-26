# 21-28d: применить план 21-28c в ANESCOM_FIX. DRY=True — только подсчёт.
# 1) убрать сомнительные пары переименований (разные коды цвета), пересчитать план (exec _X28c = openGoods3);
# 2) списания 2025: уменьшить строки; 3) ввод остатков 31.12.2024 (Документ.ВводОстатков, ТЧ Товары): + на склад оприходования,
#    − на склад списания; 4) оприходования 2025: уменьшить строки. Документ пустеет → пометка удаления.
import re
from collections import defaultdict
DRY = globals().get("DRY", True)
CM = " [аудит 26.10.2026 21-28: ввод остатков вместо оприходования/списания]"
def colors(x): return set(re.findall(r"\((\d{4})", x)) | set(re.findall(r"RAL[- ]?(\d{4})", x))
bad = [b for b, (k, r) in MAPN.items() if colors(b) and colors(k) and colors(b) != colors(k)]
for b in bad: MAPN.pop(b)
print(f"пары с разным цветом убраны: {len(bad)}; осталось пар {len(MAPN)}")
BPI2 = defaultdict(lambda: [0.0, 0.0])
for b, v in BPI.items():
    x = BPI2[MAPN[b][0] if b in MAPN else b]; x[0] += v[0]; x[1] += v[1]
DI2 = {k: (BPI2.get(k, [0, 0]), KAI.get(k, [0, 0])) for k in set(BPI2) | set(KAI)}
exec(_X28c)          # пересчёт GPLAN
N0 = datetime.datetime(2025, 1, 1, 5)
# ссылки на строки документов 2025
REF = {}
for dname in ("ОприходованиеИзлишковТоваров", "СписаниеНедостачТоваров"):
    for r in q(f"""ВЫБРАТЬ Т.Ссылка КАК Д, Т.НомерСтроки КАК НС, Т.Номенклатура КАК Н, Т.Ссылка.Склад КАК Ск ИЗ Документ.{dname}.Товары КАК Т
ГДЕ Т.Ссылка.Проведен И Т.Ссылка.Дата МЕЖДУ &Н И &К""", Н=N0, К=datetime.datetime(2026, 1, 1, 4, 59, 59)):
        REF[(s(r["Д"])[-40:], r["НС"])] = (r["Д"], r["Н"], r["Ск"])
# документы ввода остатков товаров по складам
VV = defaultdict(list); VROW = defaultdict(list)
for r in q("""ВЫБРАТЬ Т.Ссылка КАК Д, Т.Ссылка.Склад КАК Ск, Т.Номенклатура КАК Н, Т.НомерСтроки КАК НС, Т.Количество КАК Кл
ИЗ Документ.ВводОстатков.Товары КАК Т ГДЕ Т.Ссылка.Проведен И Т.Ссылка.Дата < &Н""", Н=N0):
    w = nk(s(r["Ск"]))
    if r["Д"] not in VV[w]: VV[w].append(r["Д"])
    VROW[(w, nk(s(r["Н"])))].append((r["Д"], r["НС"], r["Кл"] or 0))
plan = []; skip = 0
for kind, it, wh, dn, dt, ns, qn, rr, sm in GPLAN:
    ref = REF.get((dn, ns))
    if not ref or not VV.get(wh): skip += 1; continue
    plan.append((kind, it, wh, ref, ns, rr, sm, (sm / rr) if (kind == "оприходование" and rr) else 0))
print(f"к применению: строк {len(plan)} (пропущено без документа ввода на складе / без ссылки: {skip})")
byDoc = defaultdict(list); vvChg = defaultdict(lambda: defaultdict(float)); vvRef = {}
for kind, it, wh, ref, ns, rr, sm, pr in plan:
    byDoc[(kind, s(ref[0]))].append((ref[0], ns, rr))
    vvChg[wh][it] += rr if kind == "оприходование" else -rr
    vvRef[(wh, it)] = (ref[1], pr)
nv = sum(1 for w in vvChg for it in vvChg[w] if vvChg[w][it] > 0 and not VROW.get((w, it)))
print(f"документов 2025 к изменению: оприходований {len({k[1] for k in byDoc if k[0]=='оприходование'})}, списаний {len({k[1] for k in byDoc if k[0]=='списание'})}; "
      f"документов ввода {len({s(VV[w][0]) for w in vvChg})}+; новых строк ввода {nv}")
SF = ("Сумма", "СуммаБезНДС", "СуммаНДС", "СуммаРегл", "НДСРегл", "СуммаПР", "СуммаВР", "СуммаСНДС")
def scale(row, new, old):
    row.Количество = round(new, 3)
    try: row.КоличествоУпаковок = round(row.КоличествоУпаковок * new / old, 3) if old else round(new, 3)
    except Exception: pass
    for f in SF:
        try: setattr(row, f, round(getattr(row, f) * new / old, 2))
        except Exception: pass
def msgs(e):
    try:
        arr = ib.ПолучитьСообщенияПользователю(True); m = [arr.Получить(i).Текст for i in range(arr.Количество())]
    except Exception: m = []
    return (" / ".join(m) or str(e))[-220:]
def cut_lines(ref, items):
    obj = ref.ПолучитьОбъект(); tp = obj.Товары
    want = defaultdict(float)
    for _, ns, rr in items: want[ns] += rr
    for i in range(tp.Количество() - 1, -1, -1):
        row = tp.Получить(i); rr = want.get(row.НомерСтроки, 0)
        if rr <= 0.0005: continue
        old = row.Количество; new = old - rr
        if new <= 0.0005: tp.Удалить(i)
        else: scale(row, new, old)
    obj.Комментарий = (obj.Комментарий or "") + CM
    if tp.Количество() == 0: obj.УстановитьПометкуУдаления(True); return "помечен на удаление"
    obj.Записать(ib.РежимЗаписиДокумента.Проведение); return "уменьшен"
okd = err = 0
if not DRY:
    # 1) списания
    for (kind, dn), items in sorted(byDoc.items()):
        if kind != "списание": continue
        try: res = cut_lines(items[0][0], items); okd += 1; log(f"21-28d списание {dn}: {res}, строк {len(items)}")
        except Exception as e: err += 1; print("ОШИБКА", dn[-35:], msgs(e))
    # 2) ввод остатков
    for wh, chg in vvChg.items():
        docs = {}
        for it, d in chg.items():
            if abs(d) < 0.0005: continue
            rows = VROW.get((wh, it), [])
            dref = rows[0][0] if rows else VV[wh][0]; key = s(dref)
            if key not in docs: docs[key] = [dref.ПолучитьОбъект(), 0]
            obj = docs[key][0]; tp = obj.Товары
            idx = [i for i in range(tp.Количество()) if nk(s(tp.Получить(i).Номенклатура)) == it]
            if d > 0:
                if idx:
                    row = tp.Получить(idx[0]); old = row.Количество; scale(row, old + d, old)
                else:
                    tpl = tp.Получить(0); row = tp.Добавить()
                    for c in ("Назначение", "Упаковка", "СтавкаНДС", "ВидЗапасов", "СтатусУказанияСерий", "ГруппаПродукции"):
                        try: setattr(row, c, getattr(tpl, c))
                        except Exception: pass
                    nref, pr = vvRef[(wh, it)]
                    bq, bs = BPI2.get(it, [0, 0]); pr = (bs / bq) if bq > 0.0005 and bs > 0 else pr
                    row.Номенклатура = nref; row.Количество = round(d, 3); row.КоличествоУпаковок = round(d, 3); row.Цена = round(pr, 2)
                    for f in ("Сумма", "СуммаБезНДС", "СуммаРегл", "СуммаСНДС"):
                        try: setattr(row, f, round(pr * d, 2))
                        except Exception: pass
            else:
                left = -d
                for i in sorted(idx, reverse=True):
                    if left <= 0.0005: break
                    row = tp.Получить(i); old = row.Количество; c = min(old, left); left -= c
                    if old - c <= 0.0005: tp.Удалить(i)
                    else: scale(row, old - c, old)
                if left > 0.0005: print("НЕ ХВАТИЛО ввода", wh[:20], it[:40], round(left, 3))
            docs[key][1] += 1
        for key, (obj, n) in docs.items():
            try:
                obj.Комментарий = (obj.Комментарий or "") + CM
                obj.Записать(ib.РежимЗаписиДокумента.Проведение); okd += 1; log(f"21-28d ввод {key[-40:]}: изменено позиций {n}")
            except Exception as e: err += 1; print("ОШИБКА ввода", key[-35:], msgs(e))
    # 3) оприходования
    for (kind, dn), items in sorted(byDoc.items()):
        if kind != "оприходование": continue
        try: res = cut_lines(items[0][0], items); okd += 1; log(f"21-28d оприходование {dn}: {res}, строк {len(items)}")
        except Exception as e: err += 1; print("ОШИБКА", dn[-35:], msgs(e))
print(f"ГОТОВО (DRY={DRY}): документов записано {okd}, ошибок {err}")
