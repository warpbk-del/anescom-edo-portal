import collections
_L = [l for l in open(LOG, encoding='utf-8') if '21-28d ' in l]
okS = {l.split('21-28d списание ')[1].rsplit(': ', 1)[0] for l in _L if '21-28d списание ' in l}
okO = {l.split('21-28d оприходование ')[1].rsplit(': ', 1)[0] for l in _L if '21-28d оприходование ' in l}
okV = {l.split('21-28d ввод ')[1].split(': изменено')[0] for l in _L if '21-28d ввод ' in l}
print(len(okS), len(okO), len(okV))
def _vd(wh, it): return s((VROW.get((wh, it)) or [[VV[wh][0]]])[0][0])[-40:]
MIS = []; _c = collections.Counter()
for kind, it, wh, ref, ns, rr, sm, pr in plan:
    V = _vd(wh, it) in okV; D = s(ref[0]) in (okO if kind == 'оприходование' else okS)
    _c[(kind[:4], V, D)] += 1
    if V != D: MIS.append((kind, it, wh, ref, ns, rr, V, D))
print(dict(_c)); print('НЕСОВПАДЕНИЙ', len(MIS), 'кол-во', round(sum(x[5] for x in MIS), 3))
print('ввод упали:', sorted({w[:22] for k, it, w, *_ in plan if _vd(w, it) not in okV}))
