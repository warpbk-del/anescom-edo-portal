import openpyxl, json, re
VAT=1.16
def norm(s): return re.sub(r'\s+',' ',s.replace(', шт','')).strip().lower()
ws=openpyxl.load_workbook('geze_sebest_2026.xlsx',data_only=True).active
items={}
org=None
for r in ws.iter_rows(min_row=12,values_only=True):
    if r[0] and not r[1]:
        org=r[0]; continue
    if not r[1]: continue
    k=norm(r[1]); g=lambda i: r[i] or 0
    d=items.setdefault(k,dict(art=r[0],name=r[1].strip(),q0=0,c0=0,qin=0,pin=0,cin=0,qout=0,cout=0,q1=0,c1=0,rev=0,scost=0,spur=0,sadd=0))
    for a,i in [('q0',5),('c0',7),('qin',9),('pin',10),('cin',13),('qout',14),('cout',15),('q1',16),('c1',17)]: d[a]+=g(i)
ws=openpyxl.load_workbook('geze_valovaya_2026_kol.xlsx',data_only=True).active
for r in ws.iter_rows(min_row=15,values_only=True):
    if not r[3]: continue
    k=norm(r[3]); d=items.setdefault(k,dict(art=r[0],name=r[3].strip(),q0=0,c0=0,qin=0,pin=0,cin=0,qout=0,cout=0,q1=0,c1=0,rev=0,scost=0,spur=0,sadd=0))
    d['qs']=d.get('qs',0)+(r[7] or 0); d['rev']+=r[8] or 0; d['disc']=d.get('disc',0)+(r[9] or 0); d['scost']+=r[12] or 0; d['spur']+=r[13] or 0; d['sadd']+=r[14] or 0
price={norm(x['name']):x['aktobe'] for x in json.load(open('/tmp/claude-0/price_items.json')) if 'GEZE' in x['name'].upper()}
out=[]
for k,d in items.items():
    d['list']=price.get(k)
    # продано шт: по доле себестоимости продаж в себестоимости расхода
    d.setdefault('qs',0); d.setdefault('disc',0)
    out.append(d)
out.sort(key=lambda d:-(d['rev'] or 0)-d['c0']*0.001)
json.dump(out,open('geze.json','w'),ensure_ascii=False,indent=0)
T=lambda a: sum(d[a] or 0 for d in out)
print({a:round(T(a)) for a in ['q0','c0','qin','pin','cin','qout','cout','q1','c1','rev','scost','spur','sadd','qs','disc']})
for d in out: print(d['name'][:45],d['qout'],d['qs'],round(d['cout']-d['scost']),round(d['rev']),round(d['disc']),d['list'])
