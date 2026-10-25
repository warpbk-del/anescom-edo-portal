import json
d=json.load(open('/home/claude/w22/raw.json'))
items=[k for k in json.load(open('/home/claude/w22/lists.json'))['km'] if k[2]>0 or 'ПРОВЕРИТЬ' in str(k[4])]
BAD={6,7}  # закладные: в ANESCOM другая длина/профиль — не тот товар
price={}
for i,nom,dt,pr,q,s in d['p']:
    if i in BAD: continue
    if i not in price or dt>price[i][0]: price[i]=(dt,round(s/q,2) if q else pr,nom)
surp=[r for r in d['s'] if r['i'] not in BAD]
seen=set(); s2=[]
for r in surp:
    k=(r['doc'],r['line'])
    if k in seen: continue
    seen.add(k); s2.append(r)
res=[]
for i,(name,wo,_,_,_) in enumerate(items):
    lines=sorted([r for r in s2 if r['i']==i],key=lambda r:r['date'],reverse=True)
    left=wo; alloc=[]
    for r in lines:
        if left<=0: break
        q=min(left,r['qty']); left-=q
        alloc.append(dict(r,take=q,cost=round(r['sum']/r['qty']*q,2)))
    res.append(dict(i=i,name=name,wo=wo,alloc=alloc,left=left,price=price.get(i)))
json.dump(res,open('/home/claude/w22/res.json','w'),ensure_ascii=False)
q3=lambda a:a['date']>='2026-07-01'
tot=sum(x['wo'] for x in res); cov=sum(a['take'] for x in res for a in x['alloc'])
print('списано',tot,'покрыто',cov,'позиций с покрытием',sum(1 for x in res if x['alloc']))
for x in res:
    if x['alloc']:
        p=x['price']
        print(f"{x['i']:2} {x['name'][:48]:48} спис {x['wo']:>6g} покр {sum(a['take'] for a in x['alloc']):>6g} | "+"; ".join(f"{a['date']} {a['sklad'][:12]} {a['take']:g}{' Q3' if q3(a) else ''}" for a in x['alloc'])+f" | цена {p[1] if p else '—'}")
print('Q3 строки:',[(x['name'][:30],a['doc'][-30:],a['take']) for x in res for a in x['alloc'] if q3(a)])
print('без цены:',[x['name'][:40] for x in res if x['alloc'] and not x['price']])
