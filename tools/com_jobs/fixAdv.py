# Исправление 21-4: расчёты с контрагентами на 30.09.2026 (в КОПИИ), одна Операция (регл.) по образцу 00НФ-000292 (там бухгалтер тоже делал Дт3310 Кт1710).
# Шаг A: внутри (счёт, контрагент, договор, субконто3) сальдо разнесено по разным подразделениям с разными знаками
#        → переносим всё на основное подразделение (непустое с наибольшей суммой; иначе пустое).
# Шаг B: по одному договору аванс выданный 1710 и долг поставщику 3310 → Дт3310 Кт1710; долг покупателя 1210 и аванс полученный 3510 → Дт3510 Кт1210.
# Валютные договоры (есть валютная сумма) — не трогаем. DRY = True — только показать план.
from collections import defaultdict
DRY = globals().get("DRY", True)
D30 = datetime.datetime(2026, 9, 30, 23, 59, 59)
DOC_DATE = datetime.datetime(2026, 9, 30, 12, 0, 0)
rows = q("""ВЫБРАТЬ Т.Счет КАК Сч, Т.Счет.Код КАК Код, Т.Организация КАК Орг, Т.Субконто1 КАК С1, Т.Субконто2 КАК С2, Т.Субконто3 КАК С3, Т.Подразделение КАК П,
  Т.СуммаОстатокДт - Т.СуммаОстатокКт КАК Б, ЕСТЬNULL(Т.ВалютнаяСуммаОстатокДт, 0) + ЕСТЬNULL(Т.ВалютнаяСуммаОстатокКт, 0) КАК В
ИЗ РегистрБухгалтерии.{REG}.Остатки(&Д, Счет.Код В ("1210", "3510", "1710", "3310"), , ) КАК Т""", Д=D30)
print("строк сальдо:", len(rows))
grp = defaultdict(list)
for r in rows:
    if abs(r["В"]) > 0.001:
        continue
    grp[(r["Код"], s(r["Орг"]), s(r["С1"]), s(r["С2"]), s(r["С3"]))].append(r)
entries = []  # (dt_row_like, kt_row_like, amount, note)  row_like = dict(Сч, Орг, С1, С2, С3, П)


def rl(r, П=None):
    return dict(Сч=r["Сч"], Орг=r["Орг"], С1=r["С1"], С2=r["С2"], С3=r["С3"], П=r["П"] if П is None else П)


cons = {}  # key -> (row_like at target dept, balance)
for k, rs in grp.items():
    tot = round(sum(r["Б"] for r in rs), 2)
    nonempty = [r for r in rs if s(r["П"]).strip()]
    tgt = max(nonempty or rs, key=lambda r: abs(r["Б"]))
    if len(rs) > 1:
        for r in rs:
            if r is tgt or abs(r["Б"]) < 0.01:
                continue
            b = round(r["Б"], 2)
            if b > 0:
                entries.append((rl(tgt), rl(r), b, "A"))
            else:
                entries.append((rl(r), rl(tgt), -b, "A"))
    cons[k] = (rl(tgt), tot)
nA = len(entries); sA = sum(e[2] for e in entries)
# шаг B
by_contract = defaultdict(dict)
for (code, org, c1, c2, c3), (row, b) in cons.items():
    by_contract[(org, c1, c2)].setdefault(code, []).append([row, b])
for key, d in by_contract.items():
    for adv_acc, debt_acc, adv_sign in (("1710", "3310", 1), ("1210", "3510", 1)):
        A = [x for x in d.get(adv_acc, []) if x[1] > 0.009]
        B = [x for x in d.get(debt_acc, []) if x[1] < -0.009]
        for a in A:
            for b in B:
                m = round(min(a[1], -b[1]), 2)
                if m <= 0:
                    continue
                entries.append((b[0], a[0], m, "B" + debt_acc))   # Дт 3310/3510  Кт 1710/1210
                a[1] -= m; b[1] += m
