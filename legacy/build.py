"""6л. История прошлых лет: сверка старых баз БП 3.0 и УНФ и загрузка на портал (источник legacy).

Правила (решение пользователя 18.10.2026):
  продажи и контрагенты — из УНФ; приходы (закупки) — из БП; расход материалов — по УНФ (БП только контроль);
  деньги — из БП (банк и касса), УНФ — контроль. Обмен между базами был кривой: документы сопоставляем
  по дате, сумме, контрагенту (БИН) и номеру; то, что есть только в одной базе, — в отчёт расхождений.
  В самих базах 1С ничего не меняем: неверные документы исключаются в данных портала.

Запуск на сервере:  python build.py [--cutoff 2025-01-01] [--dry]
  читает D:\\anescom_edo\\legacy\\bp|unf\\*.tsv (выгрузка расширения ANESCOM_Reader),
  пишет таблицы *_legacy в D:\\anescom_edo\\data\\analytics.sqlite3 и печатает краткий итог.
"""
import re, sqlite3, sys
from collections import defaultdict
from lg import rows, exists, header, num, out

ARGS = sys.argv[1:]
CUTOFF = ARGS[ARGS.index("--cutoff") + 1] if "--cutoff" in ARGS else "2025-01-01"   # с 2025 — данные КА
DRY = "--dry" in ARGS
import os
DB = os.environ.get("LEGACY_DB", r"D:\anescom_edo\data\analytics.sqlite3")

# ------------------------------------------------------------------ справочники
def catalog(base, name, code_fields):
    res = {}
    for r in rows(base, "cat_" + name):
        code = ""
        for f in code_fields:
            if r.get(f):
                code = r[f].strip()
                break
        res[r["Ссылка_key"]] = {"name": r.get("Наименование", ""), "code": code, "group": r.get("Родитель", ""),
                                "is_group": r.get("ЭтоГруппа") == "1"}
    return res


def ok_doc(r):
    return r.get("Проведен") == "1" and r.get("ПометкаУдаления") != "1"


def pick(r, *names):
    for n in names:
        if r.get(n):
            return r[n]
    return ""


def dnum(no):
    """Номер документа без префиксов: «00НФ-000123» → «123»."""
    d = re.sub(r"\D", "", no or "")
    return d.lstrip("0") or "0"


def low(s):
    return (s or "").lower()


def headers(base, name, keep, filt=None):
    """Шапки проведённых документов: key → dict(keep)."""
    res = {}
    if not exists(base, "doc_" + name):
        return res
    for r in rows(base, "doc_" + name):
        if not ok_doc(r):
            continue
        if filt and not filt(r):
            continue
        res[r["Ссылка_key"]] = {k: r.get(k, "") for k in keep} | {"_doc": name}
    return res


def line_sum(r, incl_vat):
    """Сумма строки с НДС: «Всего», иначе Сумма (+ НДС, если сумма без НДС)."""
    if r.get("Всего"):
        return num(r["Всего"])
    s = num(r.get("Сумма"))
    if not incl_vat:
        s += num(r.get("СуммаНДС"))
    return s


KEEP = ["Ссылка_key", "Дата", "Номер", "Организация", "Контрагент", "Контрагент_key", "СуммаДокумента", "СуммаВключаетНДС",
        "ВидОперации", "ХозяйственнаяОперация", "Склад", "СтруктурнаяЕдиница", "СтруктурноеПодразделение",
        "Подразделение", "Ответственный", "Касса", "СтатьяДвиженияДенежныхСредств", "Статья", "Оплачено"]

# ------------------------------------------------------------------ загрузка
out(f"== legacy build, граница {CUTOFF}{' (без записи)' if DRY else ''}")
bp_cli = catalog("bp", "Контрагенты", ["ИдентификационныйКодЛичности", "РНН"])
unf_cli = catalog("unf", "Контрагенты", ["ИдентификационныйНомер", "РНН"])
bp_item = catalog("bp", "Номенклатура", ["Код"])
unf_item = catalog("unf", "Номенклатура", ["Код"])
out(f"контрагенты БП {len(bp_cli)}, УНФ {len(unf_cli)}; номенклатура БП {len(bp_item)}, УНФ {len(unf_item)}")
# УНФ — главный справочник контрагентов: БИН → наименование УНФ
bin_name = {v["code"]: v["name"] for v in unf_cli.values() if v["code"]}


