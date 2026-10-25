# 22-И (чтение): недостачи по инвентаризации АВТОКОМП (ib_av) ↔ излишки в филиалах ANESCOM (ib) с 01.01.2025.
# По БУ: недостача = Кт 13xx регистратором «Списание недостач товаров»; излишек = Дт 13xx регистратором «Оприходование излишков товаров».
# Плюс: закупки ANESCOM у АВТОКОМП по тем же товарам и расход в производство АВТОКОМП. CSV: D:\anescom_edo\data\reports\22\inv_*.csv
import csv, os, re
from collections import defaultdict
OUT = r"D:\anescom_edo\data\reports\22"; os.makedirs(OUT, exist_ok=True)
N, K = globals().get("INV_FROM", datetime.datetime(2025, 1, 1)), datetime.datetime(2026, 12, 31, 23, 59, 59)
def qq(base, text, **params):
    z = base.NewObject("Запрос"); z.Текст = text.replace("{REG}", base.Метаданные.РегистрыБухгалтерии.Получить(0).Имя)
    for k, v in params.items(): z.УстановитьПараметр(k, v)
    res = z.Выполнить(); cols = [res.Колонки.Получить(i).Имя for i in range(res.Колонки.Количество())]
    out, sel = [], res.Выбрать()
    while sel.Следующий(): out.append({c: getattr(sel, c) for c in cols})
    return out
def ss(base, v):
    try: return base.String(v)
    except Exception: return str(v)
def norm(t):
    t = (t or "").upper().replace("Ё", "Е")
    return re.sub(r"[^0-9A-ZА-ЯӘҒҚҢӨҰҮҺІ]+", "", t)
def doc_rows(base, doc, side):
    acc = "СчетКт" if side == "Кт" else "СчетДт"
    return qq(base, f"""ВЫБРАТЬ Т.Период КАК П, Т.Регистратор КАК Р, Т.Организация КАК Орг, Т.Субконто{side}1 КАК Н, Т.Субконто{side}2 КАК С2, Т.Субконто{side}3 КАК С3,
      Т.Количество{side} КАК Кол, Т.Сумма КАК Сум, Т.{acc}.Код КАК Сч, Т.Подразделение{side} КАК Подр
    ИЗ РегистрБухгалтерии.{{REG}}.ДвиженияССубконто(&Н, &К, {acc}.Код ПОДОБНО "13%" И Регистратор ССЫЛКА Документ.{doc}) КАК Т""", Н=N, К=K)
def art(base, refs):
    out = {}
    for r in refs:
        try: out[ss(base, r)] = (ss(base, r.Артикул), ss(base, r.ЕдиницаИзмерения))
        except Exception: out[ss(base, r)] = ("", "")
    return out
print("== Виды документов движения 13xx в АВТОКОМП с", N.date(), "(Кт = расход): вид | строк | сумма млн")
for r in qq(ib_av, """ВЫБРАТЬ ТИПЗНАЧЕНИЯ(Т.Регистратор) КАК Т, КОЛИЧЕСТВО(*) КАК Н, СУММА(Т.Сумма) КАК С
ИЗ РегистрБухгалтерии.{REG}.ДвиженияССубконто(&Н, &К, СчетКт.Код ПОДОБНО "13%" И НЕ СчетДт.Код ПОДОБНО "13%") КАК Т СГРУППИРОВАТЬ ПО ТИПЗНАЧЕНИЯ(Т.Регистратор)""", Н=N, К=K):
    print(f"  {ss(ib_av, r['Т'])[:45]} | {r['Н']} | {float(r['С'] or 0)/1e6:,.2f}")
