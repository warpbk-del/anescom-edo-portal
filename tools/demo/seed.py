"""Демо-данные для скриншотов презентации (вымышленные клиенты, суммы, люди)."""
import json, random, sqlite3, sys, os
from datetime import date, timedelta, datetime
random.seed(7)
DATA = sys.argv[1]
os.makedirs(DATA, exist_ok=True)
sys.path.insert(0, ".")
from app import analytics
A = sqlite3.connect(os.path.join(DATA, "analytics.sqlite3"))
A.executescript(analytics._schema())
BR = ["Актобе", "Уральск", "Атырау", "Актау"]
WH = {b: f"Склад {b}" for b in BR}
MGR = {"Актобе": ["Ахметов Ерлан", "Сергеева Анна"], "Уральск": ["Каримов Данияр", "Ли Ольга"],
       "Атырау": ["Жумабаев Нурлан"], "Актау": ["Оспанова Айгерим"]}
CLIENTS = ["ТОО «СтройМастер»", "ИП Бекова А.", "ТОО «Окна Каспия»", "ТОО «ПрофиСтрой Запад»", "ИП Тлеуов Е.",
           "ТОО «Алюкон»", "ТОО «Фасад-Сервис»", "ИП Мусин Р.", "ТОО «Евроокна Актобе»", "ТОО «Темир Курылыс»",
           "ТОО «Жайык Строй»", "ИП Сапарова Г.", "ТОО «Атырау Монтаж»", "ТОО «Мангистау Профиль»", "Покупатель розница"]
ITEMS = [("Профиль алюминиевый ALT 50", "Алюминиевый профиль", 5200), ("Профиль алюминиевый ALT F50", "Алюминиевый профиль", 6100),
         ("Профиль ПВХ 70 мм белый", "ПВХ профиль", 2400), ("Профиль ПВХ 58 мм", "ПВХ профиль", 1900),
         ("Стеклопакет 4-16-4", "Стеклопакеты", 9800), ("Стеклопакет энергосберегающий", "Стеклопакеты", 14500),
         ("Фурнитура поворотно-откидная", "Фурнитура", 7800), ("Ручка оконная", "Фурнитура", 1200),
         ("Уплотнитель EPDM", "Комплектующие", 350), ("Подоконник ПВХ 300 мм", "Подоконники", 3100),
         ("Сэндвич-панель 24 мм", "Панели", 6400), ("Ламинация профиля (золотой дуб)", "Ламинация", 1500)]
def days(a, b):
    d = a
    while d <= b:
        yield d; d += timedelta(days=1)
sales, pays = [], []
n = 0
for d in days(date(2024, 1, 3), date(2026, 10, 19)):
    if d.weekday() == 6: continue
    season = 1.0 + 0.45 * (d.month in (4, 5, 6, 7, 8, 9)) + 0.15 * (d.year - 2024)
    for b in BR:
        k = {"Актобе": 4, "Уральск": 3, "Атырау": 2, "Актау": 2}[b]
        for _ in range(random.randint(0, int(k * season))):
            n += 1
            m = random.choice(MGR[b]); cl = random.choice(CLIENTS); key = f"DOC{n}"
            for it, g, pr in random.sample(ITEMS, random.randint(1, 4)):
                q = random.randint(2, 60); s = round(q * pr * random.uniform(0.9, 1.15), 0)
                sales.append((d.isoformat(), key, f"00НФ-{n:06d}", "ТОО ANESCOM", b, WH[b], m, cl, cl, it, it, g, q, s, round(s * random.uniform(0.68, 0.8))))
            tot = sum(r[13] for r in sales[-4:] if r[1] == key)
            if random.random() < 0.85:
                pays.append(((d + timedelta(days=random.randint(0, 12))).isoformat(), "P" + key, f"ПКО-{n}", "ТОО ANESCOM", b, m, cl, cl,
                             random.choice(["cash", "card", "bank", "bank"]), tot))