def client_of(base, h):
    cat = unf_cli if base == "unf" else bp_cli
    c = cat.get(h.get("Контрагент_key"), {})
    code = c.get("code", "")
    name = bin_name.get(code) or c.get("name") or h.get("Контрагент", "")
    return name, (code or h.get("Контрагент_key", ""))


def item_of(base, key, fallback):
    cat = unf_item if base == "unf" else bp_item
    it = cat.get(key, {})
    return it.get("name") or fallback, key, it.get("group", "")


# ------------------------------------------------------------------ продажи
def op(h):
    return low(h.get("ВидОперации") + " " + h.get("ХозяйственнаяОперация"))


SALE_SKIP = ("возврат поставщику", "передача в переработку", "передача на комиссию", "возврат комитенту",
             "перемещ", "списан")


def unf_sales():
    """УНФ: расходные накладные (продажа), минус возвраты от покупателей (приходные накладные «возврат»)."""
    res = []
    hs = headers("unf", "РасходнаяНакладная", KEEP, lambda r: not any(x in op(r) for x in SALE_SKIP))
    for t in ("Запасы", "Товары", "Услуги", "Работы"):
        name = f"ts_РасходнаяНакладная__{t}"
        if not exists("unf", name):
            continue
        for r in rows("unf", name):
            h = hs.get(r["Ссылка_key"])
            if not h:
                continue
            res.append(("sale", h, r))
    hr = headers("unf", "ПриходнаяНакладная", KEEP, lambda r: "возврат от покуп" in op(r))
    for t in ("Запасы", "Товары"):
        name = f"ts_ПриходнаяНакладная__{t}"
        if exists("unf", name):
            for r in rows("unf", name):
                h = hr.get(r["Ссылка_key"])
                if h:
                    res.append(("ret", h, r))
    # розница: отчёты о розничных продажах / чеки, если вели в УНФ
    for d in ("ОтчетОРозничныхПродажах", "ЧекККМ"):
        hh = headers("unf", d, KEEP)
        for t in ("Запасы", "Товары"):
            name = f"ts_{d}__{t}"
            if hh and exists("unf", name):
                for r in rows("unf", name):
                    h = hh.get(r["Ссылка_key"])
                    if h:
                        res.append(("sale", h, r))
    return res, len(hs) + len(hr)


# ------------------------------------------------------------------ закупки
def bp_purchases():
    res = []
    hs = headers("bp", "ПоступлениеТоваровУслуг", KEEP)
    for t in ("Товары", "Услуги"):
        for r in rows("bp", f"ts_ПоступлениеТоваровУслуг__{t}"):
            h = hs.get(r["Ссылка_key"])
            if h:
                res.append(("goods" if t == "Товары" else "services", h, r))
    hv = headers("bp", "ВозвратТоваровПоставщику", KEEP)
    for r in rows("bp", "ts_ВозвратТоваровПоставщику__Товары"):
        h = hv.get(r["Ссылка_key"])
        if h:
            res.append(("return", h, r))
    ho = headers("bp", "ОприходованиеТоваров", KEEP)
    for r in rows("bp", "ts_ОприходованиеТоваров__Товары"):
        h = ho.get(r["Ссылка_key"])
        if h:
            res.append(("posting", h, r))
    return res, hs


# ------------------------------------------------------------------ расход материалов
MAT_DOCS = {  # база: (документ, ТЧ, вид)
    "unf": [("ПроизводствоСборка", "Запасы", "production"), ("СборкаЗапасов", "Запасы", "production"),
            ("СписаниеЗапасов", "Запасы", "writeoff"), ("ПеремещениеЗапасов", "Запасы", "writeoff"),
            ("ЗаказПокупателя", "Материалы", "work_order"), ("ОтчетПереработчика", "Запасы", "production")],
    "bp": [("ТребованиеНакладная", "Материалы", "requirement"), ("СписаниеТоваров", "Товары", "writeoff"),
           ("ОтчетПроизводстваЗаСмену", "Материалы", "production"),
           ("КомплектацияНоменклатуры", "Комплектующие", "assembly")],
}


