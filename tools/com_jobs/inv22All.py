# 22-И (чтение, копия ANESCOM): ВСЕ строки «Оприходования излишков» 01.01.2025–30.09.2026 (ТЧ) с артикулом и ед. изм. — для нечёткой сверки.
import json, datetime, urllib.request
N, K = datetime.datetime(2025, 1, 1), datetime.datetime(2026, 9, 30, 23, 59, 59)
rows = q("""ВЫБРАТЬ Т.Ссылка КАК Р, Т.Ссылка.Дата КАК Д, Т.Ссылка.Склад КАК Ск, Т.НомерСтроки КАК НС, Т.Номенклатура КАК Н, Т.Номенклатура.Артикул КАК А,
  Т.Номенклатура.ЕдиницаИзмерения КАК Е, Т.Количество КАК Кол, Т.Сумма КАК Сум
ИЗ Документ.ОприходованиеИзлишковТоваров.Товары КАК Т ГДЕ Т.Ссылка.Проведен И Т.Ссылка.Дата МЕЖДУ &Н И &К""", Н=N, К=K)
out = [{"d": str(r["Д"])[:10], "doc": s(r["Р"]).replace("Оприходование излишков товаров ", "")[:11], "sk": s(r["Ск"]).strip(), "ln": int(r["НС"]),
        "n": s(r["Н"]).strip(), "a": s(r["А"]).strip(), "e": s(r["Е"]), "q": float(r["Кол"] or 0), "s": round(float(r["Сум"] or 0), 2)} for r in rows]
print("строк", len(out), "сумма млн", round(sum(x["s"] for x in out) / 1e6, 2))
tok = ""
for l in open(r"D:\anescom_edo\config.env", encoding="utf-8-sig"):
    if l.strip().startswith("EDO_API_TOKEN="): tok = l.split("=", 1)[1].strip().strip('"')
body = json.dumps({"section": "inv22_all_surp", "source": "anescom", "replace": True, "rows": out}, ensure_ascii=False).encode("utf-8")
rq = urllib.request.Request("https://edo.anescom.kz/api/analytics/audit", data=body, method="POST", headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok})
try: print(urllib.request.urlopen(rq, timeout=90).read().decode()[:100])
except Exception as e: print("ОШИБКА:", str(e)[:150])
print("ГОТОВО inv22All")
