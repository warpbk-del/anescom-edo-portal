# 21-9: по результатам wrMatch (MATCH в памяти): уменьшить на совпавшее количество и оприходование излишков, и предшествующее списание/потребление/расход в производство того же товара.
# Строка с нулём — удаляется; пустой документ — на удаление. Остатки товаров на конец не меняются. DRY = True — только план.
from collections import defaultdict
DRY = globals().get("DRY", True)
red = defaultdict(lambda: defaultdict(float))   # док -> товар -> уменьшить на
refs = {}
for t, o, r, m, k in MATCH:
    red[s(o["Р"])][k] += m; refs[s(o["Р"])] = o["Р"]
    red[s(r["Р"])][k] += m; refs[s(r["Р"])] = r["Р"]
TP = {"ОприходованиеИзлишковТоваров": "Товары", "СписаниеНедостачТоваров": "Товары", "ВнутреннееПотреблениеТоваров": "Товары", "ПроизводствоБезЗаказа": "МатериалыИРаботы"}
import re as _re
DONE = set()
try:
    for ln in open(LOG, encoding="utf-8"):
        mm = _re.search(r"21-9 (.+?): (уменьшено|все строки)", ln)
        if mm:
            DONE.add(mm.group(1))
except Exception:
    pass
print("уже обработано ранее:", len(DONE))
print("документов к правке:", len(red), "| строк-товаров:", sum(len(v) for v in red.values()))
ok = err = emptied = 0
for dname, items in sorted(red.items(), key=lambda x: x[0].startswith("Оприходование")):
    if DRY or dname in DONE:
        continue
    tpn = TP.get(refs[dname].Метаданные().Имя)
    if not tpn:
        log(f"21-9 пропуск {dname}: неизвестный вид"); continue
    try:
        o = refs[dname].ПолучитьОбъект()
        tp = getattr(o, tpn)
        for i in range(tp.Количество() - 1, -1, -1):
            row = tp.Получить(i)
            n = s(row.Номенклатура)
            if items.get(n, 0) <= 0.0005:
                continue
            old = row.Количество
            cut = min(old, items[n]); items[n] -= cut; new = round(old - cut, 3)
            if new <= 0.0005:
                tp.Удалить(i); continue
            row.Количество = new
            for fld in ("КоличествоУпаковок",):
                try:
                    setattr(row, fld, round(getattr(row, fld) * new / old, 3))
                except Exception:
                    pass
            try:
                row.Сумма = round(row.Цена * new, 2)
            except Exception:
                pass
        if tp.Количество() == 0:
            o.УстановитьПометкуУдаления(True); emptied += 1
            log(f"21-9 {dname}: все строки совпали — на удаление")
        else:
            o.Записать(ib.РежимЗаписиДокумента.Проведение)
            log(f"21-9 {dname}: уменьшено по {len(items)} товарам, перепроведён")
        ok += 1
    except Exception as e:
        err += 1
        log(f"21-9 ОШИБКА {dname}: {str(e)[-160:]}")
print(f"готово: {ok}, на удаление {emptied}, ошибок {err}")
