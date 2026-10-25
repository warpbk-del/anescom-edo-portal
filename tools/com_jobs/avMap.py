# Проект 22 (чтение): таблица соответствий справочников АВТОКОМП (ib_av) → ANESCOM (ib, копия KA2026).
# Результат: D:\anescom_edo\data\reports\22\map_*.csv (Excel, ;) + сводка на экран. Ничего не пишет в базы.
import csv, os, re
from collections import defaultdict
OUT = r"D:\anescom_edo\data\reports\22"; os.makedirs(OUT, exist_ok=True)
SINCE = datetime.datetime(2025, 1, 1)
def qq(base, text, **params):
    z = base.NewObject("Запрос"); z.Текст = text
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
    t = re.sub(r'\b(ТОО|ИП|АО|ООО|TOO|LLP)\b', " ", t)
    return re.sub(r"[^0-9A-ZА-ЯӘҒҚҢӨҰҮҺІ]+", "", t)
def field(base, sprav, cands):
    m = base.Метаданные.Справочники.Найти(sprav)
    if m is None: return None
    for c in cands:
        if m.Реквизиты.Найти(c) is not None: return c
    return None
def load(base, sprav, key_cands, extra=()):
    kf = field(base, sprav, key_cands)
    m = base.Метаданные.Справочники.Найти(sprav)
    grp = " И НЕ С.ЭтоГруппа" if m.Иерархический else ""
    ex = [e for e in extra if m.Реквизиты.Найти(e) is not None]
    sel = ", ".join([f"С.{kf} КАК Ключ"] if kf else []) + "".join(f", С.{e} КАК {e}" for e in ex)
    try:
        rows = qq(base, f"ВЫБРАТЬ С.Ссылка КАК Ссылка, С.Код КАК Код, С.Наименование КАК Имя{', ' + sel if sel else ''} ИЗ Справочник.{sprav} КАК С ГДЕ НЕ С.ПометкаУдаления{grp}")
    except Exception:
        rows = qq(base, f"ВЫБРАТЬ С.Ссылка КАК Ссылка, С.Код КАК Код, С.Наименование КАК Имя{', ' + sel if sel else ''} ИЗ Справочник.{sprav} КАК С ГДЕ НЕ С.ПометкаУдаления")
    for r in rows:
        r["Ключ"] = re.sub(r"\s", "", ss(base, r.get("Ключ", ""))) if kf else ""
        for e in ex: r[e] = ss(base, r[e])
    return rows, kf, ex
def used_set(base, text):
    try: return {ss(base, r["Х"]) for r in qq(base, text, Н=SINCE)}
    except Exception as e:
        print("   (использование не определено:", str(e)[-80:], ")"); return None
SPR = [  # справочник, ключ (БИН/ИИН/артикул), доп. поля, запрос «используется с 2025»
    ("Контрагенты", ["ИдентификационныйКодЛичности", "БИН", "ИИН", "ИНН", "БИНИИН"], ("Партнер",),
     "ВЫБРАТЬ РАЗЛИЧНЫЕ Т.СубконтоДт1 КАК Х ИЗ РегистрБухгалтерии.{REG}.ДвиженияССубконто(&Н, , ) КАК Т"),
    ("Партнеры", [], (), None),
    ("Номенклатура", ["Артикул"], ("ЕдиницаИзмерения", "ВидНоменклатуры"),
     "ВЫБРАТЬ РАЗЛИЧНЫЕ Т.Номенклатура КАК Х ИЗ РегистрНакопления.ТоварыНаСкладах.Обороты(&Н, , , ) КАК Т"),
    ("Склады", [], (), None),
    ("СтруктураПредприятия", [], (), None),
    ("ФизическиеЛица", ["ИдентификационныйНомер", "ИИН", "ИдентификационныйКодЛичности"], (), None),
    ("СтатьиДвиженияДенежныхСредств", [], (), None),
]
summary = []
for sprav, kc, extra, used_q in SPR:
    try:
        A, kfa, exa = load(ib_av, sprav, kc, extra)
        B, kfb, exb = load(ib, sprav, kc, extra)
    except Exception as e:
        print(sprav, "ОШИБКА", str(e)[-120:]); continue
    used = None
    if used_q:
        regA = ib_av.Метаданные.РегистрыБухгалтерии.Получить(0).Имя
        used = used_set(ib_av, used_q.replace("{REG}", regA))
    byK, byN = defaultdict(list), defaultdict(list)
    for b in B:
        if b["Ключ"] and len(b["Ключ"]) >= 3: byK[b["Ключ"]].append(b)
        byN[norm(ss(ib, b["Имя"]))].append(b)
    cnt = defaultdict(int)
    fn = os.path.join(OUT, f"map_{sprav}.csv")
    with open(fn, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Справочник", "АВТОКОМП код", "АВТОКОМП наименование", "Ключ (" + (kfa or "—") + ")", *exa, "Используется с 2025",
                    "Статус", "ANESCOM код", "ANESCOM наименование", *[f"ANESCOM {e}" for e in exb], "Решение (заполнить)"])
        for a in A:
            nm = ss(ib_av, a["Имя"]); hit, how = [], ""
            if a["Ключ"] and len(a["Ключ"]) >= 3 and byK.get(a["Ключ"]): hit, how = byK[a["Ключ"]], "совпал по " + (kfa or "ключу")
            elif byN.get(norm(nm)): hit, how = byN[norm(nm)], "совпал по наименованию"
            if hit and extra and sprav == "Номенклатура" and ss(ib, hit[0].get("ЕдиницаИзмерения", "")) != a.get("ЕдиницаИзмерения", ""):
                how += " ⚠ другая ед. изм."
            st = ("неоднозначно (" + str(len(hit)) + ")") if len(hit) > 1 else (how if hit else "НОВЫЙ")
            u = "" if used is None else ("да" if ss(ib_av, a["Ссылка"]) in used else "нет")
            if u == "нет" and not hit: st = "не используется — не переносить"
            cnt[st.split(" (")[0].split(" ⚠")[0]] += 1
            b = hit[0] if hit else {}
            w.writerow([sprav, ss(ib_av, a["Код"]), nm, a["Ключ"], *[a.get(e, "") for e in exa], u, st,
                        ss(ib, b.get("Код", "")) if b else "", ss(ib, b.get("Имя", "")) if b else "", *[b.get(e, "") for e in exb], ""])
    line = f"{sprav}: АВТОКОМП {len(A)} | ANESCOM {len(B)} | " + ", ".join(f"{k} {v}" for k, v in sorted(cnt.items(), key=lambda x: -x[1]))
    print(line); summary.append(line)
with open(os.path.join(OUT, "_сводка.txt"), "w", encoding="utf-8") as f: f.write("\n".join(summary))
print("Файлы:", OUT)
