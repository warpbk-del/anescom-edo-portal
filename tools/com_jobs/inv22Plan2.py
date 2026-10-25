import re
AL=__AL__
def key(n):
    u=n.upper().replace("A","А").replace("C","С").replace("E","Е").replace("K","К").replace("M","М").replace("O","О").replace("P","Р").replace("T","Т").replace("X","Х").replace("Х","Х")
    m=re.search(r"([FWDМП]{1,2}\d{2,3}\.\d{2}\.\d{2})",u.replace("Р","P").replace("М","M").replace("Т","T"))
    for a,b in (("ТПУ-301","F50.10.07"),("ТПУ-6009","F50.10.14")):
        if a in u:return b
    if m:return m.group(1).replace("М","M").replace("П","P")
    v=re.search(r"ВИНТ.*?(\d,\d)Х",u)
    if v:return "ВИНТ"+v.group(1)
    return None
N8,K8=DT.datetime(2026,9,8),DT.datetime(2026,9,8,23,59,59)
W=Q('ВЫБРАТЬ Д.Ссылка Р ИЗ Документ.СписаниеНедостачТоваров Д ГДЕ Д.Дата МЕЖДУ &Н И &К И Д.Проведен',Н=N8,К=K8)
O=Q('ВЫБРАТЬ Д.Ссылка Р ИЗ Документ.ОприходованиеИзлишковТоваров Д ГДЕ Д.Дата МЕЖДУ &Н И &К И Д.Проведен',Н=N8,К=K8)
print("spisanie:",[S(x["Р"]) for x in W],"| oprih:",[S(x["Р"]) for x in O])
W=W[0]["Р"];O=O[0]["Р"]
md=AVc.Метаданные.Документы
for d in ("СписаниеНедостачТоваров","ОприходованиеИзлишковТоваров","ПересортицаТоваров","ВнутреннееПотреблениеТоваров","РеализацияТоваровУслуг"):
    t=md.Найти(d).ТабличныеЧасти.Найти("Товары");print(d,"Товары:",",".join(t.Реквизиты.Получить(i).Имя for i in range(t.Реквизиты.Количество()))[:230])
WL=[];OL=[]
for i in range(W.Товары.Количество()):
    r=W.Товары.Получить(i);WL.append([S(r.Номенклатура),float(r.Количество),float(getattr(r,"Сумма",0) or 0)])
for i in range(O.Товары.Количество()):
    r=O.Товары.Получить(i);OL.append([S(r.Номенклатура),float(r.Количество),float(getattr(r,"Сумма",0) or 0)])
print("spis strok",len(WL),"kol",round(sum(x[1] for x in WL)),"sum",round(sum(x[2] for x in WL)),"| oprih strok",len(OL),"kol",round(sum(x[1] for x in OL)),"sum",round(sum(x[2] for x in OL)))
left={i:x[1] for i,x in enumerate(WL)};plan=[]
idx={x[0]:i for i,x in enumerate(WL)}
for n,d,q,doc,p in AL:
    i=idx.get(n)
    if i is None:print(" NET v spisanii:",n[:50]);continue
    t=min(q,left[i]);left[i]-=t;plan.append(("ПРОДАЖА "+("Q3 "+d if d>="2026-07-01" else "ОКТ"),i,t))
oleft={j:x[1] for j,x in enumerate(OL)}
for i,x in enumerate(WL):
    k=key(x[0])
    if not k or left[i]<=0:continue
    for j,y in enumerate(OL):
        if oleft[j]>0 and key(y[0])==k and y[0]!=x[0]:
            t=min(left[i],oleft[j]);left[i]-=t;oleft[j]-=t;plan.append(("ПЕРЕСОРТ",i,t,j))
            if left[i]<=0:break
for i,x in enumerate(WL):
    if left[i]>0:plan.append(("ПРОИЗВОДСТВО",i,left[i]))
G=C.defaultdict(lambda:[0,0,0])
for p in plan:
    x=WL[p[1]];c=x[2]/x[1] if x[1] else 0;g=G[p[0][:8]];g[0]+=1;g[1]+=p[2];g[2]+=p[2]*c
print({k:(v[0],round(v[1]),round(v[2])) for k,v in G.items()})
print("PERESORT:"," ; ".join(f"{WL[p[1]][0][:26]}>{OL[p[3]][0][:26]} {p[2]:g}" for p in plan if p[0]=="ПЕРЕСОРТ"))
print("OPRIH 08.09 bez pary:",round(sum(oleft.values())),"sum",round(sum(oleft[j]*(OL[j][2]/OL[j][1] if OL[j][1] else 0) for j in oleft)))
print("PROIZV top:"," ; ".join(f"{WL[p[1]][0][:30]} {p[2]:g}" for p in sorted([p for p in plan if p[0]=="ПРОИЗВОДСТВО"],key=lambda p:-p[2])[:12]))
T1=Q('ВЫБРАТЬ ПЕРВЫЕ 1 Д.Ссылка Р ИЗ Документ.РеализацияТоваровУслуг Д ГДЕ Д.Проведен И Д.Контрагент.Наименование ПОДОБНО "%ANESCOM%" УПОРЯДОЧИТЬ ПО Д.Дата УБЫВ')
T2=Q('ВЫБРАТЬ ПЕРВЫЕ 1 Д.Ссылка.Ссылка Р ИЗ Документ.ВнутреннееПотреблениеТоваров.Товары Д ГДЕ Д.Ссылка.Проведен И Д.Номенклатура.Наименование ПОДОБНО "%Пленка ПВХ%" УПОРЯДОЧИТЬ ПО Д.Ссылка.Дата УБЫВ')
print("obrazec realiz:",S(T1[0]["Р"]) if T1 else "NET","| obrazec VP:",S(T2[0]["Р"]) if T2 else "NET")
if T2:
    v=T2[0]["Р"];r=v.Товары.Получить(0)
    print(" VP: podr",S(getattr(v,"Подразделение","")),"| statja",S(getattr(r,"СтатьяРасходов","")),"| analit",S(getattr(r,"АналитикаРасходов","")),"| sklad",S(v.Склад))