short = doc_rows(ib_av, "СписаниеНедостачТоваров", "Кт")
surp_av = doc_rows(ib_av, "ОприходованиеИзлишковТоваров", "Дт")
surp = doc_rows(ib, "ОприходованиеИзлишковТоваров", "Дт")
print(f"== АВТОКОМП: недостачи {len(short)} строк {sum(float(r['Сум']) for r in short)/1e6:,.2f} млн; излишки {len(surp_av)} строк {sum(float(r['Сум']) for r in surp_av)/1e6:,.2f} млн")
print(f"== ANESCOM: излишки {len(surp)} строк {sum(float(r['Сум']) for r in surp)/1e6:,.2f} млн")
# документы недостач: кто, склад, сумма
docs = defaultdict(lambda: [0.0, 0, None])
for r in short: d = docs[ss(ib_av, r["Р"])]; d[0] += float(r["Сум"]); d[1] += 1; d[2] = r["Р"]
with open(os.path.join(OUT, "inv_docs_avtokomp.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f, delimiter=";"); w.writerow(["Документ", "Склад", "Ответственный", "Автор", "Комментарий", "Строк", "Сумма"])
    for n, (sm, c, ref) in sorted(docs.items(), key=lambda x: -x[1][0]):
        g = lambda a: ss(ib_av, getattr(ref, a)) if True else ""
        vals = []
        for a in ("Склад", "Ответственный", "Автор", "Комментарий"):
            try: vals.append(ss(ib_av, getattr(ref, a)))
            except Exception: vals.append("")
        w.writerow([n, *vals, c, round(sm, 2)])
        print(f"  {n[:60]} | склад {vals[0][:25]} | отв. {vals[1][:25]} | автор {vals[2][:25]} | {sm/1e6:,.2f} млн")
# товары: ключ = артикул или нормализованное имя
A = art(ib_av, {r["Н"] for r in short}); B = art(ib, {r["Н"] for r in surp})
def key(base, ref, arts):
    a = arts.get(ss(base, ref), ("", ""))[0]
    return ("A:" + norm(a)) if len(norm(a)) >= 3 else ("N:" + norm(ss(base, ref)))
S, P = defaultdict(lambda: {"кол": 0.0, "сум": 0.0, "имя": "", "мес": set()}), defaultdict(lambda: {"кол": 0.0, "сум": 0.0, "имя": "", "фил": defaultdict(float), "мес": set()})
for r in short:
    k = key(ib_av, r["Н"], A); x = S[k]; x["кол"] += float(r["Кол"] or 0); x["сум"] += float(r["Сум"]); x["имя"] = ss(ib_av, r["Н"]); x["мес"].add(str(r["П"])[:7])
for r in surp:
    k = key(ib, r["Н"], B); x = P[k]; x["кол"] += float(r["Кол"] or 0); x["сум"] += float(r["Сум"]); x["имя"] = ss(ib, r["Н"]); x["мес"].add(str(r["П"])[:7])
    x["фил"][ss(ib, r["Орг"]).replace('Филиал ТОО "ANESCOM/АНЕСКОМ"', "").strip() or ss(ib, r["Орг"])[:20]] += float(r["Кол"] or 0)
# закупки ANESCOM у АВТОКОМП (Дт13 Кт3310, контрагент АВТОКОМП) — по тем же товарам
buy = defaultdict(float)
for r in qq(ib, """ВЫБРАТЬ Т.СубконтоДт1 КАК Н, СУММА(Т.КоличествоДт) КАК Кол ИЗ РегистрБухгалтерии.{REG}.ДвиженияССубконто(&Н, &К, СчетДт.Код ПОДОБНО "13%" И СчетКт.Код ПОДОБНО "33%") КАК Т
ГДЕ Т.СубконтоКт1.Наименование ПОДОБНО "%АВТОКОМП%" СГРУППИРОВАТЬ ПО Т.СубконтоДт1""", Н=N, К=K):
    buy[key(ib, r["Н"], art(ib, [r["Н"]]))] += float(r["Кол"] or 0)
rows = []
for k, x in S.items():
    p = P.get(k); m = min(x["кол"], p["кол"]) if p else 0
    rows.append([x["имя"], k[2:], round(x["кол"], 3), round(x["сум"], 2), ", ".join(sorted(x["мес"])),
                 round(p["кол"], 3) if p else 0, round(p["сум"], 2) if p else 0, ", ".join(f"{f} {q:g}" for f, q in p["фил"].items()) if p else "",
                 ", ".join(sorted(p["мес"])) if p else "", round(m, 3), round(x["сум"] * (m / x["кол"]) if x["кол"] else 0, 2), round(buy.get(k, 0), 3),
                 "СОВПАДАЕТ" if m > 0 else ""])
rows.sort(key=lambda r: -r[10])
with open(os.path.join(OUT, "inv_match.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["Товар (АВТОКОМП)", "Ключ", "Недостача кол.", "Недостача сумма", "Месяцы недостач", "Излишки ANESCOM кол.", "Излишки ANESCOM сумма",
                "Излишки по филиалам", "Месяцы излишков", "Совпадает кол.", "Совпадает сумма (по с/с АВТОКОМП)", "ANESCOM закупал у АВТОКОМП, кол.", "Признак"])
    w.writerows(rows)
mt = [r for r in rows if r[9] > 0]
print(f"== СОВПАДЕНИЯ: товаров {len(mt)} из {len(rows)}; сумма недостач по ним {sum(r[10] for r in mt)/1e6:,.2f} млн из {sum(r[3] for r in rows)/1e6:,.2f} млн")
for r in mt[:25]:
    print(f"  {r[0][:40]} | недостача {r[2]:g} | излишки {r[5]:g} ({r[7][:40]}) | совп. {r[9]:g} на {r[10]:,.0f} | закупал у АВТОКОМП {r[11]:g}")
print("Файлы:", OUT)
