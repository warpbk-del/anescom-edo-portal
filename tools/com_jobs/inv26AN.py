# 22-В только ANESCOM_FIX (решение 26.10 15:55): списания недостач ↔ оприходования излишков 2026 внутри фирмы.
# ТОЛЬКО ПЛАН (чтение). Типы: 1 тот же товар, тот же склад (обе строки убрать); 2 тот же товар, другой склад (перемещение);
# 3 другой цвет/декор, тот же склад (пересортица). Межфирменное (АВТОКОМП) не трогаем. «Ламинация» 08.09 (00НФ-000009/000012) — отдельный блок 22-И, исключена.
import re, csv, collections, datetime
N6, K6 = datetime.datetime(2026, 1, 1), datetime.datetime(2026, 12, 31, 23, 59, 59)
COL = r'\b(бел\w*|сер\w*|черн\w*|чёрн\w*|кор\w*|антрацит\w*|золот\w*|дуб\w*|орех\w*|махагон\w*|венге|графит\w*|бронз\w*|ral\s*\d+|\d{4}|ral\d+|темн\w*|тёмн\w*|светл\w*)\b'
def k2(n): return re.sub(r'\s+', ' ', re.sub(COL, '', n.lower())).strip()
EV = []
def load(doc, t):
    for r in q(f'ВЫБРАТЬ Т.Ссылка КАК Р, Т.НомерСтроки КАК НС, Т.Ссылка.Дата КАК Д, Т.Ссылка.Склад КАК Ск, Т.Номенклатура КАК Н, Т.Характеристика КАК Х, Т.Количество КАК К '
               f'ИЗ Документ.{doc}.Товары КАК Т ГДЕ Т.Ссылка.Проведен И Т.Ссылка.Дата МЕЖДУ &А И &Б И НЕ Т.Ссылка.Организация.Префикс = "GT" '
               f'И НЕ (Т.Ссылка.Склад.Наименование ПОДОБНО "%Ламинац%" И НАЧАЛОПЕРИОДА(Т.Ссылка.Дата, ДЕНЬ) = &Л)', А=N6, Б=K6, Л=datetime.datetime(2026, 9, 8)):
        n = s(r['Н']); EV.append(dict(t=t, ref=r['Р'], doc=s(r['Р']), ns=r['НС'], d=r['Д'], sk=s(r['Ск']), skr=r['Ск'], nr=r['Н'], xr=r['Х'], n=n, x=s(r['Х']),
                                      k1=n + '|' + s(r['Х']), k2=k2(n), q=float(r['К']), r=float(r['К'])))
load('СписаниеНедостачТоваров', 'S'); load('ОприходованиеИзлишковТоваров', 'P')
SS = [e for e in EV if e['t'] == 'S']; PP = [e for e in EV if e['t'] == 'P']
print('2026 ANESCOM: списаний недостач строк', len(SS), 'ед.', round(sum(e['q'] for e in SS)), '| оприходований строк', len(PP), 'ед.', round(sum(e['q'] for e in PP)))
RULES = [('1 тот же товар и склад — убрать обе строки', lambda a, b: a['sk'] == b['sk'] and a['k1'] == b['k1']),
         ('2 перемещение между складами', lambda a, b: a['sk'] != b['sk'] and a['k1'] == b['k1']),
         ('3 пересортица на складе (другой цвет)', lambda a, b: a['sk'] == b['sk'] and a['k1'] != b['k1'] and a['k2'] == b['k2'] and len(a['k2']) > 8)]
PLAN26 = []
for nm, f in RULES:
    for a in SS:
        if a['r'] <= 1e-6: continue
        for b in PP:
            if b['r'] > 1e-6 and f(a, b):
                t = min(a['r'], b['r']); a['r'] -= t; b['r'] -= t; PLAN26.append((nm, a, b, t))
                if a['r'] <= 1e-6: break
g = collections.defaultdict(lambda: [0, 0.0])
for nm, a, b, t in PLAN26: g[nm][0] += 1; g[nm][1] += t
for k in sorted(g): print(f'{k}: пар {g[k][0]}, ед. {g[k][1]:,.1f}')
print('ОСТАЁТСЯ: недостач ед.', round(sum(e['r'] for e in SS)), '| излишков ед.', round(sum(e['r'] for e in PP)))
for nm, a, b, t in PLAN26[:10]: print(' ', nm[:2], f'{t:g}', a['n'][:38], a['sk'][:18], '→', b['n'][:38] if nm.startswith('3') else '', b['sk'][:18], str(a['d'])[:10], str(b['d'])[:10])
fn = r'D:\anescom_edo\data\reports\inv26_ANESCOM_FIX_plan.csv'
with open(fn, 'w', encoding='utf-8-sig', newline='') as fh:
    w = csv.writer(fh, delimiter=';')
    w.writerow(['Вид', 'Кол-во', 'Списание: документ', 'дата', 'склад', 'товар', 'Оприходование: документ', 'дата', 'склад', 'товар'])
    for nm, a, b, t in PLAN26: w.writerow([nm, round(t, 3), a['doc'], str(a['d'])[:16], a['sk'], a['k1'], b['doc'], str(b['d'])[:16], b['sk'], b['k1']])
print('CSV', fn)
