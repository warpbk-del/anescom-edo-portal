"""6м. Почему долг на 31.12.2024 (908 млн) втрое выше 2023 (293 млн): python diag_debts.py
Остатки по счетам 121x/351x на конец каждого года, обороты 2024 по корр. счетам, крупнейшие клиенты 2024 vs 2023,
сверка с документами БП (реализации − возвраты − оплаты) по крупнейшим."""
from collections import defaultdict
from lg import rows, num, out

M = 1e6
bal = defaultdict(float)          # (год, счёт) → остаток на конец года (накопительно)
mon = defaultdict(float)          # (месяц, счёт)
cli = defaultdict(float)          # (месяц, ключ) нетто
corr = defaultdict(lambda: [0.0, 0.0])
names = {}
for r in rows("bp", "accsub_Типовой", ["Период", "Счет", "КорСчет", "Субконто1", "Субконто1_key", "СуммаДт", "СуммаКт"]):
    a = r["Счет"]
    if not (a.startswith("121") or a.startswith("351")):
        continue
    m = r["Период"][:7]
    v = num(r["СуммаДт"]) - num(r["СуммаКт"])
    mon[(m, a)] += v
    cli[(m, r["Субконто1_key"])] += v
    names[r["Субконто1_key"]] = r["Субконто1"]
    if m[:4] == "2024":
        x = corr[(a, r["КорСчет"])]
        x[0] += num(r["СуммаДт"]); x[1] += num(r["СуммаКт"])
accs = sorted({a for _m, a in mon})
out("остаток на 31.12 по счетам (Дт−Кт), млн: " + " | ".join(accs))
run = defaultdict(float)
for y in range(2019, 2025):
    for (m, a), v in mon.items():
        if m[:4] == str(y):
            run[a] += v
    out(f"{y}: " + " | ".join(f"{run[a] / M:,.1f}" for a in accs))
out("2024 обороты по корр. счетам (Дт / Кт), млн:")
for (a, k), (d, c) in sorted(corr.items(), key=lambda x: -(x[1][0] + x[1][1]))[:14]:
    out(f"  {a} ↔ {k or '-'}: {d / M:,.1f} / {c / M:,.1f}")
# помесячно 2024 — где скачок
cum = sum(v for (m, a), v in mon.items() if m < "2024")
line = []
for mm in range(1, 13):
    k = f"2024-{mm:02d}"
    cum += sum(v for (m, a), v in mon.items() if m == k)
    line.append(f"{mm:02d}:{cum / M:,.0f}")
out("нетто-долг на конец месяца 2024, млн: " + " ".join(line))
# крупнейшие клиенты
b23, b24 = defaultdict(float), defaultdict(float)
for (m, key), v in cli.items():
    if m <= "2023-12":
        b23[key] += v
    if m <= "2024-12":
        b24[key] += v
top = sorted(b24, key=lambda k: -(b24[k] - b23[k]))[:15]
out("рост долга за 2024 (на 31.12.2023 → 31.12.2024), млн:")
for k in top:
    out(f"  {names.get(k, k)[:40]}: {b23[k] / M:,.1f} → {b24[k] / M:,.1f}")

# ---- контроль по оборотам ДтКт (acc_Типовой): остатки 1210 и 3510 целиком, без разреза по клиентам
tot = defaultdict(float)
for r in rows("bp", "acc_Типовой", ["Период", "СчетДт", "СчетКт", "Сумма"]):
    s = num(r["Сумма"])
    for acc, sign in ((r["СчетДт"], 1), (r["СчетКт"], -1)):
        if acc[:3] in ("121", "351"):
            tot[(r["Период"][:4], acc)] += sign * s
acc2 = sorted({a for _y, a in tot})
run2 = defaultdict(float)
out("по ДтКт, остаток Дт−Кт на 31.12, млн: " + " | ".join(acc2))
for y in range(2019, 2025):
    for a in acc2:
        run2[a] += tot.get((str(y), a), 0)
    out(f"{y}: " + " | ".join(f"{run2[a] / M:,.1f}" for a in acc2))
n351 = sum(1 for r in rows("bp", "accsub_Типовой", ["Счет"]) if r["Счет"].startswith("351"))
out(f"строк 351x в обороте по субконто: {n351}")
