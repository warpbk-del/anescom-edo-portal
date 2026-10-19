"""6о. Фин. план: факт расходов из заявок Bitrix24 → таблица an_fin_fact в analytics.sqlite3.

Запуск на сервере (папка D:\\anescom_edo\\legacy\\py):
    python finplan_build.py [файлы заявок .xls …] [окно_дней=45]
По умолчанию D:\\anescom_edo\\legacy\\zayavki_20261007.xls (ANESCOM) и zayavki_avtokomp_20261019.xls (АВТОКОМП —
отдельный процесс Bitrix24, прислан 19.10.2026 08:42; организация берётся по слову «avtokomp» в имени файла;
оплаты для сверки — только из базы КА АВТОКОМП, an_cashflow_avtokomp).

Каждая заявка → статья и отдел (справочник finplan_articles.py; сначала по краткому содержанию), город, сумма в тенге, вид денег:
  белая / вторая по правилу пользователя 19.10.2026 (6н):
    1) в «Документ подтверждающий оплату» платёжное поручение («№NNN_<контрагент>_<сумма>__<дата>.pdf») → белая,
       чек Kaspi («transfer-receipt…») → вторая;
    2) иначе — нашлась оплата в БП/КА (zay_match.py: та же сумма, окно −3…+45 дней) → белая;
    3) иначе — вторая.
ФОТ, налоги с ФОТ, КПН и НДС портал берёт из 1С (an_cashflow) сам — при показе страницы, там, где они есть.
Справочник отделов и статей → an_fin_depts, an_fin_articles (портал берёт его оттуда).
План (an_fin_plan) пишет портал: правки годовых сумм статей на вкладке «Фин. план»; этот скрипт его не трогает.
"""
import os, re, sqlite3, sys
from collections import defaultdict
from datetime import datetime

from finplan_articles import ART, ARTICLES, DEPTS, article_text_first
from lg import out
from zay_match import DB, kzt_of, match

# файлы заявок: ANESCOM (основной процесс Bitrix24) и АВТОКОМП (свой процесс; в имени файла «avtokomp»)
FILES = [a for a in sys.argv[1:] if not a.isdigit()] or [r"D:\anescom_edo\legacy\zayavki_20261007.xls",
                                                         r"D:\anescom_edo\legacy\zayavki_avtokomp_20261019.xls"]
WIN = int(next((a for a in sys.argv[1:] if a.isdigit()), 45))
CITIES = ("Актобе", "Астана", "Атырау", "Актау", "Уральск", "Костанай")
COL_CONF = "Документ подтверждающий оплату"
RX_PP = re.compile(r"№\s*\d+_(.+?)_[\d\s]+(?:[.,]\d+)?__")


def city_of(s):
    s = (s or "").strip()
    for c in CITIES:
        if c.lower() in s.lower():
            return c
    return s or "Прочие"


def conf_of(s):
    """→ (вид подтверждения, контрагент из имени платёжки)."""
    s = s or ""
    if "transfer-receipt" in s.lower():
        return "чек", ""
    m = RX_PP.search(s)
    if m:
        return "платёжка", m.group(1).strip()
    if re.search(r"№\s*\d+", s):
        return "платёжка", ""
    return ("скан" if s.strip() else "нет"), ""


rows, skipped = [], 0
ZP = []
for F in FILES:
    if not os.path.exists(F):
        out(f"нет файла {F} — пропущен")
        continue
    org = "АВТОКОМП" if "avtokomp" in os.path.basename(F).lower() else "ANESCOM"
    Z, P = match(F, WIN, org)
    ZP += [(z, P, org) for z in Z]
for z, P, org in ZP:
    r = z["r"]
    s = kzt_of(z)
    if s <= 0 or s > 1e9 or z["d"].year < 2020:      # опечатки в сумме (1,15 и 1,07 млрд)
        skipped += 1
        continue
    statya = next((v for k, v in r.items() if k.startswith("Статья расхода")), "")
    code = article_text_first(statya, r.get("Назначение платежа", ""), z["text"] + " " + str(r.get("Краткое содержание (Наименование товара и услуг)", "")))
    conf, cp = conf_of(r.get(COL_CONF, ""))
    pay = P[z["pay"]] if "pay" in z else None
    if conf == "платёжка":
        color, basis = "white", "платёжка"
    elif conf == "чек":
        color, basis = "second", "чек"
    elif pay:
        color, basis = "white", "оплата в " + pay[3]
    else:
        color, basis = "second", "оплата в 1С не найдена"
    cp = cp or (pay[5] if pay else "")
    rows.append((org, str(z["d"]), z["d"].year, z["d"].month, city_of(z["city"]), ART[code][2], code, color, basis,
                 round(s, 2), cp[:120], str(r.get("Краткое содержание (Наименование товара и услуг)", ""))[:200],
                 z["cur"], r.get("Метод оплаты", "")))