def materials(base):
    res = []
    for d, t, kind in MAT_DOCS[base]:
        if not exists(base, f"ts_{d}__{t}"):
            continue
        filt = None
        if d == "ПеремещениеЗапасов":
            filt = lambda r: "списан" in op(r) or "расход" in op(r)
        if d == "ЗаказПокупателя":
            filt = lambda r: "наряд" in low(r.get("ВидОперации")) and "закрыт" in low(r.get("СостояниеЗаказа", ""))
        hs = headers(base, d, KEEP + ["СостояниеЗаказа"], filt)
        for r in rows(base, f"ts_{d}__{t}"):
            h = hs.get(r["Ссылка_key"])
            if h:
                res.append((kind, h, r, d))
    return res


# ------------------------------------------------------------------ деньги
MONEY = {
    "bp": [("ПриходныйКассовыйОрдер", "in", "cash"), ("РасходныйКассовыйОрдер", "out", "cash"),
           ("ПлатежноеПоручениеВходящее", "in", "bank"), ("ПлатежноеПоручениеИсходящее", "out", "bank"),
           ("ПлатежныйОрдерПоступлениеДенежныхСредств", "in", "bank"),
           ("ПлатежныйОрдерСписаниеДенежныхСредств", "out", "bank"),
           ("ОплатаОтПокупателяПлатежнойКартой", "in", "card")],
    "unf": [("ПоступлениеВКассу", "in", "cash"), ("РасходИзКассы", "out", "cash"),
            ("ПоступлениеНаСчет", "in", "bank"), ("РасходСоСчета", "out", "bank"),
            ("ОперацияПоПлатежнойКарте", "in", "card")],
}
INTERNAL = ("взнос наличн", "получение наличн", "перемещ", "перевод с", "между счет", "внутрен", "конвертац")


def money(base):
    res = []
    for d, direction, kind in MONEY[base]:
        for h in headers(base, d, KEEP).values():
            if d == "ПлатежноеПоручениеИсходящее" and h.get("Оплачено") not in ("1", ""):
                continue
            internal = any(x in op(h) for x in INTERNAL)
            res.append((direction, kind, internal, h))
    return res


# ------------------------------------------------------------------ сверка БП↔УНФ по документам
def recon(kind, bp_docs, unf_docs):
    """Сопоставить шапки: ключ 1 — дата + сумма + БИН; ключ 2 — дата + номер; ключ 3 — сумма + БИН ±3 дня."""
    def key_rows(base, docs):
        res = []
        for k, h in docs.items():
            name, code = client_of(base, h)
            res.append({"k": k, "date": h["Дата"][:10], "no": h["Номер"], "dn": dnum(h["Номер"]),
                        "sum": round(num(h["СуммаДокумента"]), 0), "code": code, "client": name, "doc": h["_doc"]})
        return res
    B, U = key_rows("bp", bp_docs), key_rows("unf", unf_docs)
    used = set()
    idx1, idx2, idx3 = defaultdict(list), defaultdict(list), defaultdict(list)
    for u in U:
        idx1[(u["date"], u["sum"], u["code"])].append(u)
        idx2[(u["date"], u["dn"])].append(u)
        idx3[(u["sum"], u["code"])].append(u)
    pairs, only_b = [], []
    from datetime import date as _d, timedelta as _t
    for b in B:
        hit = None
        for cand in (idx1.get((b["date"], b["sum"], b["code"]), []), idx2.get((b["date"], b["dn"]), [])):
            hit = next((u for u in cand if u["k"] not in used), None)
            if hit:
                break
        if not hit and b["sum"]:
            try:
                bd = _d.fromisoformat(b["date"])
                hit = next((u for u in idx3.get((b["sum"], b["code"]), []) if u["k"] not in used
                            and abs((_d.fromisoformat(u["date"]) - bd).days) <= 3), None)
            except ValueError:
                hit = None
        if hit:
            used.add(hit["k"])
            pairs.append((b, hit))
        else:
            only_b.append(b)
    only_u = [u for u in U if u["k"] not in used]
    return pairs, only_b, only_u


