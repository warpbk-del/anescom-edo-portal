# 22-И (чтение, копия ANESCOM): куда делся белый профиль, списанный 08.09.2026 со склада «Ламинация Автокомп» (00НФ-000009).
# 1) обороты склада «Ламинация Автокомп» 2025–2026 по товару и виду документа; 2) все ТЧ «Передача сырья переработчику» и «Поступление от переработчика» 2025–2026.
import json, datetime, urllib.request
N, K = datetime.datetime(2025, 1, 1), datetime.datetime(2026, 12, 31, 23, 59, 59)
S = q('ВЫБРАТЬ С.Ссылка КАК С ИЗ Справочник.Склады КАК С ГДЕ С.Наименование ПОДОБНО "%Ламинац%" И НЕ С.ЭтоГруппа')[0]["С"]
mov = [{"nom": s(r["Н"]), "type": s(r["Т"]), "m": str(r["М"])[:7], "in": float(r["П"] or 0), "out": float(r["Р"] or 0)} for r in q("""
ВЫБРАТЬ Т.Номенклатура КАК Н, ТИПЗНАЧЕНИЯ(Т.Регистратор) КАК Т, НАЧАЛОПЕРИОДА(Т.Период, МЕСЯЦ) КАК М, СУММА(Т.ВНаличииПриход) КАК П, СУММА(Т.ВНаличииРасход) КАК Р
ИЗ РегистрНакопления.ТоварыНаСкладах.ОстаткиИОбороты(&Н, &К, Регистратор, , Склад = &С) КАК Т
СГРУППИРОВАТЬ ПО Т.Номенклатура, ТИПЗНАЧЕНИЯ(Т.Регистратор), НАЧАЛОПЕРИОДА(Т.Период, МЕСЯЦ)""", Н=N, К=K, С=S)]
MD = ib.Метаданные.Документы; pr = []
for doc in ("ПередачаСырьяПереработчику", "ПоступлениеОтПереработчика", "ОтчетПереработчика"):
    d = MD.Найти(doc)
    if d is None: print("нет", doc); continue
    for i in range(d.ТабличныеЧасти.Количество()):
        t = d.ТабличныеЧасти.Получить(i); at = [t.Реквизиты.Получить(j).Имя for j in range(t.Реквизиты.Количество())]
        if "Номенклатура" not in at or "Количество" not in at: continue
        try:
            rows = q(f"""ВЫБРАТЬ Т.Номенклатура КАК Н, НАЧАЛОПЕРИОДА(Т.Ссылка.Дата, МЕСЯЦ) КАК М, СУММА(Т.Количество) КАК Ч, КОЛИЧЕСТВО(РАЗЛИЧНЫЕ Т.Ссылка) КАК Д
            ИЗ Документ.{doc}.{t.Имя} КАК Т ГДЕ Т.Ссылка.Проведен И Т.Ссылка.Дата МЕЖДУ &Н И &К СГРУППИРОВАТЬ ПО Т.Номенклатура, НАЧАЛОПЕРИОДА(Т.Ссылка.Дата, МЕСЯЦ)""", Н=N, К=K)
        except Exception as e:
            print(doc, t.Имя, "ошибка:", str(e)[-80:]); continue
        print(doc, t.Имя, "строк", len(rows), "кол", round(sum(float(r["Ч"] or 0) for r in rows)))
        pr += [{"doc": doc, "ts": t.Имя, "nom": s(r["Н"]), "m": str(r["М"])[:7], "qty": float(r["Ч"] or 0), "n": int(r["Д"])} for r in rows]
tok = ""
for l in open(r"D:\anescom_edo\config.env", encoding="utf-8-sig"):
    if l.strip().startswith("EDO_API_TOKEN="): tok = l.split("=", 1)[1].strip().strip('"')
for sec, rows_ in (("inv22_lam_mov", mov), ("inv22_lam_proc", pr)):
    body = json.dumps({"section": sec, "source": "anescom", "replace": True, "rows": rows_}, ensure_ascii=False).encode("utf-8")
    rq = urllib.request.Request("https://edo.anescom.kz/api/analytics/audit", data=body, method="POST", headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok})
    try: print(sec, len(rows_), urllib.request.urlopen(rq, timeout=90).read().decode()[:80])
    except Exception as e: print(sec, "ОШИБКА:", str(e)[:150])
print("ГОТОВО inv22Lam")
