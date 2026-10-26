# 21-31 доделка замены дубля счёта 2209 → «2209 в АО "Народный Банк Казахстана" KZT» (ANESCOM_FIX) — быстрый способ.
# Меняем только реквизиты/строки ТЧ типа БанковскиеСчетаОрганизаций, равные OLD; запись ОбменДанными.Загрузка=Истина
# (без проведения и обработчиков; движения регистров счёт не содержат — по НайтиПоСсылкам только документы и 2 РС).
# Параметры: DRY (по умолчанию True), LIMIT (по умолчанию 50 объектов), STEP (печать прогресса).
import time, collections
DRY = globals().get('DRY', True); LIMIT = globals().get('LIMIT', 50); STEP = globals().get('STEP', 200)
X = ib.XMLСтрока
BS = q('ВЫБРАТЬ Т.Ссылка КАК Сс, Т.Наименование КАК Нм, Т.ПометкаУдаления КАК Пм ИЗ Справочник.БанковскиеСчетаОрганизаций КАК Т ГДЕ Т.Владелец.Префикс <> "GT" И Т.Наименование ПОДОБНО "2209 в АО%"')
OLD = [x['Сс'] for x in BS if x['Пм']][0]; NEW = [x['Сс'] for x in BS if not x['Пм'] and x['Нм'].strip().endswith('KZT')][0]
assert X(OLD.Владелец) == X(NEW.Владелец) and OLD.НомерСчета == NEW.НомерСчета, 'владелец/номер не совпадают'
XO = X(OLD); TBS = ib.ТипЗнч(OLD)
def B1030():
    return q('ВЫБРАТЬ СУММА(О.СуммаОстаток) КАК См ИЗ РегистрБухгалтерии.Хозрасчетный.Остатки(, Счет.Код ПОДОБНО "1030%", , Организация.Префикс <> "GT") КАК О')[0]['См']
def BDS(ref):
    return q('ВЫБРАТЬ СУММА(О.СуммаОстаток) КАК См ИЗ РегистрНакопления.ДенежныеСредстваБезналичные.Остатки(, БанковскийСчет=&Б) КАК О', Б=ref)[0]['См']
t0 = time.time()
a = ib.NewObject('Массив'); a.Добавить(OLD); T = ib.НайтиПоСсылкам(a)
docs = []; other = collections.Counter()
for i in range(T.Количество()):
    r = T.Получить(i); fn = r.Метаданные.ПолноеИмя()
    if fn.startswith('Документ.') or (fn.startswith('Справочник.') and fn != 'Справочник.БанковскиеСчетаОрганизаций'):
        docs.append((fn, r.Данные))
    else:
        other[fn] += 1
print('FOUND', len(docs), 'объектов;', 'прочее', dict(other), int(time.time() - t0), 's')
print('BEFORE 1030', B1030(), '| DS old', BDS(OLD), '| DS new', BDS(NEW))
# поля по типам (кеш метаданных)
FIELDS = {}
def fields(fn):
    if fn in FIELDS: return FIELDS[fn]
    md = ib.Метаданные.НайтиПоПолномуИмени(fn); hdr = []; tcs = []
    for j in range(md.Реквизиты.Количество()):
        at = md.Реквизиты.Получить(j)
        if at.Тип.СодержитТип(TBS): hdr.append(at.Имя)
    for j in range(md.ТабличныеЧасти.Количество()):
        tc = md.ТабличныеЧасти.Получить(j); cols = []
        for k in range(tc.Реквизиты.Количество()):
            at = tc.Реквизиты.Получить(k)
            if at.Тип.СодержитТип(TBS): cols.append(at.Имя)
        if cols: tcs.append((tc.Имя, cols))
    FIELDS[fn] = (hdr, tcs); print('FIELDS', fn, hdr, tcs); return FIELDS[fn]
done = err = nochg = 0; errs = []; seen = set(); t1 = time.time()
for fn, ref in docs:
    if done + err + nochg >= LIMIT: break
    k = X(ref)
    if k in seen: continue
    seen.add(k)
    hdr, tcs = fields(fn); ch = []
    try:
        ob = ref.ПолучитьОбъект()
        for h in hdr:
            if X(getattr(ob, h)) == XO: setattr(ob, h, NEW); ch.append(h)
        for tn, cols in tcs:
            for row in getattr(ob, tn):
                for c in cols:
                    if X(getattr(row, c)) == XO: setattr(row, c, NEW); ch.append(tn + '.' + c)
        if not ch:
            nochg += 1; continue
        if not DRY:
            ob.ОбменДанными.Загрузка = True; ob.Записать()
        done += 1
        if done <= 3 or done % STEP == 0:
            el = time.time() - t1
            print(f' {done} {fn[9:40]} {ib.String(ref)[:45]} | {sorted(set(ch))} | {done/el*60:.0f}/мин', flush=True)
    except Exception as e:
        err += 1; errs.append((ib.String(ref)[:50], str(e)[-120:]))
el = time.time() - t1
print('DRY' if DRY else 'WRITE', 'изменено', done, 'без изменений', nochg, 'ошибок', err, f'за {int(el)} с ({done/max(el,1)*60:.0f}/мин)')
for e in errs[:8]: print(' E', e)
if not DRY:
    print('AFTER 1030', B1030(), '| DS old', BDS(OLD), '| DS new', BDS(NEW))
    log(f'21-31 bs3 счёт 2209: заменено в {done} объектах, ошибок {err} (LIMIT {LIMIT})')