nB = len(entries) - nA; sB = sum(e[2] for e in entries[nA:])
print(f"Шаг A (подразделения): проводок {nA}, сумма {sA:,.2f}")
print(f"Шаг B (зачёт аванса по договору): проводок {nB}, сумма {sB:,.2f}")
for e in sorted(entries[nA:], key=lambda e: -e[2])[:15]:
    print("  B", e[3], s(e[0]["С1"])[:26], "|", s(e[0]["С2"])[:30], "|", f"{e[2]:,.2f}")
def write_moves(new):
    ns = new.Движения.Хозрасчетный
    ns.Отбор.Регистратор.Установить(new.Ссылка)
    for dt, kt, amt, note in entries:
        z = ns.Добавить()
        z.Период = DOC_DATE
        z.Организация = dt["Орг"]
        z.СчетДт = dt["Сч"]; z.СчетКт = kt["Сч"]
        for side, x in (("Дт", dt), ("Кт", kt)):
            acc = x["Сч"]
            sub = getattr(z, "Субконто" + side)
            for i in range(acc.ВидыСубконто.Количество()):
                vid = acc.ВидыСубконто.Получить(i).ВидСубконто
                val = x["С" + str(i + 1)]
                if val is not None:
                    sub.Вставить(vid, val)
            setattr(z, "Подразделение" + side, x["П"])
        z.Сумма = amt
        z.Содержание = "Аудит 24.10: " + ("подразделение" if note == "A" else "зачёт аванса")
    ns.Записать()
    new.Записать(ib.РежимЗаписиДокумента.Проведение)



if not DRY and entries:
    tpl = q("""ВЫБРАТЬ ПЕРВЫЕ 1 Т.Регистратор КАК Д ИЗ РегистрБухгалтерии.{REG}.ДвиженияССубконто(&Н, &К, СчетДт.Код = "3310" И СчетКт.Код = "1710") КАК Т""",
            Н=datetime.datetime(2025, 12, 31), К=datetime.datetime(2025, 12, 31, 23, 59, 59))[0]["Д"]
    oo = tpl.ПолучитьОбъект()
    new = oo.Скопировать()
    new.Дата = DOC_DATE
    new.Содержание = "Расчёты с контрагентами: перенос сальдо на основное подразделение и зачёт авансов по договорам (на 30.09.2026)"
    new.Комментарий = new.Содержание + " [аудит 24.10.2026]"
    new.СуммаОперации = round(sA + sB, 2)
    ib.НачатьТранзакцию()
    try:
        new.Записать()
        write_moves(new)
        ib.ЗафиксироватьТранзакцию()
    except Exception:
        ib.ОтменитьТранзакцию()
        raise




if not DRY and entries:
    log(f"21-4 авансы: создана {s(new.Ссылка)}: A {nA} пров. {sA:,.2f}; B {nB} пров. {sB:,.2f}")
    left = q("""ВЫБРАТЬ Т.Субконто1 КАК С1, Т.Субконто2 КАК С2, СУММА(ВЫБОР КОГДА Т.Счет.Код В ("1710","1210") ТОГДА Т.СуммаОстатокДт ИНАЧЕ 0 КОНЕЦ) КАК А,
      СУММА(ВЫБОР КОГДА Т.Счет.Код В ("3310","3510") ТОГДА Т.СуммаОстатокКт ИНАЧЕ 0 КОНЕЦ) КАК Д
      ИЗ РегистрБухгалтерии.{REG}.Остатки(&Д, Счет.Код В ("1210", "3510", "1710", "3310"), , ) КАК Т СГРУППИРОВАТЬ ПО Т.Субконто1, Т.Субконто2""", Д=D30)
    both = [r for r in left if r["А"] > 1 and r["Д"] > 1]
    print("ПОСЛЕ: договоров, где одновременно аванс и долг:", len(both))
    for r in both[:10]:
        print("  ", s(r["С1"])[:26], "|", s(r["С2"])[:30], "| аванс/дебит", round(r["А"], 2), "| долг/аванс получ.", round(r["Д"], 2))
