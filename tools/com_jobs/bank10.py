# (чтение) 1030 «2209 … KZT» ANESCOM: чистое движение по видам документов (2025–25.10.2026) и по месяцам; крупнейшие документы.
import collections
D = datetime.datetime(2026, 10, 26, 5, 0); N = datetime.datetime(2025, 1, 1, 5, 0)
acc = q('ВЫБРАТЬ Б.Ссылка КАК С ИЗ Справочник.БанковскиеСчетаОрганизаций КАК Б ГДЕ Б.Наименование = "2209 в АО ""Народный Банк Казахстана"" KZT"')[0]['С']
R = q('ВЫБРАТЬ Х.Регистратор КАК Р, Х.Период КАК П, Х.Сумма КАК С, Х.СчетДт.Код КАК Дт, Х.СчетКт.Код КАК Кт, Х.СубконтоДт1 КАК СД, Х.СубконтоКт1 КАК СК '
      'ИЗ РегистрБухгалтерии.{REG}.ДвиженияССубконто(&Н, &Д, СчетДт.Код ПОДОБНО "1030%" ИЛИ СчетКт.Код ПОДОБНО "1030%", , ) КАК Х ГДЕ ((Х.СчетДт.Код ПОДОБНО "1030%" И Х.СубконтоДт1 = &Б) ИЛИ (Х.СчетКт.Код ПОДОБНО "1030%" И Х.СубконтоКт1 = &Б))', Н=N, Д=D, Б=acc)
X = ib.XMLСтрока; xa = X(acc)
bytype = collections.Counter(); bymon = collections.Counter(); bydoc = collections.Counter(); corr = collections.Counter()
for r in R:
    v = float(r['С'] or 0)
    sign = (1 if r['Дт'].startswith('1030') and X(r['СД']) == xa else 0) - (1 if r['Кт'].startswith('1030') and X(r['СК']) == xa else 0)
    if not sign: continue
    t = s(r['Р']).split(' 0')[0].split(' 00')[0][:40]; bytype[t] += sign * v; bymon[str(r['П'])[:7]] += sign * v; bydoc[s(r['Р'])[:70]] += sign * v
    corr[(r['Дт'] if sign < 0 else r['Кт'])] += sign * v
print('проводок', len(R), '| итог за период', f'{sum(bytype.values()):,.2f}')
print('ПО ВИДАМ:'); [print(f'  {v:>18,.2f}  {k}') for k, v in sorted(bytype.items(), key=lambda x: x[1])]
print('ПО МЕСЯЦАМ:', ', '.join(f'{k}:{v/1e6:,.2f}' for k, v in sorted(bymon.items())))
print('КОРР. СЧЕТА (нетто):', ', '.join(f'{k}:{v/1e6:,.2f}' for k, v in sorted(corr.items(), key=lambda x: x[1])[:12]))
print('КРУПНЕЙШИЕ ДОК. (минус):'); [print(f'  {v:>16,.2f} {k}') for k, v in sorted(bydoc.items(), key=lambda x: x[1])[:12]]