c = sqlite3.connect(DB, timeout=60)
c.executescript("""
DROP TABLE IF EXISTS an_fin_fact;
CREATE TABLE an_fin_fact (id INTEGER PRIMARY KEY AUTOINCREMENT, org TEXT, date TEXT, year INTEGER, month INTEGER, city TEXT,
    dept TEXT, article TEXT, color TEXT, basis TEXT, sum REAL, counterparty TEXT, text TEXT, currency TEXT, method TEXT);
CREATE INDEX idx_an_fin_fact_y ON an_fin_fact(year, month);
CREATE TABLE IF NOT EXISTS an_fin_plan (id INTEGER PRIMARY KEY AUTOINCREMENT, year INTEGER, article TEXT, sum REAL,
    who TEXT, ts TEXT, org TEXT);
CREATE TABLE IF NOT EXISTS an_fin_meta (k TEXT PRIMARY KEY, v TEXT);
DROP TABLE IF EXISTS an_fin_depts;
CREATE TABLE an_fin_depts (code TEXT PRIMARY KEY, name TEXT, note TEXT, pos INTEGER);
DROP TABLE IF EXISTS an_fin_articles;
CREATE TABLE an_fin_articles (code TEXT PRIMARY KEY, name TEXT, dept TEXT, section TEXT, pos INTEGER);
""")
if "org" not in [r[1] for r in c.execute("PRAGMA table_info(an_fin_plan)")]:
    c.execute("ALTER TABLE an_fin_plan ADD COLUMN org TEXT")      # правки до 19.10 08:50 — ANESCOM
c.execute("UPDATE an_fin_plan SET org='ANESCOM' WHERE org IS NULL OR org=''")
c.executemany("INSERT INTO an_fin_depts VALUES (?,?,?,?)", [d + (i,) for i, d in enumerate(DEPTS)])
c.executemany("INSERT INTO an_fin_articles VALUES (?,?,?,?,?)", [a + (i,) for i, a in enumerate(ARTICLES)])
c.executemany("INSERT INTO an_fin_fact (org, date, year, month, city, dept, article, color, basis, sum, counterparty, text, "
              "currency, method) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
last = max(r[1] for r in rows if r[0] == "ANESCOM") if any(r[0] == "ANESCOM" for r in rows) else max(r[1] for r in rows)
for k, v in (("source", ", ".join(os.path.basename(f) for f in FILES)),
             ("fact_to_ak", max((r[1] for r in rows if r[0] == "АВТОКОМП"), default="")), ("fact_to", last), ("built", datetime.now().isoformat(timespec="seconds")),
             ("rows", str(len(rows)))):
    c.execute("INSERT OR REPLACE INTO an_fin_meta (k, v) VALUES (?, ?)", (k, v))
c.commit()

out(f"заявок {len(Z)}, в факт {len(rows)}, пропущено {skipped}; факт по {last}")
agg = defaultdict(lambda: defaultdict(float))
for r in rows:
    agg[r[2]][r[7]] += r[9]
    agg[r[2]][r[5]] += r[9]
    agg[r[2]]["АК"] += r[9] if r[0] == "АВТОКОМП" else 0
out("год | белая | вторая | по отделам, млн ₸ | в т.ч. АВТОКОМП")
for y in sorted(agg):
    a = agg[y]
    deps = " ".join(f"{d}={a[d] / 1e6:,.1f}" for d in ("SAL", "MKT", "LOG", "PUR", "PRD", "HR", "ADM", "IT", "FIN", "CAP") if a[d])
    out(f"{y} | {a['white'] / 1e6:,.0f} | {a['second'] / 1e6:,.0f} | {deps} | АВТОКОМП {a['АК'] / 1e6:,.1f}")
