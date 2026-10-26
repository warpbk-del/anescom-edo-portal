# 21-31 (только чтение): ссылки на подразделения «Витраж» и «Участок покраски Автокомп» (ANESCOM_FIX).
import collections, csv
P = q('ВЫБРАТЬ П.Ссылка КАК С, П.Наименование КАК Н, П.ПометкаУдаления КАК Пм ИЗ Справочник.СтруктураПредприятия КАК П ГДЕ П.Наименование ПОДОБНО "%Витраж%" ИЛИ П.Наименование ПОДОБНО "%покраски Автокомп%"')
for p in P: print('P', p['Н'], '| пометка', p['Пм'])
md = ib.Метаданные.РегистрыСведений.АналитикаУчетаНоменклатуры
dims = [md.Измерения.Получить(i).Имя for i in range(md.Измерения.Количество())]
ress = [md.Ресурсы.Получить(i).Имя for i in range(md.Ресурсы.Количество())]
print('АУН измерения', dims, '| ресурсы', ress)
for p in P:
    a = ib.NewObject('Массив'); a.Добавить(p['С']); T = ib.НайтиПоСсылкам(a)
    c = collections.Counter(T.Получить(i).Метаданные.ПолноеИмя() for i in range(T.Количество()))
    print('REFS', p['Н'], dict(c))
    # какие поля АУН ссылаются на подразделение
    fld = [f for f in dims + ress if md.Измерения.Найти(f) is not None and md.Измерения.Найти(f).Тип.СодержитТип(ib.NewObject('ОписаниеТипов', 'СправочникСсылка.СтруктураПредприятия').Типы().Получить(0))
           or md.Ресурсы.Найти(f) is not None and md.Ресурсы.Найти(f).Тип.СодержитТип(ib.NewObject('ОписаниеТипов', 'СправочникСсылка.СтруктураПредприятия').Типы().Получить(0))]
    if not fld: continue
    cond = ' ИЛИ '.join(f'А.{f} = &П' for f in fld)
    rows = q('ВЫБРАТЬ ' + ', '.join(f'А.{f} КАК {f}' for f in dims + ress) + ' ИЗ РегистрСведений.АналитикаУчетаНоменклатуры КАК А ГДЕ ' + cond, П=p['С'])
    print(' АУН записей', len(rows), 'поля-ссылки', fld)
    # используется ли ключ аналитики в движениях (остатки себестоимости/товаров)
    out = r'D:\anescom_edo\data\reports\podr_AUN_' + str(P.index(p)) + '.csv'
    with open(out, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh, delimiter=';'); w.writerow(dims + ress)
        for r in rows: w.writerow([s(r[f]) for f in dims + ress])
    print(' CSV', out)
    byn = collections.Counter((s(r.get('Номенклатура'))[:40], s(r.get('Склад', r.get('МестоХранения')))[:25]) for r in rows)
    for (n, sk), k in byn.most_common(80): print(f'  {k:2d} | {n} | {sk}')
