# 21-22 ИСПРАВЛЕНИЯ БУ (копия) на 30.06.2025 — одна «Операция (бух)» на каждый вид, только бухучёт (оперативный учёт не трогаем):
#  a) клиенты: зачёт аванса 3510 в долг 1210 (один контрагент, одна организация) — Дт 3510 Кт 1210
#  b) поставщики: зачёт Дт-сальдо 3310 с Кт-сальдо 1710 того же контрагента — Дт 1710 Кт 3310
#  c) зарплата: внутри сотрудника Дт-сальдо 3350 в одном подразделении против Кт-сальдо в другом — Дт 3350(Кт-строка) Кт 3350(Дт-строка)
#  d) банк 1030: минус по подразделению закрыть с плюса того же счёта (подразделение головной) — Дт 1030(минус) Кт 1030(плюс)
# DRY=True по умолчанию. STEPS="abcd".
DRY = globals().get("DRY", True); STEPS = globals().get("STEPS", "abcd")
PL = ib.Метаданные.РегистрыБухгалтерии.Получить(0).ПланСчетов.Имя
D = datetime.datetime(2025, 7, 1, 6)                 # остатки «на конец 30.06.2025» (сдвиг COM −5 ч)
DOC_DATE = datetime.datetime(2025, 6, 30, 17, 0, 0)  # → 30.06.2025 12:00 в базе
def rows_of(acc):
    return q(f"""ВЫБРАТЬ О.Организация КАК Орг, О.Подразделение КАК П, О.Субконто1 КАК С1, О.Субконто2 КАК С2, О.Субконто3 КАК С3,
      О.СуммаОстатокДт - О.СуммаОстатокКт КАК Ост ИЗ РегистрБухгалтерии.{{REG}}.Остатки(&Д, Счет.Код = "{acc}", , ) КАК О""", Д=D)
def accref(c): return q(f'ВЫБРАТЬ С.Ссылка КАК С ИЗ ПланСчетов.{PL} КАК С ГДЕ С.Код = "{c}"')[0]["С"]
def subs(r): return [r["С1"], r["С2"], r["С3"]]
plans = {}
# a) клиенты
if "a" in STEPS:
    deb = [r for r in rows_of("1210") if r["Ост"] > 0.009]; adv = [r for r in rows_of("3510") if r["Ост"] < -0.009]
    by = {}
    for r in adv: by.setdefault((s(r["Орг"]), s(r["С1"])), []).append([r, -float(r["Ост"])])
    pl = []
    for r in deb:
        left = float(r["Ост"])
        for a in by.get((s(r["Орг"]), s(r["С1"])), []):
            amt = round(min(left, a[1]), 2)
            if amt > 0.009: pl.append(("3510", a[0], "1210", r, amt)); left -= amt; a[1] -= amt
            if left <= 0.009: break
    plans["a"] = (pl, "Зачёт аванса покупателя в погашение задолженности")
# b) поставщики 3310 Дт ↔ 1710 Кт
if "b" in STEPS:
    d33 = [r for r in rows_of("3310") if r["Ост"] > 0.009]; k17 = [r for r in rows_of("1710") if r["Ост"] < -0.009]
    by = {}
    for r in k17: by.setdefault((s(r["Орг"]), s(r["С1"])), []).append([r, -float(r["Ост"])])
    pl = []
    for r in d33:
        left = float(r["Ост"])
        for a in by.get((s(r["Орг"]), s(r["С1"])), []):
            amt = round(min(left, a[1]), 2)
            if amt > 0.009: pl.append(("1710", a[0], "3310", r, amt)); left -= amt; a[1] -= amt
            if left <= 0.009: break
    plans["b"] = (pl, "Зачёт: дебетовое сальдо 3310 против кредитового 1710 того же контрагента")
