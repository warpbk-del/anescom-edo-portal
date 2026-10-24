# 21-8: лишние «Списание недостач ↔ Оприходование излишков» одного товара на одном складе (±1 мес.) — убрать (решение пользователя 19:44: «решай сам»).
# Если пара документов взаимно гасится полностью — оба на удаление. Иначе — из обоих удалить совпадающие строки (одинаковый товар и количество) и перепровести.
from collections import defaultdict
DRY = globals().get("DRY", True)
W = q("""ВЫБРАТЬ Д.Ссылка КАК Д, Д.Дата КАК Дт, Д.Склад КАК С ИЗ Документ.СписаниеНедостачТоваров КАК Д ГДЕ Д.Проведен И Д.Дата >= &Н""", Н=datetime.datetime(2025, 1, 1))
R = q("""ВЫБРАТЬ Д.Ссылка КАК Д, Д.Дата КАК Дт, Д.Склад КАК С ИЗ Документ.ОприходованиеИзлишковТоваров КАК Д ГДЕ Д.Проведен И Д.Дата >= &Н""", Н=datetime.datetime(2025, 1, 1))
print("списаний", len(W), "оприходований", len(R))


def lines(ref):
    o = ref.ПолучитьОбъект(); out = defaultdict(float)
    for i in range(o.Товары.Количество()):
        t = o.Товары.Получить(i)
        out[(s(t.Номенклатура), s(getattr(t, "Характеристика", "")))] += t.Количество
    return out


def mdiff(a, b):
    return abs((a.year * 12 + a.month) - (b.year * 12 + b.month))


plan = []
WL = {s(w["Д"]): lines(w["Д"]) for w in W}
for r in R:
    rl = lines(r["Д"])
    for w in W:
        if s(w["С"]) != s(r["С"]) or mdiff(w["Дт"], r["Дт"]) > 1:
            continue
        wl = WL[s(w["Д"])]
        common = {k for k in rl if k in wl and abs(rl[k] - wl[k]) < 0.0005}
        if not common:
            continue
        full = set(rl) == common and set(wl) == common
        plan.append((w, r, common, full))
print("пар документов:", len(plan), "| полностью гасятся:", sum(1 for p in plan if p[3]))
for w, r, common, full in plan:
    print(f"  {'ПОЛН' if full else 'част'} {s(w['Д'])[-40:]} ↔ {s(r['Д'])[-40:]} | {s(r['С'])[:18]} | строк {len(common)}")
if not DRY:
    done = set()
    for w, r, common, full in plan:
        for ref in (w["Д"], r["Д"]):
            if s(ref) in done:
                continue
        try:
            if full:
                for ref in (w["Д"], r["Д"]):
                    if s(ref) not in done:
                        o = ref.ПолучитьОбъект(); o.УстановитьПометкуУдаления(True); done.add(s(ref))
                log(f"21-8 пара полностью гасится — на удаление: {s(w['Д'])} и {s(r['Д'])}")
            else:
                for ref in (w["Д"], r["Д"]):
                    o = ref.ПолучитьОбъект()
                    for i in range(o.Товары.Количество() - 1, -1, -1):
                        t = o.Товары.Получить(i)
                        if (s(t.Номенклатура), s(getattr(t, "Характеристика", ""))) in common:
                            o.Товары.Удалить(i)
                    if o.Товары.Количество() == 0:
                        o.УстановитьПометкуУдаления(True)
                    else:
                        o.Записать(ib.РежимЗаписиДокумента.Проведение)
                log(f"21-8 из пары {s(w['Д'])} / {s(r['Д'])} убраны совпадающие строки: {len(common)}")
        except Exception as e:
            log(f"21-8 ОШИБКА {s(w['Д'])} / {s(r['Д'])}: {str(e)[-150:]}")
