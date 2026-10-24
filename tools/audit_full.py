# -*- coding: utf-8 -*-
"""Полный аудит 1С (проект 21) по данным выгрузки из копии в analytics.sqlite3 — отчёт для чтения на экране сервера.
Запуск: D:\\anescom_edo\\.venv\\Scripts\\python.exe audit_full.py [раздел]  (без раздела — все)
Пишет также audit_full.txt рядом со скриптом. Суммы — млн ₸.
"""
import json, os, sqlite3, sys
from collections import defaultdict

DB = os.environ.get("AUDIT_DB", r"D:\anescom_edo\data\analytics.sqlite3")
ONLY = sys.argv[1] if len(sys.argv) > 1 else ""
c = sqlite3.connect(DB)
c.row_factory = sqlite3.Row
OUT = []


def p(*a):
    OUT.append(" ".join(str(x) for x in a))


def rows(sec):
    return [json.loads(r["row"]) for r in c.execute(
        "SELECT row FROM an_audit WHERE section=? AND source='anescom' ORDER BY id", (sec,))]


def m(x):
    return f"{(x or 0) / 1e6:,.1f}".replace(",", " ")


def org(s):
    s = (s or "").upper()
    return "GRN" if "GREENTE" in s or "ГРИНТЕ" in s else ("ANS" if s else "-")


def bal(r):
    return (r.get("end_dt") or 0) - (r.get("end_kt") or 0)


def sec(name, title):
    if ONLY and ONLY != name:
        return False
    p(""); p(f"=== {name}: {title}")
    return True


OSV = rows("osv_0930")           # с субконто, 01.01–30.09.2026
ACC = rows("osv_acc_0930")       # по счетам

# 1. Счета с «неправильным» знаком сальдо (актив с Кт, пассив с Дт) — по счетам
if sec("sign", "сальдо 30.09 не своего знака (по счетам)"):
    agg = defaultdict(float)
    for r in ACC:
        agg[(org(r.get("org")), r["acc"], r.get("acc_name", "")[:30])] += bal(r)
    for (o, a, n), b in sorted(agg.items()):
        bad = (a[0] in "12" and b < -1e5) or (a[0] in "34" and b > 1e5) or (a == "0000" and abs(b) > 1e5)
        if bad:
            p(f"{o} {a:<5} {n:<30} {m(b):>10}")

# 2. Деньги: кредитовые остатки по кассам/счетам (субконто)
if sec("cash", "деньги 10xx — кредитовые остатки по субконто на 30.09"):
    for r in sorted(OSV, key=bal):
        if r["acc"].startswith("10") and bal(r) < -1e4:
            p(f"{org(r.get('org'))} {r['acc']} {r.get('sub1','')[:40]:<40} {m(bal(r)):>9}")

# 3. Незачтённые авансы: один контрагент и в 1210 (нам должны) и в 3510 (мы должны аванс) / 1710 и 3310
if sec("adv", "незачтённые авансы (контрагент одновременно Дт и Кт), топ-25"):
    by = defaultdict(lambda: defaultdict(float))
    for r in OSV:
        a = r["acc"]
        if a[:3] in ("121", "351", "171", "331"):
            by[(org(r.get("org")), r.get("sub1", ""))][a[:3]] += bal(r)
    res = []
    for (o, k), d in by.items():
        x1 = min(d["121"], -d["351"]) if d["121"] > 0 and d["351"] < 0 else 0
        x2 = min(d["171"], -d["331"]) if d["171"] > 0 and d["331"] < 0 else 0
        if x1 > 1e5 or x2 > 1e5:
            res.append((max(x1, x2), o, k, d))
    p(f"всего контрагентов: {len(res)}; сумма к зачёту ≈ {m(sum(x[0] for x in res))}")
    for x, o, k, d in sorted(res, reverse=True)[:25]:
        p(f"{o} {k[:34]:<34} 1210 {m(d['121']):>8} 3510 {m(d['351']):>8} | 1710 {m(d['171']):>8} 3310 {m(d['331']):>8}")

# 4. Подотчёт и зарплата: отрицательные / крупные
if sec("emp", "подотчёт 1251/3350 и зарплата 3350: аномалии"):
    for r in sorted(OSV, key=bal):
        a = r["acc"]
        if a.startswith("125") and bal(r) < -1e5:
            p(f"{org(r.get('org'))} {a} {r.get('sub1','')[:40]:<40} {m(bal(r)):>9}  (перерасход не оформлен)")
        if a.startswith("335") and bal(r) > 1e5:
            p(f"{org(r.get('org'))} {a} {r.get('sub1','')[:40]:<40} {m(bal(r)):>9}  (переплата зарплаты)")

# 5. Запасы с кредитовым сальдо
if sec("stock", "запасы 13xx с кредитовым сальдо (топ-25)"):
    neg = [r for r in OSV if r["acc"].startswith("13") and bal(r) < -1e4]
    p(f"строк: {len(neg)}, сумма {m(sum(bal(r) for r in neg))}")
    for r in sorted(neg, key=bal)[:25]:
        p(f"{org(r.get('org'))} {r['acc']} {r.get('sub1','')[:38]:<38} {r.get('sub2','')[:18]:<18} {m(bal(r)):>8}")

# 6. Налоги 31xx: переплаты (Дт сальдо) и крупные долги
if sec("tax", "налоги 31xx на 30.09"):
    agg = defaultdict(float)
    for r in ACC:
        if r["acc"].startswith("31"):
            agg[(org(r.get("org")), r["acc"], r.get("acc_name", "")[:34])] += bal(r)
    for k, b in sorted(agg.items()):
        if abs(b) > 1e5:
            p(f"{k[0]} {k[1]:<5} {k[2]:<34} {m(b):>9} {'ПЕРЕПЛАТА' if b > 0 else ''}")