A.executemany("INSERT INTO an_sales (date,doc_key,doc_no,org,branch,warehouse,manager,client,client_key,item,item_key,item_group,qty,sum,cost) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", sales)
A.executemany("INSERT INTO an_payments (date,doc_key,doc_no,org,branch,manager,client,client_key,kind,sum) VALUES (?,?,?,?,?,?,?,?,?,?)", pays)
# расходы
ART = [("Заработная плата", 0.16), ("Налоги и отчисления с ФОТ", 0.05), ("Оплата поставщикам товаров", 0.55),
       ("Аренда склада", 0.03), ("Транспортные расходы", 0.04), ("Реклама и маркетинг", 0.015), ("Связь и интернет", 0.004),
       ("Коммунальные услуги", 0.01), ("Банковские комиссии", 0.003)]
cf = []
for y in (2024, 2025, 2026):
    for mth in range(1, 13):
        if date(y, mth, 1) > date(2026, 10, 19): break
        rev = sum(r[13] for r in sales if r[0].startswith(f"{y}-{mth:02d}"))
        for b in BR:
            share = {"Актобе": .38, "Уральск": .28, "Атырау": .18, "Актау": .16}[b]
            cf.append((f"{y}-{mth:02d}-05", f"CFI{y}{mth}{b}", "ПКО", "ТОО ANESCOM", b, "Оплата от покупателей", "Покупатели", "in", round(rev * share * .93)))
            for a, k in ART:
                cf.append((f"{y}-{mth:02d}-{random.randint(6, 27):02d}", f"CF{y}{mth}{b}{a}", "РКО", "ТОО ANESCOM", b, a,
                           "Поставщик" if "поставщ" in a else "", "out", round(rev * share * k * random.uniform(.85, 1.15))))
A.executemany("INSERT INTO an_cashflow (date,doc_key,doc_no,org,branch,article,counterparty,direction,sum) VALUES (?,?,?,?,?,?,?,?,?)", cf)
st = []
for b in BR:
    for it, g, pr in ITEMS:
        q = random.randint(0, 900); s30 = random.randint(0, 200)
        st.append(("ТОО ANESCOM", b, WH[b], it, it, g, "шт", q, round(q * pr * .72), "2026-10-1" + str(random.randint(0, 8)), s30, s30 * 3 + random.randint(0, 50)))
A.executemany("INSERT INTO an_stock (org,branch,warehouse,item,item_key,item_group,unit,qty,cost_sum,last_sale,sold_30,sold_90) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", st)
db_ = []
for cl in CLIENTS[:-1]:
    b = random.choice(BR); m = random.choice(MGR[b])
    debt = random.choice([0, 0, random.randint(150, 4800) * 1000]); pre = 0 if debt else random.choice([0, random.randint(50, 900) * 1000])
    od = round(debt * random.choice([0, .3, .6])) if debt else 0
    db_.append(("ТОО ANESCOM", b, m, cl, cl, debt, pre, od, random.randint(5, 75) if od else 0))
