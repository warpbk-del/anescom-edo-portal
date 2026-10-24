# Выгрузка сверки ввода остатков БП (31.12.2024) ↔ КА (01.01.2025) в CSV для бухгалтера (Excel откроет).
import csv
fn = r"D:\anescom_edo\data\reports\Сверка_ввода_остатков_БП_КА_31.12.2024.csv"
with open(fn, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["Счёт", "Ключ (БИН/ИИН/счёт/артикул)", "Наименование (БП)", "Наименование (КА)", "Остаток БП 31.12.2024", "Остаток КА 01.01.2025", "Разница КА−БП"])
    for (a, k), (b, c) in sorted(KD.items(), key=lambda x: (x[0][0], -abs(x[1][1] - x[1][0]))):
        w.writerow([a, k, BPN.get((a, k), ""), s(KAR[(a, k)]) if (a, k) in KAR else "", f"{b:.2f}".replace(".", ","), f"{c:.2f}".replace(".", ","), f"{c - b:.2f}".replace(".", ",")])
print("записано:", fn, "строк", len(KD))
