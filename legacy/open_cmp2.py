"""Проект 21: ввод остатков по контрагентам — КА (сальдо 01.01.2025, an_audit osv_2025) против БП (31.12.2024, accsub_*).
Результат — в analytics.sqlite3 an_audit, раздел cmp_open (читать: /audit/data?section=cmp_open)."""
import json, re, sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from lg import rows, num, out, exists

DB = r"D:\anescom_edo\data\analytics.sqlite3"
ACCS = ("121", "331", "351", "171", "338")


def norm(s):
    s = (s or "").upper().replace("Ё", "Е")
    s = re.sub(r"\b(ТОО|ИП|АО|ТОВАРИЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ|ИНДИВИДУАЛЬНЫЙ ПРЕДПРИНИМАТЕЛЬ|LLP|TOO)\b", " ", s)
    s = re.sub(r"[^0-9A-ZА-ЯӘҒҚҢӨҰҮҺІ]+", "", s)
    return s


ka = defaultdict(lambda: defaultdict(float)); names = {}
con = sqlite3.connect(DB)
for (row,) in con.execute("SELECT row FROM an_audit WHERE section='osv_2025' AND source='anescom'"):
    r = json.loads(row)
    a = r["acc"]
    if not a.startswith(ACCS) or "ANESCOM" not in r.get("org", "").upper() and "АНЕСКОМ" not in r.get("org", "").upper():
        continue
    k = norm(r.get("sub1"))
    names.setdefault(k, r.get("sub1"))
    ka[k][a[:4]] += num(r.get("beg_dt")) - num(r.get("beg_kt"))

bp = defaultdict(lambda: defaultdict(float)); bpacc = set()
srcs = [n for n in ("accsub_Типовой", "accsub_debts_Типовой") if exists("bp", n)]
seen_debts = "accsub_debts_Типовой" in srcs
for src in srcs:
    for r in rows("bp", src, ["Период", "Счет", "Субконто1", "СуммаДт", "СуммаКт"]):
        a = r["Счет"]
        if not a.startswith(ACCS) or r["Период"][:10] > "2024-12-31":
            continue
        if seen_debts and src == "accsub_Типовой" and a[:3] in ("121", "351"):
            continue  # берём из отдельной выгрузки расчётов
        bpacc.add(a[:4])
        k = norm(r["Субконто1"])
        names.setdefault(k, r["Субконто1"])
        bp[k][a[:4]] += num(r["СуммаДт"]) - num(r["СуммаКт"])
out("БП счета в выгрузке:", sorted(bpacc), "источники:", srcs)

res = []
for k in set(ka) | set(bp):
    b, c = bp.get(k, {}), ka.get(k, {})
    bnet = sum(b.values()); cnet = sum(c.values())
    res.append({"name": names.get(k, k), "bp": {a: round(v, 2) for a, v in b.items() if abs(v) > 0.5},
                "ka": {a: round(v, 2) for a, v in c.items() if abs(v) > 0.5},
                "bp_net": round(bnet, 2), "ka_net": round(cnet, 2), "diff": round(cnet - bnet, 2)})
res.sort(key=lambda x: -abs(x["diff"]))
ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
con.execute("DELETE FROM an_audit WHERE section='cmp_open'")
con.executemany("INSERT INTO an_audit(section, source, ts, date_from, date_to, row) VALUES('cmp_open','anescom',?,?,?,?)",
                [(ts, "2024-12-31", "2025-01-01", json.dumps(r, ensure_ascii=False)) for r in res])
con.commit()
tot = defaultdict(float)
for r in res:
    for a, v in r["bp"].items(): tot["bp" + a] += v
    for a, v in r["ka"].items(): tot["ka" + a] += v
out("контрагентов:", len(res), "итоги:", {k: round(v / 1e6, 2) for k, v in sorted(tot.items())})
for r in res[:25]:
    out(f"{r['name'][:40]} | БП {r['bp_net']:,.0f} | КА {r['ka_net']:,.0f} | разн {r['diff']:,.0f}")
