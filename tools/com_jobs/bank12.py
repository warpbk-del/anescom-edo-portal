# (чтение) По документам: оперативный РН ДенежныеСредстваБезналичные (счёт «2209 … KZT») против БУ 1030 по тому же счёту, 2025–25.10.2026.
import collections, csv
N, D = datetime.datetime(2025, 1, 1, 5, 0), datetime.datetime(2026, 10, 26, 5, 0)
acc = q('ВЫБРАТЬ Б.Ссылка КАК С ИЗ Справочник.БанковскиеСчетаОрганизаций КАК Б ГДЕ Б.Наименование = "2209 в АО ""Народный Банк Казахстана"" KZT"')[0]['С']
X = ib.XMLСтрока; xa = X(acc)
op = collections.Counter(); bu = collections.Counter(); name = {}
for r in q('ВЫБРАТЬ Т.Регистратор КАК Р, СУММА(ВЫБОР КОГДА Т.ВидДвижения = ЗНАЧЕНИЕ(ВидДвиженияНакопления.Приход) ТОГДА Т.Сумма ИНАЧЕ -Т.Сумма КОНЕЦ) КАК С '
           'ИЗ РегистрНакопления.ДенежныеСредстваБезналичные КАК Т ГДЕ Т.БанковскийСчет = &Б И Т.Период МЕЖДУ &Н И &Д СГРУППИРОВАТЬ ПО Т.Регистратор', Б=acc, Н=N, Д=D):
    k = X(r['Р']); op[k] += float(r['С'] or 0); name[k] = r['Р']
for r in q('ВЫБРАТЬ Х.Регистратор КАК Р, Х.Сумма КАК С, Х.СчетДт.Код КАК Дт, Х.СчетКт.Код КАК Кт, Х.СубконтоДт1 КАК СД, Х.СубконтоКт1 КАК СК '
           'ИЗ РегистрБухгалтерии.{REG}.ДвиженияССубконто(&Н, &Д, СчетДт.Код ПОДОБНО "1030%" ИЛИ СчетКт.Код ПОДОБНО "1030%", , ) КАК Х', Н=N, Д=D):
    sg = (1 if r['Дт'].startswith('1030') and X(r['СД']) == xa else 0) - (1 if r['Кт'].startswith('1030') and X(r['СК']) == xa else 0)
    if sg: k = X(r['Р']); bu[k] += sg * float(r['С'] or 0); name[k] = r['Р']
print('оперативно', f'{sum(op.values()):,.2f}', '| БУ', f'{sum(bu.values()):,.2f}')
diff = [(k, op.get(k, 0), bu.get(k, 0)) for k in set(op) | set(bu) if abs(op.get(k, 0) - bu.get(k, 0)) > 0.5]
diff.sort(key=lambda x: x[2] - x[1])
bytype = collections.Counter(); cnt = collections.Counter()
for k, o, b in diff:
    t = s(name[k]).split(' 0')[0][:34]; bytype[t] += b - o; cnt[t] += 1
print('док. с расхождением', len(diff), '| сумма (БУ−опер.)', f'{sum(b - o for _, o, b in diff):,.2f}')
for t, v in sorted(bytype.items(), key=lambda x: x[1]): print(f'  {v:>16,.2f}  {cnt[t]:4d} {t}')
for k, o, b in diff[:15]: print(f'   опер {o:>14,.2f} | БУ {b:>14,.2f} | {s(name[k])[:70]}')
with open(r'D:\anescom_edo\data\reports\1030_KZT_oper_vs_BU.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f, delimiter=';'); w.writerow(['Документ', 'Оперативно', 'БУ 1030', 'Разница БУ-опер'])
    for k, o, b in diff: w.writerow([s(name[k]), round(o, 2), round(b, 2), round(b - o, 2)])
BANKDIFF = diff
