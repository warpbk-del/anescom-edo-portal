"""6л. Разбор завышений перед боевой загрузкой: python diag.py [money|sales|cin|all]
money — расходы БП по видам документов / операциям / годам и крупнейшие (поиск дублей и внутренних);
sales — продажи помесячно: УНФ (расходные) против БП (реализации);
cin   — поступления денег БП против УНФ, «только БП» по видам и крупнейшие.
Вывод короткий (для буфера обмена RDP).
"""
import sys
from collections import defaultdict
from lg import rows, exists, num, out

WHAT = sys.argv[1] if len(sys.argv) > 1 else "all"
M = 1e6


def ok(r):
    return r.get("Проведен") == "1" and r.get("ПометкаУдаления") != "1"


def docs(base, name, cols=None):
    if not exists(base, "doc_" + name):
        return []
    return [r for r in rows(base, "doc_" + name, cols) if ok(r)]


COLS = ["Ссылка_key", "Проведен", "ПометкаУдаления", "Дата", "Номер", "Организация", "Контрагент", "СуммаДокумента",
        "ВидОперации", "ХозяйственнаяОперация", "СтатьяДвиженияДенежныхСредств", "Оплачено", "ВалютаДокумента",
        "СчетОрганизации", "Касса", "БанковскийСчет", "СчетКонтрагента", "КурсВзаиморасчетов"]
BP_OUT = ["РасходныйКассовыйОрдер", "ПлатежноеПоручениеИсходящее", "ПлатежныйОрдерСписаниеДенежныхСредств"]
BP_IN = ["ПриходныйКассовыйОрдер", "ПлатежноеПоручениеВходящее", "ПлатежныйОрдерПоступлениеДенежныхСредств",
         "ОплатаОтПокупателяПлатежнойКартой"]
UNF_OUT = ["РасходИзКассы", "РасходСоСчета"]
UNF_IN = ["ПоступлениеВКассу", "ПоступлениеНаСчет", "ОперацияПоПлатежнойКарте"]


def short(s, n=28):
    s = (s or "").replace("\t", " ")
    return s if len(s) <= n else s[:n - 1] + "…"


def money_block(base, names, title):
    out(f"== {title}")
    by = defaultdict(lambda: [0, 0.0])
    allr = []
    for d in names:
        for r in docs(base, d, COLS):
            y = r["Дата"][:4]
            s = num(r["СуммаДокумента"])
            o = short(r.get("ВидОперации") or r.get("ХозяйственнаяОперация"), 34)
            by[(d, o)][0] += 1
            by[(d, o)][1] += s
            by[(y, d)][0] += 1
            by[(y, d)][1] += s
            allr.append((s, y, d, o, r))
    # по видам документов × операциям (топ по сумме)
    ops = sorted(((k, v) for k, v in by.items() if not k[0][:2].isdigit()), key=lambda x: -x[1][1])
    for (d, o), (n, s) in ops[:18]:
        out(f"{short(d, 22)} | {o} | {n} | {s / M:,.0f} млн")
    # по годам × документам
    for (y, d), (n, s) in sorted((k, v) for k, v in by.items() if k[0][:2].isdigit()):
        if y >= "2019":
            out(f"{y} {short(d, 26)}: {n} док, {s / M:,.0f} млн")
    # валюта / оплачено
    cur = defaultdict(float)
    paid = defaultdict(float)
    for s, y, d, o, r in allr:
        cur[r.get("ВалютаДокумента", "")] += s
        if d == "ПлатежноеПоручениеИсходящее":
            paid[r.get("Оплачено", "")] += s
    out("валюта: " + "; ".join(f"{k or '-'} {v / M:,.0f}" for k, v in sorted(cur.items(), key=lambda x: -x[1])[:5]))
    if paid:
        out("ПП исходящее, Оплачено: " + "; ".join(f"{k or '-'} {v / M:,.0f}" for k, v in paid.items()))
    # крупнейшие
    allr.sort(key=lambda x: -x[0])
    out("крупнейшие:")
    for s, y, d, o, r in allr[:15]:
        out(f"{r['Дата'][:10]} {short(d, 18)} №{r['Номер']} {s / M:,.1f} млн | {o} | {short(r.get('Контрагент'), 26)}"
            f" | {short(r.get('СтатьяДвиженияДенежныхСредств'), 20)}")
    # пары ПП исходящее ↔ платёжный ордер списания (одна оплата двумя документами?)
    if "ПлатежноеПоручениеИсходящее" in names and "ПлатежныйОрдерСписаниеДенежныхСредств" in names:
        key = defaultdict(int)
        for s, y, d, o, r in allr:
            if d == "ПлатежныйОрдерСписаниеДенежныхСредств":
                key[(r["Дата"][:10], round(s), r.get("Контрагент"))] += 1
        dup = sum(s for s, y, d, o, r in allr if d == "ПлатежноеПоручениеИсходящее"
                  and key.get((r["Дата"][:10], round(s), r.get("Контрагент"))))
        out(f"ПП исходящее, совпавшие с ордером списания (дата+сумма+контрагент): {dup / M:,.0f} млн")
    # распределение: доля суммы в документах > 1 млрд
    big = sum(s for s, *_ in allr if s >= 1e9)
    out(f"документов ≥ 1 млрд: {sum(1 for s, *_ in allr if s >= 1e9)} на {big / M:,.0f} млн из {sum(s for s, *_ in allr) / M:,.0f}")


def sales_block():
    out("== продажи по месяцам: УНФ расходные | БП реализации (млн)")
    agg = defaultdict(lambda: [0, 0.0, 0, 0.0])
    for r in docs("unf", "РасходнаяНакладная", COLS):
        a = agg[r["Дата"][:7]]
        a[0] += 1; a[1] += num(r["СуммаДокумента"])
    ops = defaultdict(float)
    for r in docs("bp", "РеализацияТоваровУслуг", COLS):
        a = agg[r["Дата"][:7]]
        a[2] += 1; a[3] += num(r["СуммаДокумента"])
        ops[short(r.get("ВидОперации"), 30)] += num(r["СуммаДокумента"])
    for m, (un, us, bn, bs) in sorted(agg.items()):
        if m >= "2019":
            out(f"{m} | {un} {us / M:,.1f} | {bn} {bs / M:,.1f}")
    out("БП реализации по ВидОперации: " + "; ".join(f"{k or '-'} {v / M:,.0f}" for k, v in
                                                       sorted(ops.items(), key=lambda x: -x[1])[:6]))


if WHAT in ("money", "all"):
    money_block("bp", BP_OUT, "БП расход денег")
if WHAT in ("cin", "all"):
    money_block("bp", BP_IN, "БП поступление денег")
    money_block("unf", UNF_IN, "УНФ поступление денег (контроль)")
if WHAT in ("uout",):
    money_block("unf", UNF_OUT, "УНФ расход денег (контроль)")
if WHAT in ("sales", "all"):
    sales_block()
