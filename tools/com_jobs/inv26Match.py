import csv
N6,K6=DT.datetime(2026,1,1),DT.datetime(2026,10,31,23,59,59)
EV=[]
def add(f,t,d,sk,n,q,v,doc):
    if q>0.0001:EV.append(dict(f=f,t=t,d=str(d)[:10],sk=sk.strip(),n=n.strip(),q=q,v=v,doc=doc.strip()))
for r in QA('ВЫБРАТЬ Т.Номенклатура Н,Т.Количество К,Т.Ссылка Р,Т.Ссылка.Дата Д,Т.Ссылка.Склад Ск ИЗ Документ.СписаниеНедостачТоваров.Товары Т ГДЕ Т.Ссылка.Проведен И Т.Ссылка.Дата МЕЖДУ &Н И &К И НЕ Т.Ссылка.Номер ПОДОБНО "%000009"',Н=N6,К=K6):
    add("AN","S",r["Д"],SA(r["Ск"]),SA(r["Н"]),float(r["К"]),0,SA(r["Р"]))
for r in QA('ВЫБРАТЬ Т.Номенклатура Н,Т.Количество К,Т.Сумма С,Т.Ссылка Р,Т.Ссылка.Дата Д,Т.Ссылка.Склад Ск ИЗ Документ.ОприходованиеИзлишковТоваров.Товары Т ГДЕ Т.Ссылка.Проведен И Т.Ссылка.Дата МЕЖДУ &Н И &К',Н=N6,К=K6):
    add("AN","P",r["Д"],SA(r["Ск"]),SA(r["Н"]),float(r["К"]),float(r["С"] or 0),SA(r["Р"]))
for x in QA('ВЫБРАТЬ Д.Ссылка Р ИЗ Документ.ПересчетТоваров Д ГДЕ Д.Дата МЕЖДУ &Н И &К И НЕ Д.Проведен И НЕ Д.ПометкаУдаления',Н=N6,К=K6):
    o=x["Р"]
    for i in range(o.Товары.Количество()):
        r=o.Товары.Получить(i);dq=float(r.КоличествоФакт or 0)-float(r.Количество or 0)
        add("AN","S" if dq<0 else "P",o.Дата,SA(o.Склад),SA(r.Номенклатура),abs(dq),0,"НЕПРОВ "+SA(o))
for x in Q('ВЫБРАТЬ Д.Ссылка Р ИЗ Документ.ПересчетТоваров Д ГДЕ Д.Дата МЕЖДУ &Н И &К И НЕ Д.Проведен И НЕ Д.ПометкаУдаления',Н=N6,К=K6):
    o=x["Р"]
    for i in range(o.Товары.Количество()):
        r=o.Товары.Получить(i);dq=float(r.КоличествоФакт or 0)-float(r.Количество or 0)
        add("AV","S" if dq<0 else "P",o.Дата,S(o.Склад),S(r.Номенклатура),abs(dq),0,"НЕПРОВ "+S(o))
for r in QA('ВЫБРАТЬ Т.Номенклатура Н,Т.Количество К,Т.Ссылка Р,Т.Ссылка.Дата Д,Т.Ссылка.Склад Ск,Т.СтатьяРасходов СР ИЗ Документ.ВнутреннееПотреблениеТоваров.Товары Т ГДЕ Т.Ссылка.Проведен И Т.Ссылка.Дата МЕЖДУ &Н И &К',Н=N6,К=K6):
    add("AN","R",r["Д"],SA(r["Ск"]),SA(r["Н"]),float(r["К"]),0,SA(r["Р"])+" / "+SA(r["СР"])[:30])
for r in Q('ВЫБРАТЬ Т.Номенклатура Н,Т.Количество К,Т.Ссылка Р,Т.Ссылка.Дата Д,Т.Ссылка.Склад Ск,Т.СтатьяРасходов СР ИЗ Документ.ВнутреннееПотреблениеТоваров.Товары Т ГДЕ (Т.Ссылка.Проведен ИЛИ Т.Ссылка.Комментарий ПОДОБНО "22-И%") И Т.Ссылка.Дата МЕЖДУ &Н И &К',Н=N6,К=K6):
    add("AV","R",r["Д"],S(r["Ск"]),S(r["Н"]),float(r["К"]),0,S(r["Р"])+" / "+S(r["СР"])[:30])
pq={b:k for a,b,k in PER}
for r in Q('ВЫБРАТЬ Т.Номенклатура Н,Т.Количество К,Т.Сумма С,Т.Ссылка Р,Т.Ссылка.Дата Д,Т.Ссылка.Склад Ск ИЗ Документ.ОприходованиеИзлишковТоваров.Товары Т ГДЕ Т.Ссылка.Проведен И Т.Ссылка.Дата МЕЖДУ &Н И &К',Н=N6,К=K6):
    n=S(r["Н"]);q=float(r["К"]);u=float(r["С"] or 0)/q if q else 0;t=min(q,pq.get(n,0));pq[n]=pq.get(n,0)-t
    add("AV","P",r["Д"],S(r["Ск"]),n,q-t,u*(q-t),S(r["Р"]))
