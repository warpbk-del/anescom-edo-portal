# 21-29c: построчная сверка 1030/2209 (ANESCOM_FIX) с выпиской 01.04–25.10.2026 (только чтение).
import collections
ST = zlib.decompress(base64.b64decode(_ST)).decode().split(",")
BK = collections.defaultdict(list)
for i, x in enumerate(ST):
    key = (x[:4], x[4], int(x[5:])); BK[key].append(i)
z = ib.NewObject("Запрос")
z.Текст = ("ВЫБРАТЬ Т.Период КАК П, Т.Регистратор КАК Р, Т.СчетДт.Код КАК СД, Т.СчетКт.Код КАК СК, Т.СубконтоДт1 КАК ДС, Т.СубконтоКт1 КАК КС, Т.Сумма КАК С "
           "ИЗ РегистрБухгалтерии.%s.ДвиженияССубконто(&Н, &К, , , ) КАК Т ГДЕ Т.СчетДт.Код = \"1030\" ИЛИ Т.СчетКт.Код = \"1030\"" % REG)
z.УстановитьПараметр("Н", datetime.datetime(2026, 4, 1, 5)); z.УстановитьПараметр("К", datetime.datetime(2026, 10, 26, 4, 59, 59))
sel = z.Выполнить().Выбрать(); C1 = []
while sel.Следующий():
    p = sel.П; dm = p.strftime("%d%m")
    if sel.СД.strip() == "1030" and "2209" in ib.String(sel.ДС) and "(KZT)" not in ib.String(sel.ДС): C1.append((dm, "+", round((sel.С or 0) * 100), sel.Р, p))
    if sel.СК.strip() == "1030" and "2209" in ib.String(sel.КС) and "(KZT)" not in ib.String(sel.КС): C1.append((dm, "-", round((sel.С or 0) * 100), sel.Р, p))
used = set(); un1 = []
for dm, sg, a, r, p in C1:
    lst = BK.get((dm, sg, a), [])
    j = next((i for i in lst if i not in used), None)
    if j is None: un1.append((dm, sg, a, r, p))
    else: used.add(j)
unb = [i for i in range(len(ST)) if i not in used]
print(f"1С строк {len(C1)}, выписка {len(ST)}; совпало {len(used)}; нет в выписке (1С) {len(un1)} на +{sum(a for d,s,a,*_ in un1 if s=='+')/100:,.2f} / -{sum(a for d,s,a,*_ in un1 if s=='-')/100:,.2f}; "
      f"нет в 1С (банк) {len(unb)} на +{sum(int(ST[i][5:]) for i in unb if ST[i][4]=='+')/100:,.2f} / -{sum(int(ST[i][5:]) for i in unb if ST[i][4]=='-')/100:,.2f}")
print("== в 1С, нет в выписке (крупные):")
for dm, sg, a, r, p in sorted(un1, key=lambda x: -x[2])[:25]:
    print(f"  {p.strftime('%d.%m')} {sg}{a/100:>15,.2f} {ib.String(r)[-55:]}")
print("== в выписке, нет в 1С (индексы, крупные):", " ".join(f"{i}:{ST[i][4]}{int(ST[i][5:])/100:,.0f}" for i in sorted(unb, key=lambda i: -int(ST[i][5:]))[:40]))
UNB = unb; UN1 = un1
