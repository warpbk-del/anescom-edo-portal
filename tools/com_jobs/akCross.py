# 22-Д (чтение): продажи «АК-» АВТОКОМП → ANESCOM 07–10.2026 и как они оприходованы в ANESCOM (копия KA2026).
import json, datetime, urllib.request
N, K = datetime.datetime(2026, 7, 1), datetime.datetime(2026, 10, 31, 23, 59, 59)
AV, AN = IB_POOL[r"D:\Base\1C\AVTOKOMP_FIX"], IB_POOL[r"D:\Base\1C\KA2026"]
def qq(base, text, **p):
    z = base[0].NewObject("Запрос"); z.Текст = text
    for k, v in p.items(): z.УстановитьПараметр(k, v)
    res = z.Выполнить(); cols = [res.Колонки.Получить(i).Имя for i in range(res.Колонки.Количество())]; out, sel = [], res.Выбрать()
    while sel.Следующий(): out.append({c: getattr(sel, c) for c in cols})
    return out
ss = lambda base, v: base[0].String(v)
rows = []
for r in qq(AV, """ВЫБРАТЬ Т.Ссылка.Номер КАК Ном, Т.Ссылка.Дата КАК Д, Т.Номенклатура.Наименование КАК Н, Т.Количество КАК Кол, Т.Сумма КАК Сум, Т.СуммаНДС КАК НДС
  ИЗ Документ.РеализацияТоваровУслуг.Товары КАК Т ГДЕ Т.Ссылка.Проведен И Т.Ссылка.Дата МЕЖДУ &Н И &К И Т.Ссылка.Контрагент.Наименование ПОДОБНО "%ANESCOM%"
  И (Т.Номенклатура.Наименование ПОДОБНО "АК-%" ИЛИ Т.Номенклатура.Наименование ПОДОБНО "AK-%")""", Н=N, К=K):
    rows.append({"side": "AV", "num": ss(AV, r["Ном"]), "d": str(r["Д"])[:10], "n": ss(AV, r["Н"]), "q": float(r["Кол"] or 0), "sum": float(r["Сум"] or 0), "vat": float(r["НДС"] or 0)})
for r in qq(AN, """ВЫБРАТЬ Т.Ссылка.Номер КАК Ном, Т.Ссылка.Дата КАК Д, Т.Ссылка.НомерВходящегоДокумента КАК Вх, Т.Номенклатура.Наименование КАК Н, Т.Количество КАК Кол, Т.Сумма КАК Сум
  ИЗ Документ.ПриобретениеТоваровУслуг.Товары КАК Т ГДЕ Т.Ссылка.Проведен И Т.Ссылка.Дата МЕЖДУ &Н И &К И Т.Ссылка.Контрагент.Наименование ПОДОБНО "%АВТОКОМП%" """, Н=N, К=K):
    rows.append({"side": "AN", "num": ss(AN, r["Ном"]), "vh": ss(AN, r["Вх"]), "d": str(r["Д"])[:10], "n": ss(AN, r["Н"]), "q": float(r["Кол"] or 0), "sum": float(r["Сум"] or 0)})
print("строк", len(rows), "AV", sum(1 for r in rows if r["side"] == "AV"), "AN", sum(1 for r in rows if r["side"] == "AN"))
tok = ""
for l in open(r"D:\anescom_edo\config.env", encoding="utf-8-sig"):
    if l.strip().startswith("EDO_API_TOKEN="): tok = l.split("=", 1)[1].strip().strip('"')
body = json.dumps({"section": "ak_cross", "source": "avtokomp", "replace": True, "rows": rows}, ensure_ascii=False).encode("utf-8")
rq = urllib.request.Request("https://edo.anescom.kz/api/analytics/audit", data=body, method="POST", headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok})
print(urllib.request.urlopen(rq, timeout=90).read().decode()[:60]); print("ГОТОВО akCross")
