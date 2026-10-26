# 21-32 (только чтение): состав начальной страницы у всех пользователей ИБ.
# Хранилище: ХранилищеСистемныхНастроек, ключ "Общее/НастройкиНачальнойСтраницы".
import collections
cnt = collections.Counter(); users_with = collections.defaultdict(list); nouser = 0; nset = 0
U = ib.ПользователиИнформационнойБазы.ПолучитьПользователей()
print('USERS', U.Количество())
for i in range(U.Количество()):
    u = U.Получить(i); name = u.Имя
    try:
        st = ib.ХранилищеСистемныхНастроек.Загрузить("Общее/НастройкиНачальнойСтраницы", "", None, name)
    except Exception as e:
        print(' ERR', name, str(e)[-80:]); continue
    if st is None:
        nouser += 1; continue
    nset += 1
    sf = st.ПолучитьСоставФорм()
    for col in ('ЛеваяКолонка', 'ПраваяКолонка'):
        arr = getattr(sf, col)
        for j in range(arr.Количество()):
            f = arr.Получить(j); cnt[(col, f)] += 1; users_with[f].append(name)
print('WITH_SETTINGS', nset, 'DEFAULT(no settings)', nouser)
for (col, f), n in cnt.most_common():
    print(f' {n:3d} {col[:5]} {f}')
# состав по умолчанию: новый объект НастройкиНачальнойСтраницы (так делает обработка для пользователей без настроек)
try:
    sf = ib.NewObject("НастройкиНачальнойСтраницы").ПолучитьСоставФорм()
    for col in ('ЛеваяКолонка', 'ПраваяКолонка'):
        arr = getattr(sf, col)
        print('DEFAULT', col[:5], [arr.Получить(j) for j in range(arr.Количество())])
    print('NEW СоставФорм ok', ib.NewObject("СоставФормНачальнойСтраницы").ЛеваяКолонка.Количество())
except Exception as e:
    print('DEFAULT ERR', str(e)[-150:])
for f, us in users_with.items():
    if 'онитор' in f:
        print('MON', f, len(us), ', '.join(us[:6]))
