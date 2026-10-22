import json
V=1.16; M=9.7
d=json.load(open('geze.json'))
for x in d:
    x['uin']=x['pin']/x['qin'] if x['qin'] else None
    x['uland']=x['cin']/x['qin'] if x['qin'] else None
    x['extra']=(x['cin']/x['pin']-1)*100 if x['pin'] else None
    x['revx']=x['rev']/V
    x['marg']=x['revx']-x['scost']
    x['mpct']=x['marg']/x['revx']*100 if x['rev'] else None
    x['avgp']=x['rev']/x['qs'] if x['qs'] else None
    x['dpct']=x['disc']/(x['rev']+x['disc'])*100 if x['rev'] else None
    x['ucs']=x['scost']/x['qs'] if x['qs'] else None
    x['mon']=x['q1']/(x['qs']/M) if x['qs'] else None
    x['short']=x['name'].replace('Доводчик ','').replace('дверной ','').replace(' size EN',' EN').replace('Пластина монтажная','Пластина').replace('Тяга рычажная','Тяга').replace('с тягой','').strip()
json.dump(d,open('geze2.json','w'),ensure_ascii=False)
S=lambda a,f=lambda x:True: sum(x[a] or 0 for x in d if f(x))
T={a:S(a) for a in ['q0','c0','qin','pin','cin','qout','cout','q1','c1','qs','rev','disc','scost','spur','sadd','revx','marg']}
T['dead']=S('c1',lambda x:x['q1']>0 and x['qs']==0); T['deadq']=S('q1',lambda x:x['q1']>0 and x['qs']==0)
T['nonsale_q']=T['qout']-T['qs']
json.dump(T,open('tot.json','w'))
for k,v in T.items(): print(k,round(v))
print('extra%',T['cin']/T['pin']-1,'margin%',T['marg']/T['revx'],'disc%',T['disc']/(T['rev']+T['disc']),'mon',T['q1']/(T['qs']/M))
for x in sorted(d,key=lambda x:x['mpct'] if x['mpct'] is not None else 999)[:8]: print(x['short'][:40],x['qs'],round(x['avgp'] or 0),round(x['ucs'] or 0),round(x['mpct'] or 0))
