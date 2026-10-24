import csv
fn = r"D:\anescom_edo\data\reports\Сверка_расчетов_по_контрагентам_БП_КА_31.12.2024.csv"
with open(fn, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["Контрагент", "Нетто БП 31.12.2024", "Счета БП", "Нетто КА 01.01.2025", "Счета КА", "Разница КА−БП", "Вид"])
    for n, b, c, ab_, ak_ in NET2:
        kind = "нет в КА" if abs(c) < 0.01 else ("нет в БП" if abs(b) < 0.01 else "разная сумма")
        w.writerow([n, f"{b:.2f}".replace(".", ","), ab_, f"{c:.2f}".replace(".", ","), ak_, f"{c - b:.2f}".replace(".", ","), kind])
print("записано", fn, len(NET2))