# 7. Документы: непроведённые / помеченные / будущие
if sec("docs", "непроведённые, помеченные на удаление, с будущей датой"):
    for r in sorted(rows("unposted"), key=lambda r: -(r.get("unposted", 0) + r.get("future", 0))):
        if r.get("unposted") or r.get("future") or (r.get("deleted") or 0) > 20:
            p(f"{org(r.get('org'))} {r.get('doc_type','')[:40]:<40} непр {r.get('unposted',0):>5} помеч {r.get('deleted',0):>5} будущ {r.get('future',0):>3} {r.get('max_future','')[:10]} пример {r.get('sample_no','')[:14]}")

# 8. Переработка: получено давальческого vs отчитано
if sec("proc", "переработка: получено и не отчитано"):
    for r in rows("processor"):
        d = (r.get("received") or 0) - (r.get("reported") or 0)
        p(f"{r.get('date','')[:10]} {r.get('order','')[:40]:<40} {r.get('item','')[:30]:<30} получ {r.get('received')} отч {r.get('reported')} разн {round(d,3)}")

# 9. Отрицательные остатки товаров
if sec("neg", "отрицательные остатки товаров (регистры)"):
    for r in sorted(rows("negstock"), key=lambda r: r.get("qty", 0))[:20]:
        p(f"{r.get('register','')[:20]} {r.get('where','')[:30]:<30} {r.get('item','')[:40]:<40} {r.get('qty')}")

# 10. Банки Halyk через 1021 по месяцам
if sec("bank", "1021: перемещения текущий 2209 <-> депозит 1094 по месяцам"):
    agg = defaultdict(lambda: defaultdict(float))
    for r in rows("money_pairs"):
        if "1021" in (r["dt"], r["kt"]):
            agg[r["month"][:7]][f'{r["dt"]}>{r["kt"]}'] += r["sum"]
    p("месяц    2209->деп  деп(прих)  деп->2209  2209(прих)  прочее1021")
    for mo in sorted(agg):
        a = agg[mo]
        other = sum(v for k, v in a.items() if k not in ("1021>1030", "1050>1021", "1021>1050", "1030>1021"))
        p(f"{mo} {m(a['1021>1030']):>10} {m(a['1050>1021']):>10} {m(a['1021>1050']):>10} {m(a['1030>1021']):>11} {m(other):>11}")

# 11. Транзит денег 1021/1022/1023 и прочие 10xx — итог по субконто на 30.09
if sec("transit", "транзитные счета денег 102x на 30.09 по субконто"):
    for r in sorted(OSV, key=bal):
        if r["acc"].startswith("102") and abs(bal(r)) > 1e5:
            p(f"{org(r.get('org'))} {r['acc']} {r.get('sub1','')[:45]:<45} {m(bal(r)):>10}")

# 12. Выбранные счета по месяцам (moves_sel): 1151, 3340, 1340, 3381, 1060, 3360, 5610
if sec("sel", "выбранные счета по месяцам (Дт/Кт), 2025–2026"):
    agg = defaultdict(lambda: [0.0, 0.0])
    for r in rows("moves_sel"):
        if r["date"][:7] == "2024-12":
            continue
        for a in ("1151", "3340", "1340", "3381", "1060", "3360", "5610", "1050"):
            if r["dt"] == a:
                agg[(a, r["date"][:7])][0] += r["sum"]
            if r["kt"] == a:
                agg[(a, r["date"][:7])][1] += r["sum"]
    cur = None
    for (a, mo), (d, k) in sorted(agg.items()):
        if a != cur:
            p(f"-- {a}"); cur = a
        p(f"   {mo} Дт {m(d):>9} Кт {m(k):>9}")

# 13. 3340 / 1151 — документы
if sec("seldocs", "3340 и 1151: крупные проводки 2026"):
    for a in ("3340", "1151"):
        rs = [r for r in rows("moves_sel") if a in (r["dt"], r["kt"]) and r["date"] >= "2026"]
        p(f"-- {a}: {len(rs)} проводок")
        for r in sorted(rs, key=lambda r: -abs(r["sum"]))[:15]:
            p(f'{r["date"]} {r["dt"]}>{r["kt"]} {m(r["sum"]):>8} {r["doc"][:46]:<46} {r["sub_dt"][:16]:<16} {r["sub_kt"][:16]:<16} {r["text"][:30]}')

# 14. Типы документов по деньгам — нетипичные пары счетов
if sec("pairs", "нетипичные корреспонденции по деньгам (2026)"):
    agg = defaultdict(float)
    for r in rows("money_pairs"):
        if r["month"] >= "2026":
            agg[(r["dt"], r["kt"], r["doc_type"][:34])] += r["sum"]
    common = {"1210", "3510", "3310", "1710", "3350", "1251", "3110", "3120", "3130", "3150", "3211", "3212", "3213",
              "3221", "1030", "1010", "1021", "1050", "7210", "7470", "1420", "3020", "3310"}
    for (d, k, t), s in sorted(agg.items(), key=lambda x: -abs(x[1])):
        other = k if d.startswith("10") else d
        if other not in common and abs(s) > 5e6:
            p(f"{d}>{k} {t:<34} {m(s):>9}")

text = "\n".join(OUT)
print(text)
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit_full.txt"), "w", encoding="utf-8") as f:
    f.write(text)
