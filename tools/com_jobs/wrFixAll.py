# 21-9: по результатам wrMatch (MATCH в памяти): уменьшить на совпавшее количество и оприходование излишков, и предшествующее списание/потребление/расход в производство того же товара.
# Строка с нулём — удаляется; пустой документ — на удаление. Остатки товаров на конец не меняются. DRY = True — только план.
from collections import defaultdict
DRY = globals().get("DRY", True)
red = defaultdict(lambda: defaultdict(float))   # док -> товар -> уменьшить на
refs = {}
for t, o, r, m, k in MATCH:
    red[s(o["Р"])][k] += m; refs[s(o["Р"])] = o["Р"]
    red[s(r["Р"])][k] += m; refs[s(r["Р"])] = r["Р"]
TP = {"Оприходование излишков": "Товары", "Списание недостач": "Товары", "Внутреннее потребление": "Товары", "Производство без заказа": "МатериалыИРаботы"}
print("документов к правке:", len(red), "| строк-товаров:", sum(len(v) for v in red.values()))
ok = err = emptied = 0
for dname, items in sorted(red.items()):
    tpn = next(v for kx, v in TP.items() if dname.startswith(kx))
    if DRY:
        continue
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
