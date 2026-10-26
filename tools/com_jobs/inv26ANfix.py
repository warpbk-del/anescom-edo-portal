# 22-В запись в ANESCOM_FIX по плану PLAN26 (из inv26AN, тот же сеанс). Каждая пара — в своей транзакции (откат при ошибке).
# 1: уменьшить строку списания и строку оприходования на t; 2: + «Перемещение товаров» (статус «Принято») со склада недостачи на склад излишка;
# 3: + «Пересортица товаров» на складе (товар недостачи → товар излишка). Дата новых документов = min(дат) − 1 мин (+5 ч сдвиг COM).
# DRY=True по умолчанию. ONLY = {'1','2','3'} — какие типы делать.
import datetime, collections
DRY = globals().get('DRY', True); ONLY = globals().get('ONLY', {'1', '2', '3'})
SHIFT = datetime.timedelta(hours=5)
MOVE_T = q("ВЫБРАТЬ ПЕРВЫЕ 1 Д.Ссылка КАК Д ИЗ Документ.ПеремещениеТоваров КАК Д ГДЕ Д.Проведен И Д.Статус = ЗНАЧЕНИЕ(Перечисление.СтатусыПеремещенийТоваров.Принято) УПОРЯДОЧИТЬ ПО Д.Дата УБЫВ")[0]['Д']
SORT_T = q("ВЫБРАТЬ ПЕРВЫЕ 1 Д.Ссылка КАК Д ИЗ Документ.ПересортицаТоваров КАК Д ГДЕ Д.Проведен УПОРЯДОЧИТЬ ПО Д.Дата УБЫВ")[0]['Д']
TAG = '[22-В 26.10.2026]'
def msgs():
    try:
        a = ib.ПолучитьСообщенияПользователю(True); return ' / '.join(a.Получить(i).Текст for i in range(a.Количество()))[-300:]
    except Exception: return ''
def reduce(ref, nm_ref, xr, t, line_no, note):
    o = ref.ПолучитьОбъект(); T = o.Товары
    row = None
    for i in range(T.Количество()):
        r = T.Получить(i)
        if r.НомерСтроки == line_no and ib.XMLСтрока(r.Номенклатура) == ib.XMLСтрока(nm_ref): row = r; break
    if row is None: raise Exception('строка не найдена ' + s(ref))
    v = float(row.Количество) - t
    if v <= 1e-4: T.Удалить(row)
    else:
        row.Количество = round(v, 3)
        if hasattr(row, 'КоличествоУпаковок'): row.КоличествоУпаковок = round(v, 3)
        try:
            if float(row.Цена or 0): row.Сумма = round(float(row.Цена) * v, 2)
        except Exception: pass
    if TAG not in (o.Комментарий or ''): o.Комментарий = ((o.Комментарий or '') + ' | ' + TAG + ' ' + note).strip(' |')
    o.Записать(ib.РежимЗаписиДокумента.Проведение)
ok = collections.Counter(); bad = []; made = []
for nm, a, b, t in PLAN26:
    typ = nm[0]
    if typ not in ONLY: continue
    oa, ob = a['ref'].Организация, b['ref'].Организация
    d = min(a['d'], b['d']); d = datetime.datetime(d.year, d.month, d.day, d.hour, d.minute) - datetime.timedelta(minutes=1)
    desc = f"{typ} {t:g} {a['n'][:34]} {a['sk'][:16]} → {(b['n'][:34] + ' ') if typ == '3' else ''}{b['sk'][:16]} {d:%d.%m.%Y %H:%M}"
    if typ == '2' and ib.XMLСтрока(oa) != ib.XMLСтрока(ob):
        bad.append((desc, 'разные организации (филиал) — пропуск')); continue
    if DRY: print('  PLAN', desc); ok[typ] += 1; continue
    ib.НачатьТранзакцию()
    try:
        newdoc = ''
        if typ == '2':
            m = MOVE_T.ПолучитьОбъект().Скопировать(); m.Дата = d + SHIFT; m.Организация = oa
            m.СкладОтправитель = a['skr']; m.СкладПолучатель = b['skr']; m.Статус = ib.Перечисления.СтатусыПеремещенийТоваров.Принято
            for tc in ('Товары', 'ВидыЗапасов', 'Серии'):
                try: getattr(m, tc).Очистить()
                except Exception: pass
            try: m.ЗаказНаПеремещение = None
            except Exception: pass
            r = m.Товары.Добавить(); r.Номенклатура = a['nr']; r.Характеристика = a['xr']; r.Количество = round(t, 3); r.КоличествоУпаковок = round(t, 3)
            m.Комментарий = f"{TAG} списано недостачей на {a['sk']} ({a['doc'][:45]}), оприходовано излишком на {b['sk']} ({b['doc'][:45]}) — оформлено перемещением"
            m.Записать(ib.РежимЗаписиДокумента.Проведение); newdoc = s(m.Ссылка)
        if typ == '3':
            x = SORT_T.Скопировать(); x.Дата = d + SHIFT; x.Склад = a['skr']; x.Организация = oa
            tm = SORT_T.Товары.Получить(0); x.Товары.Очистить()
            r = x.Товары.Добавить(); ib.ЗаполнитьЗначенияСвойств(r, tm)
            r.Номенклатура = a['nr']; r.НоменклатураОприходование = b['nr']; r.Количество = round(t, 3)
            if hasattr(r, 'КоличествоУпаковок'): r.КоличествоУпаковок = round(t, 3)
            for f, v in (('Характеристика', a['xr']), ('ХарактеристикаОприходование', b['xr'])):
                try: setattr(r, f, v)
                except Exception: pass
            for f in ('АналитикаУчетаНоменклатуры', 'АналитикаУчетаНоменклатурыОприходование', 'Назначение', 'НазначениеОприходование', 'Серия', 'СерияОприходование', 'Упаковка', 'УпаковкаОприходование'):
                try: setattr(r, f, None)
                except Exception: pass
            x.Комментарий = f"{TAG} недостача {a['n'][:40]} ({a['doc'][:40]}) = излишек {b['n'][:40]} ({b['doc'][:40]}) — пересортица"
            x.Записать(ib.РежимЗаписиДокумента.Проведение); newdoc = s(x.Ссылка)
        reduce(b['ref'], b['nr'], b['xr'], t, b['ns'], 'излишек уменьшен (сопоставлен)')
        reduce(a['ref'], a['nr'], a['xr'], t, a['ns'], 'недостача уменьшена (сопоставлена)')
        ib.ЗафиксироватьТранзакцию(); ok[typ] += 1; made.append((desc, newdoc))
    except Exception as e:
        try: ib.ОтменитьТранзакцию()
        except Exception: pass
        bad.append((desc, (msgs() or str(e))[-220:]))
print('DRY' if DRY else 'WRITE', 'сделано по типам', dict(ok), '| не вышло', len(bad))
for x in bad[:25]: print('  НЕТ', x[0], '|', x[1])
if not DRY:
    for x in made[:10]: print('  ОК', x[0], '|', x[1][:50])
    log(f'22-В ANESCOM_FIX: сделано {dict(ok)}, не вышло {len(bad)}')
