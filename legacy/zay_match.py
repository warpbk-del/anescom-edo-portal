"""6н. Заявки на оплату Bitrix24 ↔ оплаты в 1С: белая = оплата нашлась в БП (до 2025) или КА (с 2025), иначе вторая.
Правило пользователя 19.10.2026 01:44. Запуск на сервере: python zay_match.py <файл заявок .xls> [окно_дней=45]
Сопоставление: та же сумма (до тенге; валютные — в валюте документа БП) и оплата в окне [дата заявки − 3; + окно];
каждая оплата используется один раз; сначала точные суммы, потом ±1%. Пишет zay_match.csv и печатает итог по годам."""
import csv, re, sqlite3, sys, os
from bisect import bisect_left
from collections import defaultdict
from datetime import date, timedelta
from html.parser import HTMLParser
from lg import rows, num, out, exists

DB = os.environ.get("LEGACY_DB", r"D:\anescom_edo\data\analytics.sqlite3")
INTERNAL = ("другой счет", "инкассац", "иностранной валют", "покупка валют", "перемещ", "взнос наличн", "конвертац")

# ---- заявки
class T(HTMLParser):   # выгрузка Bitrix24 «.xls» — это HTML-таблица; pandas на сервере может не быть
    def __init__(self):
        super().__init__(); self.rows, self.row, self.cell, self.inc = [], None, "", False
    def handle_starttag(self, t, a):
        if t == "tr": self.row = []
        elif t == "td": self.inc, self.cell = True, ""
        elif t == "br" and self.inc: self.cell += " "
    def handle_endtag(self, t):
        if t == "td" and self.row is not None: self.row.append(self.cell.strip()); self.inc = False
        elif t == "tr" and self.row is not None: self.rows.append(self.row); self.row = None
    def handle_data(self, d):
        if self.inc: self.cell += d


def read_requests(F):
    """Строки выгрузки Bitrix24 → (заголовок, список словарей)."""
    t = T()
    t.feed(open(F, encoding="utf-8-sig", errors="replace").read())
    return t.rows[0], [dict(zip(t.rows[0], r)) for r in t.rows[1:]]


def amt(s):
    m = re.search(r"-?\d[\d\s]*(?:[.,]\d+)?", str(s).replace("\xa0", " "))
    return float(m.group(0).replace(" ", "").replace(",", ".")) if m else 0.0


def cur(s):
    s = str(s)
    return "RUB" if "руб" in s else "USD" if "$" in s else "EUR" if "€" in s else "KZT"


RATE = {"RUB": {2020: 5.73, 2021: 5.78, 2022: 6.85, 2023: 5.43, 2024: 5.11, 2025: 6.2, 2026: 6.0},
        "USD": {2020: 413, 2021: 426, 2022: 461, 2023: 456, 2024: 469, 2025: 515, 2026: 510},
        "EUR": {2020: 471, 2021: 504, 2022: 486, 2023: 493, 2024: 508, 2025: 585, 2026: 590}}


