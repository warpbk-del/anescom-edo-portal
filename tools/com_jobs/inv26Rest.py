# (чтение) после inv26AN: что осталось без пары — по группам товара и складам; и что из этого похоже на АВТОКОМП
import collections, re
def grp(n): return ' '.join(re.sub(r'[\d,.]+(мм|м)?', '', n.lower()).split()[:2])
for nm, L in (('НЕДОСТАЧИ', SS), ('ИЗЛИШКИ', PP)):
    G = collections.defaultdict(lambda: [0.0, 0]); W = collections.defaultdict(float); D = collections.defaultdict(float); docs = set()
    for e in L:
        if e['r'] <= 1e-6: continue
        G[grp(e['n'])][0] += e['r']; G[grp(e['n'])][1] += 1; W[e['sk']] += e['r']; D[e['doc'][:45]] += e['r']; docs.add(e['doc'])
    print(f'== {nm}: строк {sum(v[1] for v in G.values())}, ед. {sum(v[0] for v in G.values()):,.0f}, документов {len(docs)}')
    for k, v in sorted(G.items(), key=lambda x: -x[1][0])[:10]: print(f'   {k[:30]:30s} {v[0]:>10,.0f} ед. ({v[1]} стр.)')
    print('   склады:', '; '.join(f'{k[:22]} {v:,.0f}' for k, v in sorted(W.items(), key=lambda x: -x[1])[:6]))
    print('   документы:', '; '.join(f'{k[-24:]} {v:,.0f}' for k, v in sorted(D.items(), key=lambda x: -x[1])[:6]))
