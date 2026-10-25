# 22-И (чтение, копия ANESCOM): материалы ламинации на складе «Автокомп» (пересчёт НФ-00000005 01.09.2025, факт 0, не списано).
# По каждой позиции склада «Автокомп» и «Ламинация Автокомп»: остаток сейчас, обороты по видам документов 2024–2026, поставщики и средняя цена.
import json, datetime, urllib.request
from collections import defaultdict
N, K = datetime.datetime(2024, 1, 1), datetime.datetime(2026, 12, 31, 23, 59, 59)
sk = q('ВЫБРАТЬ С.Ссылка КАК С, С.Наименование КАК Н ИЗ Справочник.Склады КАК С ГДЕ С.Наименование ПОДОБНО "%втоком%" И НЕ С.ЭтоГруппа')
arr = ib.NewObject("Массив")
for r in sk: arr.Добавить(r["С"])
rows = q("""ВЫБРАТЬ Т.Склад КАК Ск, Т.Номенклатура КАК Н, ТИПЗНАЧЕНИЯ(Т.Регистратор) КАК Т, ГОД(Т.Период) КАК Г, СУММА(Т.ВНаличииПриход) КАК П, СУММА(Т.ВНаличииРасход) КАК Р
ИЗ РегистрНакопления.ТоварыНаСкладах.ОстаткиИОбороты(&Н, &К, Регистратор, , Склад В (&М)) КАК Т СГРУППИРОВАТЬ ПО Т.Склад, Т.Номенклатура, ТИПЗНАЧЕНИЯ(Т.Регистратор), ГОД(Т.Период)""", Н=N, К=K, М=arr)
mov = [{"sklad": s(r["Ск"]), "nom": s(r["Н"]), "type": s(r["Т"]), "year": int(r["Г"]), "in": float(r["П"] or 0), "out": float(r["Р"] or 0)} for r in rows]
ost = q("""ВЫБРАТЬ Т.Склад КАК Ск, Т.Номенклатура КАК Н, Т.ВНаличииОстаток КАК О ИЗ РегистрНакопления.ТоварыНаСкладах.Остатки(, Склад В (&М)) КАК Т""", М=arr)
bal = [{"sklad": s(r["Ск"]), "nom": s(r["Н"]), "qty": float(r["О"] or 0)} for r in ost if abs(float(r["О"] or 0)) > 0.0005]
noms = ib.NewObject("Массив"); seen = set()
for r in ost:
    if s(r["Н"]) not in seen: seen.add(s(r["Н"])); noms.Добавить(r["Н"])
for r in q('ВЫБРАТЬ РАЗЛИЧНЫЕ Т.Номенклатура КАК Н ИЗ Документ.ПересчетТоваров.Товары КАК Т ГДЕ Т.Ссылка.Склад В (&М)', М=arr):
    if s(r["Н"]) not in seen: seen.add(s(r["Н"])); noms.Добавить(r["Н"])
buy = [{"nom": s(r["Н"]), "supplier": s(r["К"]), "year": int(r["Г"]), "qty": float(r["Кол"] or 0), "sum": round(float(r["Сум"] or 0), 2), "unit": s(r["Е"])} for r in q("""
ВЫБРАТЬ Т.Номенклатура КАК Н, Т.Ссылка.Контрагент КАК К, ГОД(Т.Ссылка.Дата) КАК Г, СУММА(Т.Количество) КАК Кол, СУММА(Т.Сумма) КАК Сум, Т.Номенклатура.ЕдиницаИзмерения КАК Е
ИЗ Документ.ПриобретениеТоваровУслуг.Товары КАК Т ГДЕ Т.Ссылка.Проведен И Т.Номенклатура В (&М) И Т.Ссылка.Дата >= &Н
СГРУППИРОВАТЬ ПО Т.Номенклатура, Т.Ссылка.Контрагент, ГОД(Т.Ссылка.Дата), Т.Номенклатура.ЕдиницаИзмерения""", М=noms, Н=datetime.datetime(2023, 1, 1))]
print("движений", len(mov), "| остатков", len(bal), "| закупок", len(buy))
for b in sorted(bal, key=lambda x: -abs(x["qty"]))[:15]: print(f"  {b['sklad'][:20]} | {b['nom'][:55]} | {b['qty']:,.1f}")
tok = ""
for l in open(r"D:\anescom_edo\config.env", encoding="utf-8-sig"):
    if l.strip().startswith("EDO_API_TOKEN="): tok = l.split("=", 1)[1].strip().strip('"')
for sec, rows_ in (("inv22_ak_mov", mov), ("inv22_ak_bal", bal), ("inv22_ak_buy", buy)):
    body = json.dumps({"section": sec, "source": "anescom", "replace": True, "rows": rows_}, ensure_ascii=False).encode("utf-8")
    rq = urllib.request.Request("https://edo.anescom.kz/api/analytics/audit", data=body, method="POST", headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok})
    try: print(sec, urllib.request.urlopen(rq, timeout=60).read().decode()[:100])
    except Exception as e: print(sec, "ОШИБКА:", str(e)[:150])
print("ГОТОВО inv22Film")
