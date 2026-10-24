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
