# (чтение) детали остатка: шуруп (крупная строка) и группы, что есть и в недостачах, и в излишках
import re
def grp(n): return ' '.join(re.sub(r'[\d,.]+(мм|м)?', '', n.lower()).split()[:2])
big = max(SS, key=lambda e: e['r'])
o = big['ref']; row = [o.Товары.Получить(i) for i in range(o.Товары.Количество()) if o.Товары.Получить(i).НомерСтроки == big['ns']][0]
print('КРУПНАЯ:', big['doc'][:60], '|', big['n'][:50], '| кол-во', big['q'], '| ед.', s(big['nr'].ЕдиницаИзмерения), '| сумма', s(getattr(row, 'Сумма', '')), '| склад', big['sk'])
print('   автор', s(o.Ответственный) if hasattr(o, 'Ответственный') else '', '| коммент', (o.Комментарий or '')[:80])
gs = {grp(e['n']) for e in SS if e['r'] > 1e-6} & {grp(e['n']) for e in PP if e['r'] > 1e-6}
for g in sorted(gs):
    print('==', g)
    for t, L in (('-', SS), ('+', PP)):
        for e in L:
            if e['r'] > 1e-6 and grp(e['n']) == g: print(f"   {t}{e['r']:>8,.0f} {e['n'][:48]:48s} {e['x'][:12]:12s} {e['sk'][:16]} {str(e['d'])[:10]}")