# c) зарплата по подразделениям
if "c" in STEPS:
    rr = rows_of("3350"); dt = [r for r in rr if r["Ост"] > 0.009]
    kt = {}
    for r in rr:
        if r["Ост"] < -0.009: kt.setdefault((s(r["Орг"]), s(r["С1"])), []).append([r, -float(r["Ост"])])
    pl = []
    for r in dt:
        left = float(r["Ост"])
        for a in kt.get((s(r["Орг"]), s(r["С1"])), []):
            amt = round(min(left, a[1]), 2)
            if amt > 0.009: pl.append(("3350", a[0], "3350", r, amt)); left -= amt; a[1] -= amt
            if left <= 0.009: break
    plans["c"] = (pl, "Взаимозачёт расчётов с работником между подразделениями")
# d) банк 1030 по подразделениям
if "d" in STEPS:
    rr = rows_of("1030"); neg = [r for r in rr if r["Ост"] < -0.009]
    pos = {}
    for r in rr:
        if r["Ост"] > 0.009: pos.setdefault((s(r["Орг"]), s(r["С1"])), []).append([r, float(r["Ост"])])
    pl = []
    for r in neg:
        left = -float(r["Ост"])
        for a in sorted(pos.get((s(r["Орг"]), s(r["С1"])), []), key=lambda x: -x[1]):
            amt = round(min(left, a[1]), 2)
            if amt > 0.009: pl.append(("1030", r, "1030", a[0], amt)); left -= amt; a[1] -= amt
            if left <= 0.009: break
    plans["d"] = (pl, "Перенос остатка банковского счёта между подразделениями")
for k, (pl, title) in plans.items():
    print(f"[{k}] {title}: проводок {len(pl)}, сумма {sum(x[4] for x in pl)/1e6:,.2f} млн")
    for x in pl[:6]: print(f"     Дт {x[0]} {s(x[1]['С1'])[:30]:30} / Кт {x[2]} {s(x[3]['П'])[:20]:20} {x[4]:,.2f}")
if not DRY:
    tpl = q("""ВЫБРАТЬ ПЕРВЫЕ 1 Д.Ссылка КАК Д ИЗ Документ.ОперацияБух КАК Д ГДЕ Д.Комментарий ПОДОБНО "%аудит 24.10.2026%" """)[0]["Д"]
    def put(z, side, a, r):
        sub = getattr(z, "Субконто" + side); vals = subs(r)
        for i in range(a.ВидыСубконто.Количество()):
            if i < 3 and s(vals[i]): sub.Вставить(a.ВидыСубконто.Получить(i).ВидСубконто, vals[i])
        setattr(z, "Подразделение" + side, r["П"])
    for k, (pl, title) in plans.items():
        if not pl: continue
        for org in sorted({s(x[3]["Орг"]) for x in pl}):
            part = [x for x in pl if s(x[3]["Орг"]) == org]
            new = tpl.ПолучитьОбъект().Скопировать(); new.Дата = DOC_DATE
            new.Содержание = title; new.Комментарий = title + " [аудит 24.10.2026, 21-22]"
            new.СуммаОперации = round(sum(x[4] for x in part), 2); new.Записать()
            ns = new.Движения.Хозрасчетный; ns.Отбор.Регистратор.Установить(new.Ссылка)
            for dt_acc, dt_row, kt_acc, kt_row, amt in part:
                a_dt, a_kt = accref(dt_acc), accref(kt_acc)
                z = ns.Добавить(); z.Период = DOC_DATE; z.Организация = kt_row["Орг"]; z.Сумма = amt; z.Содержание = title
                z.СчетДт = a_dt; put(z, "Дт", a_dt, dt_row); z.СчетКт = a_kt; put(z, "Кт", a_kt, kt_row)
            ns.Записать(); new.Записать(ib.РежимЗаписиДокумента.Проведение)
            log(f"21-22{k} {title}: {s(new.Ссылка)} — {len(part)} проводок, {new.СуммаОперации:,.2f} ({org})")
