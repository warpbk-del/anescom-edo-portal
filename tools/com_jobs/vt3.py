# 21-31 (ANESCOM_FIX): очистить ссылки и удалить подразделения «Витраж» и «Участок покраски Автокомп». DRY=True по умолчанию.
import collections
X = ib.XMLСтрока; DRY = globals().get('DRY', True)
TP = ib.NewObject('ОписаниеТипов', 'СправочникСсылка.СтруктураПредприятия').Типы().Получить(0)
EMPTY = ib.Справочники.СтруктураПредприятия.ПустаяСсылка()
P = q('ВЫБРАТЬ П.Ссылка КАК С, П.Наименование КАК Н ИЗ Справочник.СтруктураПредприятия КАК П ГДЕ П.ПометкаУдаления И (П.Наименование ПОДОБНО "%Витраж%" ИЛИ П.Наименование ПОДОБНО "%покраски Автокомп%")')
SKIPMD = ('Справочник.СтруктураПредприятия', 'РегистрСведений.ВерсииОбъектов')
ST = collections.Counter()
def obj_fields(md):
    hdr = [md.Реквизиты.Получить(j).Имя for j in range(md.Реквизиты.Количество()) if md.Реквизиты.Получить(j).Тип.СодержитТип(TP)]
    tcs = []
    for j in range(md.ТабличныеЧасти.Количество()):
        tc = md.ТабличныеЧасти.Получить(j)
        cols = [tc.Реквизиты.Получить(k).Имя for k in range(tc.Реквизиты.Количество()) if tc.Реквизиты.Получить(k).Тип.СодержитТип(TP)]
        if cols: tcs.append((tc.Имя, cols))
    return hdr, tcs
for p in P:
    pr = p['С']; xp = X(pr); print('=== ', p['Н'])
    # 1) АУН: записи и ключи аналитики (только у Витража есть)
    aun = q('ВЫБРАТЬ А.Номенклатура КАК Н, А.Характеристика КАК Х, А.Серия КАК С, А.Склад КАК Ск, А.Назначение КАК Нз, А.СтатьяКалькуляции КАК Ст, А.КлючАналитики КАК К ИЗ РегистрСведений.АналитикаУчетаНоменклатуры КАК А ГДЕ А.Склад = &П', П=pr)
    print(' АУН записей', len(aun))
    if not DRY:
        for r in aun:
            ns = ib.РегистрыСведений.АналитикаУчетаНоменклатуры.СоздатьНаборЗаписей()
            for f, k in (('Номенклатура', 'Н'), ('Характеристика', 'Х'), ('Серия', 'С'), ('Склад', 'Ск'), ('Назначение', 'Нз'), ('СтатьяКалькуляции', 'Ст')):
                getattr(ns.Отбор, f).Установить(r[k])
            ns.ОбменДанными.Загрузка = True; ns.Записать(); ST['aun_del'] += 1
            ko = r['К'].ПолучитьОбъект()
            if ko is not None:
                ko.ОбменДанными.Загрузка = True; ko.Удалить(); ST['key_del'] += 1
    # 2) прочие ссылки
    a = ib.NewObject('Массив'); a.Добавить(pr); T = ib.НайтиПоСсылкам(a)
    done = set()
    for i in range(T.Количество()):
        r = T.Получить(i); md = r.Метаданные; fn = md.ПолноеИмя()
        if fn in SKIPMD or fn == 'РегистрСведений.АналитикаУчетаНоменклатуры': continue
        if fn.startswith('Справочник.') or fn.startswith('Документ.'):
            k = X(r.Данные)
            if k in done: continue
            done.add(k)
            if fn == 'Справочник.КлючиРеестраДокументов':
                b = ib.NewObject('Массив'); b.Добавить(r.Данные); TT = ib.НайтиПоСсылкам(b)
                lft = [TT.Получить(j).Метаданные.ПолноеИмя() for j in range(TT.Количество())]
                lft = [m for m in lft if m not in ('Справочник.КлючиРеестраДокументов', 'РегистрСведений.ВерсииОбъектов')]
                print(' KEY', ib.String(r.Данные)[:40], '| ссылок на ключ', len(lft), '→', 'удалить' if not lft else 'очистить')
                if not lft:
                    if not DRY:
                        ko = r.Данные.ПолучитьОбъект(); ko.ОбменДанными.Загрузка = True; ko.Удалить()
                    ST['rkey_del'] += 1; continue
            hdr, tcs = obj_fields(md); ob = r.Данные.ПолучитьОбъект(); ch = []
            for h in hdr:
                if X(getattr(ob, h)) == xp: setattr(ob, h, EMPTY); ch.append(h)
            for tn, cols in tcs:
                tab = getattr(ob, tn); dl = []
                for row in tab:
                    for c in cols:
                        if X(getattr(row, c)) == xp:
                            if tn == 'ПолитикиУчетаСерий': dl.append(row); ch.append('удалить строку ' + tn)
                            else: setattr(row, c, EMPTY); ch.append(tn + '.' + c)
                for row in dl: tab.Удалить(row)
            print(' OBJ', fn, ib.String(r.Данные)[:40], '| очистить', ch)
            if ch and not DRY:
                ob.ОбменДанными.Загрузка = True; ob.Записать()
            ST['obj'] += 1
        elif fn.startswith('РегистрСведений.'):
            if fn in done: continue
            done.add(fn)
            dims = [md.Измерения.Получить(j).Имя for j in range(md.Измерения.Количество()) if md.Измерения.Получить(j).Тип.СодержитТип(TP)]
            nm = fn.split('.', 1)[1]
            print(' RS', fn, '| измерения-подразделения', dims)
            for d in dims:
                ns = getattr(ib.РегистрыСведений, nm).СоздатьНаборЗаписей()
                getattr(ns.Отбор, d).Установить(pr); ns.Прочитать()
                print('   записей с', d, '=', ns.Количество())
                if ns.Количество() and not DRY:
                    ns.Очистить(); ns.ОбменДанными.Загрузка = True; ns.Записать(); ST['rs_del'] += 1
            if not dims: print('   ! подразделение не в измерении — пропуск'); ST['skip'] += 1
        else:
            print(' ? ', fn); ST['skip'] += 1
    # 3) удалить подразделение, если ссылок не осталось
    if not DRY:
        T = ib.НайтиПоСсылкам(a)
        left = [T.Получить(i).Метаданные.ПолноеИмя() for i in range(T.Количество())]
        left = [m for m in left if m not in SKIPMD]
        if left:
            print(' ОСТАЛИСЬ ссылки', collections.Counter(left))
        else:
            po = pr.ПолучитьОбъект(); po.ОбменДанными.Загрузка = True; po.Удалить(); ST['podr_del'] += 1
            print(' УДАЛЕНО подразделение', p['Н'])
print('DRY' if DRY else 'WRITE', dict(ST))
if not DRY: log(f'21-31 vt3 Витраж/Участок покраски: {dict(ST)}')
