# 22-И (чтение, копия ANESCOM) v2: оприходования по ТАБЛИЧНОЙ ЧАСТИ документов (бухрегистр 2026/филиалы неполон): для комплектующих, списанных в АВТОКОМП 08.09.2026 и найденных излишками у филиалов,
# строки «Оприходования излишков» 01.01.2025–30.09.2026 (Дт13xx) по кандидатам номенклатуры + последние цены приобретения у АВТОКОМП.
# Результат: POST /api/analytics/audit разделы inv22_surp, inv22_price, inv22_cand (портал, только админ) + CSV D:\\anescom_edo\\data\\reports\\22.
import re, os, json, csv, datetime, urllib.request
ITEMS = [["Винт BC 4,2х13 DIN 7981 ТАТПРОФ", 1000], ["Винт BC 5,5х19 DIN 7976 А2 TATPROF", 5], ["Винт BC 5,5х38 DIN 7976 А2 TATPROF", 31], ["Винт BC 5,5х50 DIN 7976 А2 TATPROF", 4], ["Держатель щеточного уплотнителя МП-45.07.02 ТАТПРОФ (7024МАТ) 6м", 48], ["Дренажная вставка F50.13.01 TATPROF", 50], ["Закладная ригельная F50.08.50 L=124 мм к F50.02.12 TATPROF", 28], ["Закладная ригельная F50.08.50 L=84,2 мм к F50.02.07 TATPROF", 76], ["Закладная стойки F50.08.06 к F50.01.06, F50.01.22 TATPROF 6м", 6], ["Крышка стоечная ригельная МП-5014МО ТАТПРОФ (8017) 6м", 2], ["Ответки для многозапорных замков БПК 3045.50.220", 10], ["Подставка под заполнение W72.13.01 TATPROF", 922], ["Подставка под стеклопакет F50.05.02 TATPROF 6м", 2], ["Рама двери открывание наружу МП-65.02.01 ТАТПРОФ (7024) 6,5м", 5], ["Рама окна W65.01.04 TATPROF (8017) 6м", 19], ["Ручка дверная труба-овал 950мм СТН-1565.950.60 (7024МАТ) САТУРН", 12], ["Створка двери открывание наружу D65.02.02 TATPROF (7024МАТ) 6,5м", 4], ["Створка двери открывание наружу МП-45.02.03 ТАТПРОФ (8017) 6м", 9], ["Стойка ригель 106мм МП-5006 ТАТПРОФ (8017) 6м", 2], ["Стойка ригель S 105мм F50.01.22 TATPROF (7024МАТ) 6,8м", 4], ["Стойка ригель S 54,8мм F50.01.20 TATPROF (7024МАТ) 6,8м", 2], ["Термовставка F50.12.03 TATPROF 3м", 50], ["Уголок 40*15 МП-115 (8017) ТАТПРОФ 6м", 1], ["Уголок выравнивающий W45.16.04 TATPROF", 37], ["Уголок стальной D45.14.01 TATPROF", 96], ["Уплотнитель F50.10.08 125м TATPROF", 330], ["Уплотнитель F50.10.11, EPDM 300м TATPROF", 600], ["Уплотнитель притвора ТПУ-45.02,500м (аналог W45.10.02)", 2500], ["Уплотнитель ригельный ТПУ -6009 (F50.10.14) 75м", 275], ["Уплотнитель стеклопакета ТПУ-301, 150м (аналог 50.10.07)", 750], ["Уплотнитель стеклопакета ТПУ-45.01,300м (аналог W45.10.01)", 950], ["Уплотнитель стоечный F50.10.02, EPDM 400м TATPROF", 400], ["Уплотнитель стоечный ТПУ-6002, 150м (аналог F50.10.10)", 900], ["Уплотнитель ТПУ-6008, 75м (аналог F50.10.12)", 700], ["Штапик W65(32),W45(12) W45.04.05 TATPROF (7024МАТ) 6м", 42], ["Штапик W65(44),W45(24) W45.04.02 TATPROF (7021МАТ) 6м", 38], ["Штапик МП65(24),МП45(4) МП-45.10.02 ТАТПРОФ (7024) 6м", 20], ["Штифт нагель 5х13,5 TATPROF", 2071]]
N, K = datetime.datetime(2025, 1, 1), datetime.datetime(2026, 9, 30, 23, 59, 59)
OUT = r"D:\anescom_edo\data\reports\22"; os.makedirs(OUT, exist_ok=True)
COL = r"(7024\s?МАТ|7024\s?мат|7021\s?МАТ|8017|9016|7016|9005|9006|7024)"
def codes(n):
    c = re.findall(r"(?:[A-ZА-Я]{1,2}\d{2}\.\d{2}\.\d{2}|МП-\d{2,3}\.\d{2}\.\d{2}|МП-\d{3,4}[А-ЯA-Z]*|ТПУ\s?-\s?\d{2,4}(?:\.\d{2})?|СТН-[\d.\-]+[А-ЯA-Z]?|\d{4}\.\d{2}\.\d{3}|\d,\dх\d{2})", n)
    return [re.sub(r"\s", "", x) for x in c]