def match(F, WIN=45):
    """→ (Z, P): заявки (z['pay'] — индекс найденной оплаты в P) и оплаты 1С."""
    head, recs = read_requests(F)
    col_sum = [c for c in head if c.startswith("Сумма")][0]
    col_att = [c for c in head if c.startswith("Вложения")][0]
    Z = []
    for i, r in enumerate(recs):
        try:
            d = date(int(str(r["Дата"])[6:10]), int(str(r["Дата"])[3:5]), int(str(r["Дата"])[0:2]))
        except Exception:
            continue
        Z.append({"i": i, "d": d, "sum": amt(r[col_sum]), "cur": cur(r[col_sum]), "city": r.get("Город", ""),
                  "purpose": r.get("Назначение платежа", ""), "text": str(r.get("Краткое содержание (Наименование товара и услуг)", ""))[:80],
                  "att": str(r[col_att])[:80], "r": r})
    out(f"заявок: {len(Z)}")

    # ---- оплаты: БП (документы списания), КА (an_cashflow out)
    P = []   # (дата, сумма, валюта, база, номер, контрагент)
    for d in ("ПлатежноеПоручениеИсходящее", "РасходныйКассовыйОрдер", "ПлатежныйОрдерСписаниеДенежныхСредств"):
        if not exists("bp", "doc_" + d):
            continue
        for r in rows("bp", "doc_" + d, ["Проведен", "ПометкаУдаления", "Дата", "Номер", "Контрагент", "СуммаДокумента",
                                        "ВидОперации", "ВалютаДокумента"]):
            if r["Проведен"] != "1" or r["ПометкаУдаления"] == "1":
                continue
            if any(x in (r["ВидОперации"] or "").lower() for x in INTERNAL):
                continue
            cu = (r.get("ВалютаДокумента") or "KZT").upper()
            cu = "RUB" if cu.startswith("RU") else "USD" if cu.startswith("US") else "EUR" if cu.startswith("EU") else "KZT"
            P.append((date.fromisoformat(r["Дата"][:10]), num(r["СуммаДокумента"]), cu, "БП", r["Номер"], r["Контрагент"]))
    nbp = len(P)
    c = sqlite3.connect(DB)
    for dt, s, no, cp in c.execute("SELECT date, SUM(sum), doc_no, counterparty FROM an_cashflow WHERE direction='out' "
                                   "AND doc_key NOT LIKE 'L:%' GROUP BY doc_key"):
        P.append((date.fromisoformat(dt), s, "KZT", "КА", no, cp))
    out(f"оплат: БП {nbp}, КА {len(P) - nbp}")

    idx = defaultdict(list)   # (валюта, сумма до тенге) → [индексы оплат], отсортированы по дате
    for k, p in enumerate(P):
        idx[(p[2], round(p[1]))].append(k)
    for v in idx.values():
        v.sort(key=lambda k: P[k][0])
    used = set()
    bykey = sorted(idx.keys())


    def find(z, tol):
        lo, hi = z["d"] - timedelta(days=3), z["d"] + timedelta(days=WIN)
        if tol == 0:
            cands = idx.get((z["cur"], round(z["sum"])), [])
        else:
            a, b = z["sum"] * (1 - tol), z["sum"] * (1 + tol)
            cands = []
            j = bisect_left(bykey, (z["cur"], round(a)))
            while j < len(bykey) and bykey[j][0] == z["cur"] and bykey[j][1] <= b:
                cands += idx[bykey[j]]
                j += 1
            cands.sort(key=lambda k: abs((P[k][0] - z["d"]).days))
        for k in cands:
            if k not in used and lo <= P[k][0] <= hi:
                return k
        return None


    for tol in (0, 0.01):
        for z in sorted(Z, key=lambda z: z["d"]):
            if "pay" in z or z["sum"] <= 0:
                continue
            k = find(z, tol)
            if k is not None:
                used.add(k)
                z["pay"] = k
                z["tol"] = tol

    return Z, P


def kzt_of(z):
    return z["sum"] if z["cur"] == "KZT" else z["sum"] * RATE[z["cur"]].get(z["d"].year, RATE[z["cur"]][2026])


if __name__ == "__main__":
    F = sys.argv[1]
    Z, P = match(F, int(sys.argv[2]) if len(sys.argv) > 2 else 45)
    agg = defaultdict(lambda: [0, 0.0, 0, 0.0])
    with open("zay_match.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["дата", "сумма", "валюта", "сумма_тг", "город", "назначение", "содержание", "вложения", "вид",
                    "база", "дата_оплаты", "номер", "контрагент"])
        for z in Z:
            kzt = kzt_of(z)
            if kzt > 1e9:   # опечатки в сумме (1,15 и 1,07 млрд) — не считаем
                continue
            p = P[z["pay"]] if "pay" in z else None
            a = agg[z["d"].year]
            if p:
                a[0] += 1; a[1] += kzt
            else:
                a[2] += 1; a[3] += kzt
            w.writerow([z["d"], z["sum"], z["cur"], round(kzt), z["city"], z["purpose"], z["text"], z["att"],
                        "белая" if p else "вторая", p[3] if p else "", p[0] if p else "", p[4] if p else "", p[5] if p else ""])
    out("год | белая (нашлась оплата в 1С): шт, млн | вторая: шт, млн")
    for y in sorted(agg):
        a = agg[y]
        out(f"{y} | {a[0]} {a[1] / 1e6:,.0f} | {a[2]} {a[3] / 1e6:,.0f}")