for n,d,q,doc,p in AL:
    for e in EV:
        if q>0 and e["f"]=="AN" and e["t"]=="P" and e["n"]==n and doc in e["doc"]:
            t=min(q,e["q"]);u=e["v"]/e["q"] if e["q"] else 0;e["q"]-=t;e["v"]-=u*t;q-=t
for e in EV:e["k1"]=nz(e["n"]);e["k2"]=ck(e["n"]);e["r"]=e["q"]
SS=[e for e in EV if e["t"]=="S"];PP=[e for e in EV if e["t"]=="P"];RR=[e for e in EV if e["t"]=="R"]
print("RASHOD-spisanie",{f:(len([e for e in RR if e["f"]==f]),round(sum(e["q"] for e in RR if e["f"]==f))) for f in("AN","AV")});print("SHORT",{f:(len([e for e in SS if e["f"]==f]),round(sum(e["q"] for e in SS if e["f"]==f))) for f in("AN","AV")},"SURP",{f:(len([e for e in PP if e["f"]==f]),round(sum(e["q"] for e in PP if e["f"]==f)),round(sum(e["v"] for e in PP if e["f"]==f)/1e6,2)) for f in("AN","AV")})
ST=[("1 ВЗАИМОЗАЧЁТ на складе",lambda s,p:s["f"]==p["f"] and s["sk"]==p["sk"] and s["k1"]==p["k1"]),
("2 ПЕРЕМЕЩЕНИЕ между складами",lambda s,p:s["f"]==p["f"] and s["k1"]==p["k1"]),
("3 РЕАЛИЗАЦИЯ между фирмами",lambda s,p:s["k1"]==p["k1"]),
("4 ПЕРЕСОРТ в фирме",lambda s,p:s["f"]==p["f"] and s["k2"]==p["k2"]),
("5 РЕАЛИЗ+ПЕРЕСОРТ",lambda s,p:s["k2"]==p["k2"])]
MT=[]
for nm,f in ST:
    for s in SS:
        if s["r"]<=0:continue
        for p in PP:
            if p["r"]>0 and f(s,p):
                t=min(s["r"],p["r"]);u=p["v"]/p["q"] if p["q"] else 0;s["r"]-=t;p["r"]-=t;MT.append((nm,s,p,t,u*t))
                if s["r"]<=0:break
ST2=[("6 СПИСАНИЕ НА РАСХОДЫ→позже ИЗЛИШЕК (фирма та же)",lambda s,p:s["f"]==p["f"] and s["k1"]==p["k1"] and p["d"]>=s["d"]),
("7 СПИСАНИЕ НА РАСХОДЫ→позже ИЗЛИШЕК (другая фирма)",lambda s,p:s["k1"]==p["k1"] and p["d"]>=s["d"]),
("8 СПИСАНИЕ НА РАСХОДЫ→позже ИЗЛИШЕК другого цвета",lambda s,p:s["k2"]==p["k2"] and p["d"]>=s["d"])]
for nm,f in ST2:
    for s in RR:
        if s["r"]<=0:continue
        for p in PP:
            if p["r"]>0 and f(s,p):
                t=min(s["r"],p["r"]);u=p["v"]/p["q"] if p["q"] else 0;s["r"]-=t;p["r"]-=t;MT.append((nm,s,p,t,u*t))
                if s["r"]<=0:break
G=C.defaultdict(lambda:[0,0,0])
for nm,s,p,t,v in MT:g=G[nm];g[0]+=1;g[1]+=t;g[2]+=v
for k in sorted(G):print(k,"| строк",G[k][0],"| кол",round(G[k][1]),"| сумма излишков млн",round(G[k][2]/1e6,2))
for f in("AN","AV"):print("OSTATOK",f,"недост",round(sum(e["r"] for e in SS if e["f"]==f)),"| излишки",round(sum(e["r"] for e in PP if e["f"]==f)),round(sum(e["v"]*e["r"]/e["q"] for e in PP if e["f"]==f and e["q"])/1e6,2),"млн")
fn=r"D:\anescom_edo\data\reports\inv26_match.csv"
with open(fn,"w",encoding="utf-8-sig",newline="") as fh:
    w=csv.writer(fh,delimiter=";")
    w.writerow(["Вид","Кол-во","Сумма излишка","Недостача/списание: фирма","склад","документ","дата","товар","Излишек: фирма","склад","документ","дата","товар"])
    for nm,s,p,t,v in MT:w.writerow([nm,round(t,3),round(v,2),s["f"],s["sk"],s["doc"],s["d"],s["n"],p["f"],p["sk"],p["doc"],p["d"],p["n"]])
    for e in SS:
        if e["r"]>0.0001:w.writerow(["6 ОСТАТОК недостача",round(e["r"],3),"",e["f"],e["sk"],e["doc"],e["d"],e["n"],"","","","",""])
    for e in PP:
        if e["r"]>0.0001:w.writerow(["7 ОСТАТОК излишек",round(e["r"],3),round(e["v"]*e["r"]/e["q"],2) if e["q"] else 0,"","","","","",e["f"],e["sk"],e["doc"],e["d"],e["n"]])
print("CSV:",fn,len(MT))