def color(n):
    m = re.search(COL, n); return re.sub(r"\s", "", m.group(1)).upper()[:4] if m else None
def norm(t): return re.sub(r"[^0-9A-ZА-Я]+", "", (t or "").upper().replace("Ё", "Е"))
cand_rows, refs_all = [], []
for i, (name, qty) in enumerate(ITEMS):
    cs, col = codes(name), color(name)
    if cs:
        pats = [cs[0]] + ([cs[1]] if cs[0].startswith("ТПУ") and len(cs) > 1 else [])
        din = re.search(r"DIN\s?(\d{3,4})", name)
        cand, seen = [], set()
        for pt in pats:
            for r in q("ВЫБРАТЬ Н.Ссылка КАК С, Н.Наименование КАК Н ИЗ Справочник.Номенклатура КАК Н ГДЕ НЕ Н.ЭтоГруппа И НЕ Н.ПометкаУдаления И Н.Наименование ПОДОБНО &П", П="%" + pt.replace("ТПУ-", "ТПУ%") + "%"):
                nn = s(r["Н"])
                if nn in seen or (col and col not in norm(nn)) or (din and din.group(1) not in nn) or nn.upper().startswith(("АК-", "AK-")): continue
                seen.add(nn); cand.append(r)
    else:
        w = " ".join(name.split()[:3])
        cand = q("ВЫБРАТЬ Н.Ссылка КАК С, Н.Наименование КАК Н ИЗ Справочник.Номенклатура КАК Н ГДЕ НЕ Н.ЭтоГруппа И НЕ Н.ПометкаУдаления И Н.Наименование ПОДОБНО &П", П=w + "%")
    for r in cand:
        cand_rows.append({"i": i, "item": name, "qty_av": qty, "nom": s(r["Н"])}); refs_all.append((i, r["С"]))
print("кандидатов:", len(cand_rows), "по", len({r["i"] for r in cand_rows}), "из", len(ITEMS))
arr = ib.NewObject("Массив"); idx = {}
for i, ref in refs_all:
    arr.Добавить(ref); idx.setdefault(s(ref), []).append(i)
TXT = """ВЫБРАТЬ Т.Ссылка КАК Р, Т.Ссылка.Дата КАК Д, Т.Ссылка.Организация КАК О, Т.Ссылка.Склад КАК Ск, Т.Ссылка.Проведен КАК Пр, Т.НомерСтроки КАК НС,
  Т.Номенклатура КАК Н, Т.Количество КАК Кол, {SUM}
ИЗ Документ.ОприходованиеИзлишковТоваров.Товары КАК Т ГДЕ Т.Ссылка.Дата МЕЖДУ &Н И &К И НЕ Т.Ссылка.ПометкаУдаления И Т.Номенклатура В (&М)"""
try:
    rows = q(TXT.replace("{SUM}", "Т.Сумма КАК Сум"), Н=N, К=K, М=arr)
except Exception as e:
    print("без Сумма:", str(e)[-100:]); rows = q(TXT.replace("{SUM}", "Т.Цена * Т.Количество КАК Сум"), Н=N, К=K, М=arr)
surp = []
for r in rows:
    nm = s(r["Н"])
    for i in idx.get(nm, [-1]):
        surp.append({"i": i, "nom": nm, "date": str(r["Д"])[:10], "doc": s(r["Р"]), "org": s(r["О"]), "sklad": s(r["Ск"]), "posted": bool(r["Пр"]),
                     "line": int(r["НС"]), "qty": float(r["Кол"] or 0), "sum": round(float(r["Сум"] or 0), 2)})
print("строк оприходований (ТЧ):", len(surp), "на", round(sum(x["sum"] for x in surp) / 1e6, 2), "млн; проведено", sum(x["posted"] for x in surp))
# все документы оприходования за период (контроль)
for r in q("""ВЫБРАТЬ Д.Ссылка КАК Р, Д.Организация КАК О, Д.Склад КАК Ск, Д.Проведен КАК Пр ИЗ Документ.ОприходованиеИзлишковТоваров КАК Д
    ГДЕ Д.Дата МЕЖДУ &Н И &К И НЕ Д.ПометкаУдаления УПОРЯДОЧИТЬ ПО Д.Дата""", Н=N, К=K):
    print(" ", s(r["Р"])[:62], "|", s(r["Ск"])[:28], "|", "пров" if r["Пр"] else "НЕ пров")
tok = ""
for l in open(r"D:\anescom_edo\config.env", encoding="utf-8-sig"):
    if l.strip().startswith("EDO_API_TOKEN="): tok = l.split("=", 1)[1].strip().strip('"')
for sec, rows_ in (("inv22_surp", surp),):
    body = json.dumps({"section": sec, "source": "anescom", "replace": True, "rows": rows_, "date_from": "2025-01-01", "date_to": "2026-09-30"}, ensure_ascii=False).encode("utf-8")
    rq = urllib.request.Request("https://edo.anescom.kz/api/analytics/audit", data=body, method="POST",
                                headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok})
    try: print(sec, urllib.request.urlopen(rq, timeout=60).read().decode()[:120])
    except Exception as e: print(sec, "ОШИБКА отправки:", str(e)[:150])
print("ГОТОВО inv22Docs")