# ------------------------------------------------------------------ сборка строк для портала
def F(v):
    return f"{v:,.0f}".replace(",", " ")


def month(dt):
    return dt[:7]


sales, purch, mats, cash = [], [], [], []
s_rows, n_sale_docs = unf_sales()
for typ, h, r in s_rows:
    name, code = client_of("unf", h)
    item, ikey, grp = item_of("unf", r.get("Номенклатура_key", ""), r.get("Номенклатура", ""))
    sgn = -1 if typ == "ret" else 1
    incl = h.get("СуммаВключаетНДС") in ("1", "")
    sales.append([h["Дата"][:10], r["Ссылка_key"], h["Номер"], h["Организация"],
                  pick(h, "Подразделение", "СтруктурнаяЕдиница"), h.get("СтруктурнаяЕдиница", ""),
                  h.get("Ответственный", ""), name, code, item, ikey, grp,
                  sgn * num(r.get("Количество")), sgn * line_sum(r, incl), sgn * num(r.get("Себестоимость"))])
out(f"продажи УНФ: строк {len(sales)} (документов {n_sale_docs})")

p_rows, bp_post = bp_purchases()
for typ, h, r in p_rows:
    name, code = client_of("bp", h)
    item, ikey, grp = item_of("bp", r.get("Номенклатура_key", ""), r.get("Номенклатура", "") or r.get("Содержание", ""))
    sgn = -1 if typ == "return" else 1
    incl = h.get("СуммаВключаетНДС") in ("1", "")
    purch.append([h["Дата"][:10], r["Ссылка_key"], h["Номер"], h["Организация"],
                  pick(h, "СтруктурноеПодразделение", "Подразделение"), h.get("Склад", ""), name, code, item, ikey,
                  grp, sgn * num(r.get("Количество")), sgn * line_sum(r, incl), typ])
out(f"закупки БП: строк {len(purch)}")

for base in ("unf", "bp"):
    for kind, h, r, d in materials(base):
        item, ikey, grp = item_of(base, r.get("Номенклатура_key", ""), r.get("Номенклатура", ""))
        mats.append([h["Дата"][:10], r["Ссылка_key"], h["Номер"], h["Организация"],
                     pick(h, "СтруктурнаяЕдиница", "Склад", "Подразделение"), item, ikey, grp,
                     num(r.get("Количество")), num(pick(r, "Сумма", "Стоимость", "СуммаПлановая")), kind, base, d])
# оценка: если в строке расхода нет суммы — количество × средняя цена закупки БП (по наименованию)
price = defaultdict(lambda: [0.0, 0.0])
for r in purch:
    if r[13] == "goods" and r[11] > 0 and r[12] > 0:
        pr = price[low(r[8]).strip()]
        pr[0] += r[12]; pr[1] += r[11]
n_est = 0
for m in mats:
    if not m[9] and m[8]:
        pr = price.get(low(m[5]).strip())
        if pr and pr[1]:
            m[9] = m[8] * pr[0] / pr[1]
            n_est += 1
out(f"оценено по цене закупки: {n_est} строк расхода")
out(f"расход материалов: строк УНФ {sum(1 for m in mats if m[11] == 'unf')}, БП {sum(1 for m in mats if m[11] == 'bp')}")

money_bp, money_unf = money("bp"), money("unf")
for direction, kind, internal, h in money_bp:
    name, code = client_of("bp", h)
    art = "Внутреннее перемещение" if internal else (pick(h, "СтатьяДвиженияДенежныхСредств", "Статья") or "(без статьи)")
    cash.append([h["Дата"][:10], h["Ссылка_key"], h["Номер"], h["Организация"], "", art, name, direction,
                 num(h["СуммаДокумента"]), kind, "bp"])
