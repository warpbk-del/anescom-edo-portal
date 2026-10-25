import re
ANc=IB_POOL[r"D:\Base\1C\KA2026"][0]
def QA(t,**p):
    z=ANc.NewObject("Запрос");z.Текст=t
    for k,v in p.items():z.УстановитьПараметр(k,v)
    r=z.Выполнить();cols=[r.Колонки.Получить(i).Имя for i in range(r.Колонки.Количество())];s=r.Выбрать();o=[]
    while s.Следующий():o.append({c:getattr(s,c) for c in cols})
    return o
SA=lambda v:ANc.String(v)
def nz(n):
    s=n.lower().replace("ё","е");s=re.sub(r"^\s*(ак|ak)\s*-\s*","",s)
    s=s.replace("чёрн","чер").replace("черн","чер").replace("черный","чер").replace("белый","бел").replace("темно-сер","тс")
    return re.sub(r"[^0-9a-zа-я]+","",s)
def art(n):
    u=n.upper().replace("М","M").replace("Р","P").replace("Т","T").replace("Х","X").replace("А","A").replace("С","C").replace("Е","E").replace("О","O").replace("К","K").replace("В","B").replace("Н","H")
    m=re.search(r"[FWDMP]{1,2}\d{2,3}\.\d{2}\.\d{2}|TПY\s*-?\s*\d+|HELIOS|BAULINE|STANDART",u.replace("П","П"))
    return m.group(0) if m else None
N6,K6=DT.datetime(2026,1,1),DT.datetime(2026,10,31,23,59,59)
# АВТОКОМП: недостачи 2026 = непроведённый пересчёт 08.09 №1 ; излишки 2026 = оприходования излишков (за вычетом пересортицы 0000-000003)
avS=[];avP=[]
for x in Q('ВЫБРАТЬ Д.Ссылка Р ИЗ Документ.ПересчетТоваров Д ГДЕ Д.Дата МЕЖДУ &Н И &К И НЕ Д.Проведен И НЕ Д.ПометкаУдаления',Н=N6,К=K6):
    o=x["Р"]
    for i in range(o.Товары.Количество()):
        r=o.Товары.Получить(i);d=float(r.КоличествоФакт or 0)-float(r.Количество or 0)
        if d<-0.0001:avS.append([S(r.Номенклатура),-d,S(o)[-30:]])
        elif d>0.0001:avP.append([S(r.Номенклатура),d,S(o)[-30:]])
for r in Q('ВЫБРАТЬ Т.Номенклатура Н,Т.Количество К,Т.Сумма С,Т.Ссылка Р ИЗ Документ.ОприходованиеИзлишковТоваров.Товары Т ГДЕ Т.Ссылка.Проведен И Т.Ссылка.Дата МЕЖДУ &Н И &К',Н=N6,К=K6):
    avP.append([S(r["Н"]),float(r["К"]),S(r["Р"])[-30:]])
for a,b,k in PER:
    for x in avP:
        if x[0]==b and k>0:t=min(k,x[1]);x[1]-=t;k-=t
# ANESCOM 2026: излишки и недостачи (проведённые документы)
anP=[[SA(r["Н"]),float(r["К"]),SA(r["Р"])[-32:],SA(r["Ск"])[:20],float(r["С"] or 0)] for r in QA('ВЫБРАТЬ Т.Номенклатура Н,Т.Количество К,Т.Сумма С,Т.Ссылка Р,Т.Ссылка.Склад Ск ИЗ Документ.ОприходованиеИзлишковТоваров.Товары Т ГДЕ Т.Ссылка.Проведен И Т.Ссылка.Дата МЕЖДУ &Н И &К',Н=N6,К=K6)]
anS=[[SA(r["Н"]),float(r["К"]),SA(r["Р"])[-32:],SA(r["Ск"])[:20]] for r in QA('ВЫБРАТЬ Т.Номенклатура Н,Т.Количество К,Т.Ссылка Р,Т.Ссылка.Склад Ск ИЗ Документ.СписаниеНедостачТоваров.Товары Т ГДЕ Т.Ссылка.Проведен И Т.Ссылка.Дата МЕЖДУ &Н И &К',Н=N6,К=K6)]
for n,d,q,doc,p in AL:
    for x in anP:
        if q>0 and x[0]==n and doc in x[2]:t=min(q,x[1]);x[1]-=t;q-=t
print("AV nedost",len(avS),round(sum(x[1] for x in avS)),"| AV izl",len([x for x in avP if x[1]>0]),round(sum(x[1] for x in avP)),"| AN izl",len(anP),round(sum(x[1] for x in anP)),round(sum(x[4] for x in anP)/1e6,2),"mln | AN nedost",len(anS),round(sum(x[1] for x in anS)))
def match(S_,P_,tag):
    res=[];tot=C.Counter()
    for lvl,f in ((1,nz),(2,lambda n:(art(n),nz(re.sub(r"\(.*?\)","",n))[:12]) if art(n) else None)):
        for s in S_:
            if s[1]<=0:continue
            ks=f(s[0])
            if not ks:continue
            for p in P_:
                if p[1]>0 and f(p[0])==ks:
                    t=min(s[1],p[1]);s[1]-=t;p[1]-=t;res.append((lvl,s[0],p[0],t,p[2],p[3] if len(p)>3 else ""));tot[lvl]+=t
                    if s[1]<=0:break
    print("==",tag,"sovpalo po urovnjam",dict(tot),"| ostalos",round(sum(x[1] for x in S_)))
    for r in sorted(res,key=lambda r:-r[3])[:14]:print(f"  u{r[0]} {r[3]:g} | {r[1][:38]} -> {r[2][:38]} | {r[4][:24]} {r[5]}")
    return res
M1=match(avS,anP,"NEDOSTACHA AVTOKOMP -> IZLISHKI ANESCOM")
M2=match(anS,avP,"NEDOSTACHA ANESCOM -> IZLISHKI AVTOKOMP")
print("AN nedost ostatok top:"," ; ".join(f"{x[0][:30]} {x[1]:g} {x[3]}" for x in sorted(anS,key=lambda x:-x[1])[:8]))
