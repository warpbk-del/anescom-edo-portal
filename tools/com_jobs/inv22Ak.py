# 22-И (чтение, копия ANESCOM): склады ANESCOM «Автокомп» / «Ламинация Автокомп» —
# пересчёты товаров (статус, проведён, учёт/факт), списания недостач, оприходования излишков с 01.01.2024 по табличным частям.
# Результат: POST /api/analytics/audit inv22_ak_docs, inv22_ak_lines (портал, админ).
import json, datetime, urllib.request
N, K = datetime.datetime(2024, 1, 1), datetime.datetime(2026, 12, 31, 23, 59, 59)
sk = q('ВЫБРАТЬ С.Ссылка КАК С, С.Наименование КАК Н ИЗ Справочник.Склады КАК С ГДЕ С.Наименование ПОДОБНО "%втоком%" И НЕ С.ЭтоГруппа')
print("склады:", [s(r["Н"]) for r in sk])
arr = ib.NewObject("Массив")
for r in sk: arr.Добавить(r["С"])
MD = ib.Метаданные.Документы
def attrs(doc, ts="Товары"):
    try:
        t = MD.Найти(doc).ТабличныеЧасти.Найти(ts)
        return [t.Реквизиты.Получить(i).Имя for i in range(t.Реквизиты.Количество())]
    except Exception as e:
        print(doc, "нет ТЧ:", str(e)[-60:]); return []
def hdr(doc):
    d = MD.Найти(doc); return [d.Реквизиты.Получить(i).Имя for i in range(d.Реквизиты.Количество())]
docs, lines = [], []
for doc in ("ПересчетТоваров", "СписаниеНедостачТоваров", "ОприходованиеИзлишковТоваров"):
    if MD.Найти(doc) is None: print("нет документа", doc); continue
    a, h = attrs(doc), hdr(doc)
    print(doc, "ТЧ:", ",".join(a)[:200]); print("   шапка:", ",".join(x for x in h if x in ("Склад", "Статус", "Ответственный", "Исполнитель", "Комментарий", "Организация")))
    num = [x for x in a if x.startswith("Количество") or x in ("Сумма", "Цена", "Отклонение")]
    extra = "".join(f", Т.{x} КАК {x}" for x in num)
    stat = ", Т.Ссылка.Статус КАК Статус" if "Статус" in h else ""
    otv = ", Т.Ссылка.Ответственный КАК Отв" if "Ответственный" in h else ""
    rows = q(f"""ВЫБРАТЬ Т.Ссылка КАК Р, Т.Ссылка.Дата КАК Д, Т.Ссылка.Склад КАК Ск, Т.Ссылка.Проведен КАК Пр, Т.Ссылка.Автор КАК Авт, Т.НомерСтроки КАК НС,
        Т.Номенклатура КАК Н{extra}{stat}{otv}
      ИЗ Документ.{doc}.Товары КАК Т ГДЕ Т.Ссылка.Дата МЕЖДУ &Н И &К И НЕ Т.Ссылка.ПометкаУдаления И Т.Ссылка.Склад В (&М)""", Н=N, К=K, М=arr)
    agg = {}
    for r in rows:
        d = s(r["Р"]); L = {"kind": doc, "doc": d, "date": str(r["Д"])[:10], "sklad": s(r["Ск"]), "posted": bool(r["Пр"]), "line": int(r["НС"]), "nom": s(r["Н"])}
        for x in num: L[x] = float(r[x] or 0)
        lines.append(L)
        g = agg.setdefault(d, {"kind": doc, "doc": d, "date": L["date"], "sklad": L["sklad"], "posted": L["posted"], "rows": 0,
                               "status": s(r["Статус"]) if stat else "", "otv": s(r["Отв"]) if otv else "", "author": s(r["Авт"])})
        g["rows"] += 1
        for x in num: g[x] = g.get(x, 0) + L[x]
    for g in agg.values():
        docs.append(g); print(" ", g["doc"][:58], "|", g["sklad"][:24], "|", "пров" if g["posted"] else "НЕ пров", g["status"][:12], "|", g["rows"], "стр |",
                             " ".join(f"{k}={v:,.0f}" for k, v in g.items() if k in num))
tok = ""
for l in open(r"D:\anescom_edo\config.env", encoding="utf-8-sig"):
    if l.strip().startswith("EDO_API_TOKEN="): tok = l.split("=", 1)[1].strip().strip('"')
for sec, rows_ in (("inv22_ak_docs", docs), ("inv22_ak_lines", lines)):
    body = json.dumps({"section": sec, "source": "anescom", "replace": True, "rows": rows_}, ensure_ascii=False).encode("utf-8")
    rq = urllib.request.Request("https://edo.anescom.kz/api/analytics/audit", data=body, method="POST",
                                headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok})
    try: print(sec, urllib.request.urlopen(rq, timeout=60).read().decode()[:100])
    except Exception as e: print(sec, "ОШИБКА:", str(e)[:150])
print("ГОТОВО inv22Ak")