PAY_OPS = ("покупат", "оплата от", "розничн", "выручк")
pays = []
for direction, kind, internal, h in money_bp:
    if direction == "in" and not internal and (kind == "card" or any(x in op(h) for x in PAY_OPS)) and h["Дата"][:10] < CUTOFF:
        name, code = client_of("bp", h)
        pays.append([h["Дата"][:10], "L:" + h["Ссылка_key"], h["Номер"], h["Организация"], "", "", name,
                     code, kind, num(h["СуммаДокумента"])])
out(f"оплаты клиентов (БП): {len(pays)}")
out(f"деньги БП: документов {len(money_bp)}; УНФ (контроль) {len(money_unf)}")

# ------------------------------------------------------------------ сверка
report = []  # (вид, месяц, bp_n, bp_sum, unf_n, unf_sum, matched_n, only_bp_n, only_bp_sum, only_unf_n, only_unf_sum)
diffs = []   # (вид, база, дата, номер, контрагент, сумма, документ)


def add_recon(kind, bp_docs, unf_docs):
    pairs, ob, ou = recon(kind, bp_docs, unf_docs)
    agg = defaultdict(lambda: [0, 0.0, 0, 0.0, 0, 0, 0.0, 0, 0.0])
    for b, u in pairs:
        a = agg[month(u["date"])]
        a[0] += 1; a[1] += b["sum"]; a[2] += 1; a[3] += u["sum"]; a[4] += 1
    for b in ob:
        a = agg[month(b["date"])]
        a[0] += 1; a[1] += b["sum"]; a[5] += 1; a[6] += b["sum"]
        diffs.append((kind, "bp", b["date"], b["no"], b["client"], b["sum"], b["doc"]))
    for u in ou:
        a = agg[month(u["date"])]
        a[2] += 1; a[3] += u["sum"]; a[7] += 1; a[8] += u["sum"]
        diffs.append((kind, "unf", u["date"], u["no"], u["client"], u["sum"], u["doc"]))
    for m, a in sorted(agg.items()):
        report.append((kind, m, *a))
    out(f"сверка {kind}: пар {len(pairs)} на {F(sum(b['sum'] for b, _u in pairs))}; только БП {len(ob)} "
        f"на {F(sum(b['sum'] for b in ob))}; только УНФ {len(ou)} на {F(sum(u['sum'] for u in ou))}")


add_recon("sales", headers("bp", "РеализацияТоваровУслуг", KEEP),
          headers("unf", "РасходнаяНакладная", KEEP, lambda r: not any(x in op(r) for x in SALE_SKIP)))
add_recon("purchases", bp_post,
          headers("unf", "ПриходнаяНакладная", KEEP, lambda r: "поставщ" in op(r) or not op(r).strip()))
add_recon("cash_in", {str(i): x[3] for i, x in enumerate(money_bp) if x[0] == "in" and not x[2]},
          {str(i): x[3] for i, x in enumerate(money_unf) if x[0] == "in" and not x[2]})
add_recon("cash_out", {str(i): x[3] for i, x in enumerate(money_bp) if x[0] == "out" and not x[2]},
          {str(i): x[3] for i, x in enumerate(money_unf) if x[0] == "out" and not x[2]})

# ------------------------------------------------------------------ итоги по годам
yr = defaultdict(lambda: defaultdict(float))
for r in sales:
    yr[r[0][:4]]["sales"] += r[13]
for r in purch:
    yr[r[0][:4]]["purch"] += r[12]
for r in mats:
    if r[11] == "unf":
        yr[r[0][:4]]["mat_unf"] += r[9]
    else:
        yr[r[0][:4]]["mat_bp"] += r[9]
for r in cash:
    if r[5] != "Внутреннее перемещение":
        yr[r[0][:4]]["in" if r[7] == "in" else "out"] += r[8]
out("год | продажи УНФ | закупки БП | материалы УНФ | материалы БП | поступило | потрачено")
for y in sorted(yr):
    v = yr[y]
    out(f"{y} | {v['sales']:,.0f} | {v['purch']:,.0f} | {v['mat_unf']:,.0f} | {v['mat_bp']:,.0f} | "
        f"{v['in']:,.0f} | {v['out']:,.0f}".replace(",", " "))

