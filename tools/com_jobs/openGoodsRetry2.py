KC.Установить(False)
try:
    for (k, dn), items in byDoc.items():
        if k == 'списание' and dn not in okS:
            try:
                print(dn[-35:], cut_lines(items[0][0], items)); log(f'21-28d списание {dn}: повтор успешно, строк {len(items)}')
            except Exception as e:
                print('ОШИБКА', dn[-35:], msgs(e))
finally:
    KC.Установить(True); print('контроль', KC.Получить())
