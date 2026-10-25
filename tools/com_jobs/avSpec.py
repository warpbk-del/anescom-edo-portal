# 22-С (чтение, AVTOKOMP_FIX): настройки и факт производства для ресурсных спецификаций.
# av_spec_meta: спецификации, подразделения, статьи калькуляции, ТЧ документов производства; av_spec_rows: строки производства 2025–2026 (выпуск/материалы).
import json, datetime, urllib.request
N, K = datetime.datetime(2025, 1, 1), datetime.datetime(2026, 12, 31, 23, 59, 59)
MD = ib.Метаданные
def push(sec, rows):
    tok = ""
    for l in open(r"D:\anescom_edo\config.env", encoding="utf-8-sig"):
        if l.strip().startswith("EDO_API_TOKEN="): tok = l.split("=", 1)[1].strip().strip('"')
    body = json.dumps({"section": sec, "source": "avtokomp", "replace": True, "rows": rows}, ensure_ascii=False).encode("utf-8")
    rq = urllib.request.Request("https://edo.anescom.kz/api/analytics/audit", data=body, method="POST", headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok})
    try: print(sec, len(rows), urllib.request.urlopen(rq, timeout=120).read().decode()[:50])
    except Exception as e: print(sec, "ОШИБКА:", str(e)[:120])
meta = []
def tq(text, kind, **p):
    try:
        for r in q(text, **p): meta.append({"kind": kind, **{k: s(v) for k, v in r.items()}})
    except Exception as e: meta.append({"kind": kind, "err": str(e)[-150:]})
tq("ВЫБРАТЬ С.Наименование КАК Н, С.Статус КАК Ст, С.ПометкаУдаления КАК Уд ИЗ Справочник.РесурсныеСпецификации КАК С", "spec")
tq("ВЫБРАТЬ П.Наименование КАК Н, П.ПроизводственноеПодразделение КАК Пр ИЗ Справочник.СтруктураПредприятия КАК П", "dept")
tq("ВЫБРАТЬ С.Наименование КАК Н ИЗ Справочник.СтатьиКалькуляции КАК С", "calc")
tq("ВЫБРАТЬ С.Наименование КАК Н ИЗ ПланВидовХарактеристик.СтатьиРасходов КАК С ГДЕ НЕ С.ЭтоГруппа", "exp")
rows = []
for doc in ("ПроизводствоБезЗаказа", "ДвижениеПродукцииИМатериалов", "ВнутреннееПотреблениеТоваров"):
    d = MD.Документы.Найти(doc)
    if d is None: meta.append({"kind": "nodoc", "Н": doc}); continue
    hdr = [d.Реквизиты.Получить(i).Имя for i in range(d.Реквизиты.Количество())]
    dep = next((a for a in ("Подразделение", "ПодразделениеПолучатель", "Склад") if a in hdr), None)
    for j in range(d.ТабличныеЧасти.Количество()):
        t = d.ТабличныеЧасти.Получить(j); at = [t.Реквизиты.Получить(i).Имя for i in range(t.Реквизиты.Количество())]
        meta.append({"kind": "ts", "Н": doc + "." + t.Имя, "Ст": ",".join(at)[:400]})
        if "Номенклатура" not in at or "Количество" not in at: continue
        try:
            for r in q(f"""ВЫБРАТЬ Т.Ссылка КАК Р, Т.Ссылка.Дата КАК Д, {'Т.Ссылка.' + dep if dep else '""'} КАК Пд, Т.Номенклатура.Наименование КАК Н,
                Т.Номенклатура.ЕдиницаИзмерения КАК Е, Т.Количество КАК Кол ИЗ Документ.{doc}.{t.Имя} КАК Т
                ГДЕ Т.Ссылка.Проведен И Т.Ссылка.Дата МЕЖДУ &Н И &К""", Н=N, К=K):
                rows.append({"doc": doc, "ts": t.Имя, "ref": s(r["Р"])[-30:], "d": str(r["Д"])[:10], "dep": s(r["Пд"]), "n": s(r["Н"]), "e": s(r["Е"]), "q": float(r["Кол"] or 0)})
        except Exception as e: meta.append({"kind": "err", "Н": doc + "." + t.Имя, "Ст": str(e)[-150:]})
print("meta", len(meta), "rows", len(rows))
push("av_spec_meta", meta)
for i in range(0, len(rows), 20000): push("av_spec_rows" + ("" if i == 0 else str(i // 20000)), rows[i:i + 20000])
print("ГОТОВО avSpec")
