# (чтение) 21-26 / шаг 25: где хранится «Порядок округления результатов расчёта налогов»; текущие записи.
for kind in ('РегистрыСведений', 'Справочники', 'Константы'):
    coll = getattr(MD, kind)
    for i in range(coll.Количество()):
        m = coll.Получить(i)
        if 'кругл' in m.Имя.lower() or 'кругл' in (m.Синоним or '').lower():
            print(kind, m.Имя, '|', m.Синоним)
            if kind == 'РегистрыСведений':
                f = []
                for c in (m.Измерения, m.Ресурсы, m.Реквизиты): f += [c.Получить(j).Имя for j in range(c.Количество())]
                per = m.ПериодичностьРегистраСведений if hasattr(m, 'ПериодичностьРегистраСведений') else ''
                print('   поля', f, '| периодичность', s(per))
                try:
                    rows = q(f'ВЫБРАТЬ * ИЗ РегистрСведений.{m.Имя} КАК Т')
                    print('   записей', len(rows))
                    for r in rows[:40]: print('    ', {k: s(v)[:28] for k, v in r.items()})
                except Exception as e: print('   ERR', str(e)[-100:])
