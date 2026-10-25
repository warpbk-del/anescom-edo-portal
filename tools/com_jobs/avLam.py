# 22-Д (чтение, AVTOKOMP_FIX): ламинация/покраска для ANESCOM в АВТОКОМП 2025–2026.
# 1) обороты ТоварыНаСкладах по группам товаров (АК-, сырьё ламинации/покраски, белый ПВХ-профиль) × вид документа × месяц;
# 2) реализации ANESCOM: товары «АК-»/услуги/прочее × месяц (кол-во, сумма); 3) приобретения у ANESCOM × группа × месяц; 4) остатки групп сейчас.
# Результат: POST портал раздел av_lam_* (source=avtokomp).
import json, datetime, urllib.request, re
N, K = datetime.datetime(2025, 1, 1), datetime.datetime(2026, 12, 31, 23, 59, 59)
def grp(n):
    u = n.upper()
    if u.startswith(("АК-", "AK-")): return "АК"
    if re.search(r"ПЛЕНКА|ПЛЁНКА|KLEIBERIT|КЛЕЙ|ПРАЙМЕР|ОЧИСТИТЕЛ|ПОРОШК|КРАСК|ГРУНТ|RAL\b", u): return "сырьё_лам_покр"
    if re.search(r"HELIOS|BAULINE|STANDART|PROPLEX|ШТАПИК|ИМПОСТ|РАМА|СТВОРКА", u): return "ПВХ_профиль" if not re.search(r"TATPROF|ТАТПРОФ|МП-|F50|W45|W65|D45|D65", u) else "алюм_профиль"
    return "прочее"
def push(sec, rows):
    tok = ""
    for l in open(r"D:\anescom_edo\config.env", encoding="utf-8-sig"):
        if l.strip().startswith("EDO_API_TOKEN="): tok = l.split("=", 1)[1].strip().strip('"')
    body = json.dumps({"section": sec, "source": "avtokomp", "replace": True, "rows": rows}, ensure_ascii=False).encode("utf-8")
    rq = urllib.request.Request("https://edo.anescom.kz/api/analytics/audit", data=body, method="POST", headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok})
    try: print(sec, len(rows), urllib.request.urlopen(rq, timeout=90).read().decode()[:60])
    except Exception as e: print(sec, "ОШИБКА:", str(e)[:120])
mov = {}
for r in q("""ВЫБРАТЬ Т.Номенклатура.Наименование КАК Н, ТИПЗНАЧЕНИЯ(Т.Регистратор) КАК Т, НАЧАЛОПЕРИОДА(Т.Период, МЕСЯЦ) КАК М,
  СУММА(Т.ВНаличииПриход) КАК П, СУММА(Т.ВНаличииРасход) КАК Р
 ИЗ РегистрНакопления.ТоварыНаСкладах.ОстаткиИОбороты(&Н, &К, Регистратор, , ) КАК Т
 СГРУППИРОВАТЬ ПО Т.Номенклатура.Наименование, ТИПЗНАЧЕНИЯ(Т.Регистратор), НАЧАЛОПЕРИОДА(Т.Период, МЕСЯЦ)""", Н=N, К=K):
    g = grp(s(r["Н"]))
    if g == "прочее": continue
    k = (g, s(r["Т"]), str(r["М"])[:7]); a = mov.setdefault(k, [0.0, 0.0]); a[0] += float(r["П"] or 0); a[1] += float(r["Р"] or 0)
push("av_lam_mov", [{"g": k[0], "t": k[1], "m": k[2], "in": round(v[0], 3), "out": round(v[1], 3)} for k, v in mov.items()])
sal = {}
for r in q("""ВЫБРАТЬ Т.Номенклатура.Наименование КАК Н, Т.Номенклатура.ТипНоменклатуры КАК ТН, НАЧАЛОПЕРИОДА(Т.Ссылка.Дата, МЕСЯЦ) КАК М,
  СУММА(Т.Количество) КАК Кол, СУММА(Т.Сумма) КАК Сум, СУММА(Т.СуммаНДС) КАК НДС
 ИЗ Документ.РеализацияТоваровУслуг.Товары КАК Т ГДЕ Т.Ссылка.Проведен И Т.Ссылка.Дата МЕЖДУ &Н И &К И Т.Ссылка.Контрагент.Наименование ПОДОБНО "%ANESCOM%"
 СГРУППИРОВАТЬ ПО Т.Номенклатура.Наименование, Т.Номенклатура.ТипНоменклатуры, НАЧАЛОПЕРИОДА(Т.Ссылка.Дата, МЕСЯЦ)""", Н=N, К=K):
    n = s(r["Н"]); tn = s(r["ТН"]); g = "услуга" if "слуг" in tn or "абот" in tn else grp(n)
    k = (g, str(r["М"])[:7], n if g == "услуга" else ""); a = sal.setdefault(k, [0.0, 0.0, 0.0])
    a[0] += float(r["Кол"] or 0); a[1] += float(r["Сум"] or 0); a[2] += float(r["НДС"] or 0)
push("av_lam_sales", [{"g": k[0], "m": k[1], "srv": k[2], "qty": round(v[0], 3), "sum": round(v[1], 2), "vat": round(v[2], 2)} for k, v in sal.items()])
buy = {}
for r in q("""ВЫБРАТЬ Т.Номенклатура.Наименование КАК Н, НАЧАЛОПЕРИОДА(Т.Ссылка.Дата, МЕСЯЦ) КАК М, СУММА(Т.Количество) КАК Кол, СУММА(Т.Сумма) КАК Сум
 ИЗ Документ.ПриобретениеТоваровУслуг.Товары КАК Т ГДЕ Т.Ссылка.Проведен И Т.Ссылка.Дата МЕЖДУ &Н И &К И Т.Ссылка.Контрагент.Наименование ПОДОБНО "%ANESCOM%"
 СГРУППИРОВАТЬ ПО Т.Номенклатура.Наименование, НАЧАЛОПЕРИОДА(Т.Ссылка.Дата, МЕСЯЦ)""", Н=N, К=K):
    k = (grp(s(r["Н"])), str(r["М"])[:7]); a = buy.setdefault(k, [0.0, 0.0]); a[0] += float(r["Кол"] or 0); a[1] += float(r["Сум"] or 0)
push("av_lam_buy", [{"g": k[0], "m": k[1], "qty": round(v[0], 3), "sum": round(v[1], 2)} for k, v in buy.items()])
bal = {}
for r in q("ВЫБРАТЬ Т.Номенклатура.Наименование КАК Н, Т.Склад КАК С, Т.ВНаличииОстаток КАК О ИЗ РегистрНакопления.ТоварыНаСкладах.Остатки(, ) КАК Т"):
    g = grp(s(r["Н"]))
    if g == "прочее": continue
    k = (g, s(r["С"])); bal[k] = bal.get(k, 0.0) + float(r["О"] or 0)
push("av_lam_bal", [{"g": k[0], "sk": k[1], "qty": round(v, 3)} for k, v in bal.items()])
print("ГОТОВО avLam")