A.executemany("INSERT INTO an_debts (org,branch,manager,client,client_key,debt,prepay,overdue,overdue_days) VALUES (?,?,?,?,?,?,?,?,?)", db_)
for y in (2024, 2025):
    A.executemany("INSERT INTO an_debts_hist (date,year,org,branch,manager,client,client_key,debt,prepay,overdue,overdue_days) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                  [(f"{y}-12-31", str(y)) + r for r in db_])
# производство АВТОКОМП
po = []; pin = []; pout = []
COL = ["Золотой дуб", "Орех", "Антрацит", "Махагон", "Белый"]
for i in range(1, 40):
    d = date(2026, 1, 5) + timedelta(days=i * 7)
    if d > date(2026, 10, 19): break
    it, g = random.choice([("Профиль ПВХ 70 мм", "ПВХ профиль"), ("Профиль ПВХ 58 мм", "ПВХ профиль")])
    q = random.randint(800, 4000); c = random.choice(COL)
    po.append((f"O{i}", f"ЗП-{i:04d}", d.isoformat(), "ТОО «ЛамиТек»", "ТОО АВТОКОМП", "В работе" if i > 30 else "Закрыт", it, it, g, c, q, q if i <= 30 else round(q * .4), (d + timedelta(days=14)).isoformat()))
    pin.append(((d + timedelta(days=10)).isoformat(), f"IN{i}", f"ПТ-{i:04d}", "ТОО АВТОКОМП", "ТОО «ЛамиТек»", f"ЗП-{i:04d}", "Склад производства", it, it, g, c, q if i <= 30 else round(q * .4)))
for d in days(date(2025, 1, 6), date(2026, 10, 18)):
    if d.weekday() >= 5: continue
    for dept, it, g, u, w, a in [("Алюминий", "Окно алюминиевое", "Алюминиевые конструкции", "шт", 18, 1.6), ("ПВХ", "Окно ПВХ", "ПВХ конструкции", "шт", 22, 1.8), ("Покраска", "Покраска профиля", "Покраска", "м", 1.2, .15)]:
        q = random.randint(4, 30) if dept != "Покраска" else random.randint(80, 400)
        pout.append((d.isoformat(), f"PO{d}{dept}", f"ПР-{d.strftime('%m%d')}", "ТОО АВТОКОМП", dept, "Цех", it, it, g, random.choice(COL), q, u, round(q * w), "кг", round(q * a, 1), "м²"))
for t, rows, cols in [("an_prod_orders_avtokomp", po, "order_key,order_no,order_date,partner,org,status,item,item_key,item_group,color,qty,qty_in,due_date"),
                      ("an_prod_in_avtokomp", pin, "date,doc_key,doc_no,org,partner,order_no,warehouse,item,item_key,item_group,color,qty"),
                      ("an_prod_out_avtokomp", pout, "date,doc_key,doc_no,org,dept,warehouse,item,item_key,item_group,color,qty,unit,weight,weight_unit,area,area_unit")]:
    A.executemany(f"INSERT INTO {t} ({cols}) VALUES ({','.join('?' * len(cols.split(',')))})", rows)
A.execute("INSERT INTO an_loads (ts,kind,date_from,date_to,rows,replaced,ip,note) VALUES (?,?,?,?,?,?,?,?)", (datetime.now().isoformat(), "sales", "2024-01-01", "2026-10-19", len(sales), 0, "1C", "демо"))
# фин. план
sys.path.insert(0, "legacy")
from finplan_articles import DEPTS, ARTICLES
A.executescript("""
CREATE TABLE IF NOT EXISTS an_fin_fact (id INTEGER PRIMARY KEY AUTOINCREMENT, org TEXT, date TEXT, year INTEGER, month INTEGER, city TEXT,
    dept TEXT, article TEXT, color TEXT, basis TEXT, sum REAL, counterparty TEXT, text TEXT, currency TEXT, method TEXT);
CREATE TABLE IF NOT EXISTS an_fin_plan (id INTEGER PRIMARY KEY AUTOINCREMENT, year INTEGER, article TEXT, sum REAL, who TEXT, ts TEXT, org TEXT);
CREATE TABLE IF NOT EXISTS an_fin_meta (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS an_fin_depts (code TEXT PRIMARY KEY, name TEXT, note TEXT, pos INTEGER);
CREATE TABLE IF NOT EXISTS an_fin_articles (code TEXT PRIMARY KEY, name TEXT, dept TEXT, section TEXT, pos INTEGER);
""")
A.executemany("INSERT OR REPLACE INTO an_fin_depts VALUES (?,?,?,?)", [d + (i,) for i, d in enumerate(DEPTS)])
A.executemany("INSERT OR REPLACE INTO an_fin_articles VALUES (?,?,?,?,?)", [a + (i,) for i, a in enumerate(ARTICLES)])
ff = []
for y in (2025, 2026):
    for mth in range(1, 13):
        if date(y, mth, 1) > date(2026, 10, 19): break
        for a in ARTICLES:
            if random.random() < .45: continue
            for city in BR + ["Производство"]:
                if random.random() < .5: continue
                org = "АВТОКОМП" if city == "Производство" else "ANESCOM"
                ff.append((org, f"{y}-{mth:02d}-15", y, mth, city, a[2], a[0], random.choice(["white", "white", "second"]), "демо",
                           round(random.uniform(40, 900) * 1000), "", a[1], "KZT", "Безнал"))
A.executemany("INSERT INTO an_fin_fact (org,date,year,month,city,dept,article,color,basis,sum,counterparty,text,currency,method) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ff)
for k, v in (("fact_to", "2026-10-19"), ("fact_to_ak", "2026-10-19"), ("built", datetime.now().isoformat()), ("rows", str(len(ff))), ("source", "демо")):
    A.execute("INSERT OR REPLACE INTO an_fin_meta VALUES (?,?)", (k, v))
A.commit()
print("analytics ok", len(sales), len(pays), len(cf), len(ff))
