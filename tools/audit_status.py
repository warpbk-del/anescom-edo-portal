# -*- coding: utf-8 -*-
"""Сводка аудита 1С (проект 21) прямо из D:\\anescom_edo\\data\\analytics.sqlite3 — для чтения на экране сервера.
Запуск: D:\\anescom_edo\\.venv\\Scripts\\python.exe audit_status.py [part]
part: s (сводка, по умолчанию) | h (банки 1021/1030/1050) | a (АВТОКОМП) | m (1151/3340/0000)
"""
import json, sqlite3, sys
from collections import defaultdict

DB = r"D:\anescom_edo\data\analytics.sqlite3"
part = sys.argv[1] if len(sys.argv) > 1 else "s"
c = sqlite3.connect(DB)
c.row_factory = sqlite3.Row


def rows(sec):
    return [json.loads(r["row"]) for r in c.execute(
        "SELECT row FROM an_audit WHERE section=? AND source='anescom' ORDER BY id", (sec,))]


def mln(x):
    x = x or 0
    return f"{x / 1e6:,.2f}".replace(",", " ")


if part == "s":
    for r in c.execute("SELECT section, COUNT(*) n, MAX(ts) ts FROM an_audit WHERE source='anescom' GROUP BY section ORDER BY ts DESC"):
        print(f"{r['section']:<16}{r['n']:>8}  {r['ts']}")
    last = c.execute("SELECT ts, body FROM an_meta WHERE body LIKE '%audit_run%' ORDER BY id DESC LIMIT 1").fetchone()
    if last:
        b = json.loads(last["body"])
        print("LAST RUN", last["ts"], json.dumps(b.get("counts"), ensure_ascii=False))
        for e in b.get("errors") or []:
            print("ERR", str(e)[:200])

elif part == "h":
    # пары счетов по деньгам: где участвует 1021 — по субконто и типам документов, итог 2025–2026
    agg = defaultdict(lambda: [0, 0.0])
    for r in rows("money_pairs"):
        if "1021" in (r["dt"], r["kt"]):
            k = (r["dt"], r["kt"], r["sub_dt"][:22], r["sub_kt"][:22], r["doc_type"][:28])
            agg[k][0] += r["n"]; agg[k][1] += r["sum"]
    for k, v in sorted(agg.items(), key=lambda x: -abs(x[1][1]))[:40]:
        print(f"{k[0]}>{k[1]} | {k[2]:<22} | {k[3]:<22} | {k[4]:<28} | n={v[0]:<5} {mln(v[1]):>12}")

elif part == "hm":
    # по месяцам: 4 потока через 1021 (млн)
    agg = defaultdict(lambda: defaultdict(float))
    for r in rows("money_pairs"):
        if "1021" in (r["dt"], r["kt"]) and r["dt"] in ("1021", "1030", "1050") and r["kt"] in ("1021", "1030", "1050"):
            agg[r["month"][:7]][f'{r["dt"]}>{r["kt"]}'] += r["sum"]
    keys = ["1021>1030", "1050>1021", "1021>1050", "1030>1021"]
    print("month     " + "".join(f"{k:>12}" for k in keys) + "   out2209-in1094   out1094-in2209")
    for m in sorted(agg):
        a = agg[m]
        print(f"{m}   " + "".join(f"{mln(a[k]):>12}" for k in keys)
              + f"{mln(a['1021>1030'] - a['1050>1021']):>16}{mln(a['1021>1050'] - a['1030>1021']):>16}")

elif part == "acc":
    # au acc 1151 : по месяцам и корр. счетам (moves_sel, кроме 2024-12)
    acc = sys.argv[2]
    agg = defaultdict(float)
    for r in rows("moves_sel"):
        if acc in (r["dt"], r["kt"]) and r["date"][:7] != "2024-12":
            side = "Dt" if r["dt"] == acc else "Kt"
            agg[(r["date"][:7], side, r["kt"] if side == "Dt" else r["dt"])] += r["sum"]
    for k in sorted(agg):
        print(f"{k[0]} {acc} {k[1]} corr {k[2]:<6} {mln(agg[k]):>12}")

elif part == "docs":
    # au docs 3340 [2026-0] : документы по счёту (moves_sel), крупные первыми
    acc = sys.argv[2]; pref = sys.argv[3] if len(sys.argv) > 3 else ""
    rs = [r for r in rows("moves_sel") if acc in (r["dt"], r["kt"]) and r["date"].startswith(pref) and r["date"][:7] != "2024-12"]
    for r in sorted(rs, key=lambda r: -abs(r["sum"]))[:45]:
        print(f'{r["date"]} {r["dt"]}>{r["kt"]} {mln(r["sum"]):>9} | {r["doc"][:48]:<48} | {r["sub_dt"][:18]:<18} | {r["sub_kt"][:18]:<18} | {r["text"][:40]}')

elif part == "osv":
    # au osv АВТОКОМП : строки ОСВ на 30.09 с текстом
    t = sys.argv[2].upper()
    for sec in ("osv_0930",):
        for r in rows(sec):
            s2 = json.dumps(r, ensure_ascii=False)
            if t in s2.upper():
                print(s2[:250])

elif part == "a":
    for r in rows("moves_sel") + rows("money_pairs"):
        s = json.dumps(r, ensure_ascii=False)
        if "АВТОКОМП" in s.upper():
            print(s[:230])

elif part == "m":
    agg = defaultdict(lambda: [0, 0.0])
    for r in rows("moves_sel"):
        for acc in ("1151", "3340", "0000"):
            if acc in (r["dt"], r["kt"]):
                k = (acc, r["dt"], r["kt"], r["date"][:7], r["sub_dt"][:20], r["sub_kt"][:20])
                agg[k][0] += 1; agg[k][1] += r["sum"]
    for k, v in sorted(agg.items())[:60]:
        print(f"{k[0]} {k[1]}>{k[2]} {k[3]} | {k[4]:<20} | {k[5]:<20} | n={v[0]:<4} {mln(v[1]):>10}")