# ------------------------------------------------------------------ запись в базу портала
if DRY:
    out("--dry: в базу не пишу")
    sys.exit(0)

TABLES = {
    "an_sales_legacy": ("date, doc_key, doc_no, org, branch, warehouse, manager, client, client_key, item, item_key, "
                        "item_group, qty REAL, sum REAL, cost REAL", sales),
    "an_purchases_legacy": ("date, doc_key, doc_no, org, branch, warehouse, supplier, supplier_key, item, item_key, "
                            "item_group, qty REAL, sum REAL, kind", purch),
    "an_materials_legacy": ("date, doc_key, doc_no, org, branch, item, item_key, item_group, qty REAL, sum REAL, kind, "
                            "base, doc", mats),
    "an_cashflow_legacy": ("date, doc_key, doc_no, org, branch, article, counterparty, direction, sum REAL, kind, base",
                           cash),
    "an_legacy_recon": ("kind, month, bp_n REAL, bp_sum REAL, unf_n REAL, unf_sum REAL, matched REAL, only_bp_n REAL, "
                        "only_bp_sum REAL, only_unf_n REAL, only_unf_sum REAL", report),
    "an_legacy_diff": ("kind, base, date, doc_no, client, sum REAL, doc", diffs),
}
c = sqlite3.connect(DB, timeout=60)
for t, (cols, data) in TABLES.items():
    c.execute(f"DROP TABLE IF EXISTS {t}")
    c.execute(f"CREATE TABLE {t} (id INTEGER PRIMARY KEY AUTOINCREMENT, "
              + ", ".join(x if " " in x.strip() else x.strip() + " TEXT" for x in cols.split(",")) + ")")
    n = len(cols.split(","))
    if t not in ("an_legacy_recon", "an_legacy_diff"):
        data = [r for r in data if r[0] < CUTOFF]
    c.executemany(f"INSERT INTO {t} ({', '.join(x.split()[0] for x in cols.split(','))}) VALUES ({','.join('?' * n)})", data)
    if "date" in cols.split(",")[0]:
        c.execute(f"CREATE INDEX IF NOT EXISTS idx_{t}_date ON {t}(date)")
    out(f"{t}: {len(data)}")
# ---- те же данные в основные таблицы портала (все вкладки + кнопки прошлых лет, решение 18.10.2026 22:43)
# метка doc_key «L:» — строки старых баз; выгрузка КА идёт с 2025 года и их не трогает
MAIN = {
    "an_sales": ("date, doc_key, doc_no, org, branch, warehouse, manager, client, client_key, item, item_key, item_group, "
                 "qty, sum, cost", [[r[0], "L:" + r[1]] + r[2:] for r in sales if r[0] < CUTOFF]),
    "an_cashflow": ("date, doc_key, doc_no, org, branch, article, counterparty, direction, sum",
                    [[r[0], "L:" + r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8]] for r in cash
                     if r[0] < CUTOFF and r[5] != "Внутреннее перемещение"]),
    "an_payments": ("date, doc_key, doc_no, org, branch, manager, client, client_key, kind, sum", pays),
}
for t, (cols, data) in MAIN.items():
    c.execute(f"DELETE FROM {t} WHERE doc_key LIKE 'L:%'")
    n = len(cols.split(","))
    c.executemany(f"INSERT INTO {t} ({cols}) VALUES ({','.join('?' * n)})", data)
    out(f"{t} (старые базы): {len(data)}")
c.execute("CREATE TABLE IF NOT EXISTS an_meta (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, body TEXT NOT NULL)")
import json, datetime
c.execute("INSERT INTO an_meta(ts, body) VALUES (?, ?)", (datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
          json.dumps({"kind": "legacy_build", "cutoff": CUTOFF, "years": {y: dict(v) for y, v in yr.items()}}, ensure_ascii=False)))
c.commit()
c.close()
out("записано")
