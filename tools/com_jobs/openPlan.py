# План корректировки ввода остатков (не расчёты): для строк OPEN_D найти ссылку субконто в КА; итоги по счетам — найдено/не найдено.
from collections import defaultdict
SKIP = ("1210", "3510", "1710", "3310", "0000", "000")
PL = ib.Метаданные.РегистрыБухгалтерии.Получить(0).ПланСчетов.Имя
accref = {}
def acc(c):
    if c not in accref:
        r = q(f'ВЫБРАТЬ С.Ссылка КАК С ИЗ ПланСчетов.{PL} КАК С ГДЕ С.Код = "{c}"')
        accref[c] = r[0]["С"] if r else None
    return accref[c]
# индекс КА: все субконто1 по счёту (из ОстаткиИОбороты за 2025) по нормализованному имени
KAIDX = defaultdict(dict)
for r in q("""ВЫБРАТЬ РАЗЛИЧНЫЕ Т.Счет.Код КАК С, Т.Субконто1 КАК С1 ИЗ РегистрБухгалтерии.{REG}.ОстаткиИОбороты(&Н, &К, , , , , ) КАК Т""",
           Н=datetime.datetime(2025, 1, 1, 6), К=datetime.datetime(2026, 9, 30)):
    KAIDX[r["С"]][nk(s(r["С1"]))] = r["С1"]
PLAN = []; stat = defaultdict(lambda: [0, 0, 0.0, 0.0])
for (a, sb), (b, k) in OPEN_D.items():
    if a in SKIP or abs(k - b) < 0.5:
        continue
    A = acc(a)
    if A is None:
        stat[a][1] += 1; stat[a][3] += abs(k - b); continue
    nsub = A.ВидыСубконто.Количество()
    ref = None
    if nsub == 0 or not sb:
        ref = "—"
    else:
        ref = KAIDX[a].get(sb)
        if ref is None:
            for a2, d in KAIDX.items():
                if sb in d:
                    ref = d[sb]; break
    if ref is None:
        stat[a][1] += 1; stat[a][3] += abs(k - b)
    else:
        stat[a][0] += 1; stat[a][2] += abs(k - b); PLAN.append((a, sb, ref, round(b - k, 2)))   # b−k: на сколько изменить КА
print("счёт | найдено строк (сумма) | не найдено строк (сумма)")
for a, (n1, n2, s1, s2) in sorted(stat.items(), key=lambda x: -(x[1][2] + x[1][3])):
    print(f"  {a:<7} {n1:>4} ({s1:>15,.2f}) | {n2:>4} ({s2:>15,.2f})")
print("к корректировке строк:", len(PLAN), "| изменение итога (дельта в 0000):", round(-sum(x[3] for x in PLAN), 2))
