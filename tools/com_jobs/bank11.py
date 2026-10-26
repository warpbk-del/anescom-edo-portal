# (чтение) 1030 «2209 … KZT»: по выбранным месяцам — нетто по видам документов и по корр. счетам, топ документов в обе стороны.
import collections
MONTHS = globals().get('MONTHS', ['2025-10', '2025-11', '2025-05', '2026-05'])
acc = q('ВЫБРАТЬ Б.Ссылка КАК С ИЗ Справочник.БанковскиеСчетаОрганизаций КАК Б ГДЕ Б.Наименование = "2209 в АО ""Народный Банк Казахстана"" KZT"')[0]['С']
X = ib.XMLСтрока; xa = X(acc)
for m in MONTHS:
    y, mo = int(m[:4]), int(m[5:])
    N = datetime.datetime(y, mo, 1, 5, 0); K = datetime.datetime(y + (mo == 12), (mo % 12) + 1, 1, 4, 59, 59)
    R = q('ВЫБРАТЬ Х.Регистратор КАК Р, Х.Сумма КАК С, Х.СчетДт.Код КАК Дт, Х.СчетКт.Код КАК Кт, Х.СубконтоДт1 КАК СД, Х.СубконтоКт1 КАК СК, Х.Содержание КАК Сд '
          'ИЗ РегистрБухгалтерии.{REG}.ДвиженияССубконто(&Н, &К, СчетДт.Код ПОДОБНО "1030%" ИЛИ СчетКт.Код ПОДОБНО "1030%", , ) КАК Х', Н=N, К=K)
    bt = collections.Counter(); bc = collections.Counter(); bd = collections.Counter()
    for r in R:
        v = float(r['С'] or 0)
        sg = (1 if r['Дт'].startswith('1030') and X(r['СД']) == xa else 0) - (1 if r['Кт'].startswith('1030') and X(r['СК']) == xa else 0)
        if not sg: continue
        t = s(r['Р']).split(' 0')[0][:34]; bt[t] += sg * v; bc[r['Кт'] if sg > 0 else r['Дт']] += sg * v; bd[s(r['Р'])[:62]] += sg * v
    print(f'=== {m}: нетто {sum(bt.values())/1e6:,.2f} млн')
    print('  виды:', ', '.join(f'{k}:{v/1e6:,.2f}' for k, v in sorted(bt.items(), key=lambda x: x[1]) if abs(v) > 1e5))
    print('  корр:', ', '.join(f'{k}:{v/1e6:,.2f}' for k, v in sorted(bc.items(), key=lambda x: x[1]) if abs(v) > 1e5))
    lst = sorted(bd.items(), key=lambda x: x[1])
    for k, v in lst[:4] + lst[-4:]: print(f'    {v/1e6:>10,.2f} {k}')
