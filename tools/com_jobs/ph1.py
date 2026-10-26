# Телефоны → +7XXXXXXXXXX (ANESCOM_FIX). DRY=True по умолчанию; TEST=N — записать только N объектов (проверка).
# Меняем строку КИ: Представление, Значение (через БСП КонтактнаяИнформацияПоПредставлению), НомерТелефона/НомерТелефонаБезКодов (если есть).
import re, collections, csv
DRY = globals().get('DRY', True); TEST = globals().get('TEST', 0)
UKI = ib.УправлениеКонтактнойИнформацией
def norm(p):
    """Вернуть +7XXXXXXXXXX или None (неоднозначно)."""
    if len(re.findall(r'\d{6,}|\d[\d\s\-\(\)]{8,}\d', p)) > 1 and re.search(r'[,;/]|\s{2,}', p): return None   # несколько номеров
    d = re.sub(r'\D', '', p)
    if len(d) == 11 and d[0] in '78': return '+7' + d[1:]
    if len(d) == 10 and d[0] == '7': return '+7' + d
    if len(d) == 12 and d.startswith('77'): return None
    return None
ST = collections.Counter(); bad = []; plan = collections.defaultdict(list); REFS = {}
for cat in ('Партнеры', 'Контрагенты', 'КонтактныеЛицаПартнеров', 'ФизическиеЛица'):
    for r in q(f'ВЫБРАТЬ КИ.Ссылка КАК С, КИ.Вид КАК Вд, КИ.Представление КАК П, КИ.НомерСтроки КАК Н ИЗ Справочник.{cat}.КонтактнаяИнформация КАК КИ ГДЕ КИ.Тип = ЗНАЧЕНИЕ(Перечисление.ТипыКонтактнойИнформации.Телефон) И НЕ КИ.Ссылка.ПометкаУдаления'):
        p = (r['П'] or '').strip()
        if re.fullmatch(r'\+7\d{10}', p): continue
        n = norm(p)
        if n:
            kk = (cat, ib.XMLСтрока(r['С'])); REFS[kk] = r['С']; plan[kk].append((r['Н'], p, n)); ST['fix'] += 1
        else: bad.append([cat, s(r['С']), s(r['Вд']), p]); ST['manual'] += 1
print('К ИСПРАВЛЕНИЮ строк', ST['fix'], 'объектов', len(plan), '| вручную (неоднозначно)', ST['manual'])
for (cat, k), rows in list(plan.items())[:6]:
    for n_, p, n in rows: print('  ', cat, '|', p, '→', n)
for b in bad[:12]: print('  ?', b[0], '|', b[1][:30], '|', b[3])
with open(r'D:\anescom_edo\data\reports\Телефоны_вручную.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f, delimiter=';'); w.writerow(['Справочник', 'Объект', 'Вид', 'Телефон сейчас']); w.writerows(bad)
if not DRY:
    done = err = 0; errs = []
    for (cat, k), rows in plan.items():
        if TEST and done >= TEST: break
        try:
            ref = REFS[(cat, k)]
            ob = ref.ПолучитьОбъект(); T = ob.КонтактнаяИнформация
            for n_, p, n in rows:
                row = T.Получить(n_ - 1)
                assert (row.Представление or '').strip() == p, 'строка изменилась'
                row.Значение = UKI.КонтактнаяИнформацияПоПредставлению(n, row.Вид)
                row.Представление = n
                for f, v in (('НомерТелефона', n), ('НомерТелефонаБезКодов', n[2:])):
                    try: setattr(row, f, v)
                    except Exception: pass
                try: row.ЗначенияПолей = ''
                except Exception: pass
            ob.ОбменДанными.Загрузка = True; ob.Записать(); done += 1
            if TEST: print('  WRITE', s(ref)[:40], [(T.Получить(n_ - 1).Представление, (T.Получить(n_ - 1).Значение or '')[:80]) for n_, p, n in rows])
        except Exception as e:
            err += 1; errs.append((k[:8], str(e)[-120:]))
    print('WRITE объектов', done, 'ошибок', err, errs[:5])
    log(f'телефоны +7: объектов {done}, ошибок {err} (TEST={TEST})')
