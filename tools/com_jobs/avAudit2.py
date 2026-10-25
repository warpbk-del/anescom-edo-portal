import csv
D1=DT.datetime(2026,10,31,23,59,59)
PS=AVc.ПланыСчетов.Найти("Типовой") if False else None
AC={};VID={}
for r in Q(f'ВЫБРАТЬ С.Ссылка Р,С.Код К,С.Наименование Н,С.Вид В ИЗ ПланСчетов.{RG} С'):AC[S(r["К"])]=S(r["Н"]);VID[S(r["К"])]=S(r["В"])
B=C.defaultdict(lambda:[0.0,0.0])
for r in Q(f'ВЫБРАТЬ О.Счет.Код К,О.Субконто1 С1,О.СуммаОстатокДт Д,О.СуммаОстатокКт Кт ИЗ РегистрБухгалтерии.{RG}.Остатки(&Д,,,) О',Д=D1):
    x=B[(S(r["К"]),S(r["С1"]))];x[0]+=float(r["Д"] or 0);x[1]+=float(r["Кт"] or 0)
T=C.defaultdict(lambda:[0.0,0.0])
for (k,s1),(d,c) in B.items():T[k][0]+=d;T[k][1]+=c
print("== OSV 31.10.2026 (mln) schet: Dt / Kt")
print(" ; ".join(f"{k} {d/1e6:.2f}/{c/1e6:.2f}" for k,(d,c) in sorted(T.items()) if abs(d)+abs(c)>5e4))
RED=[(k,s1,d,c) for (k,s1),(d,c) in B.items() if (VID.get(k,"").startswith("Актив") and not "Пассив" in VID.get(k,"") and c>1000) or (VID.get(k,"")=="Пассивный" and d>1000)]
print("== KRASNYE ostatki:",len(RED));[print("  ",k,AC.get(k,"")[:22],"|",s1[:34],"| Dt",round(d),"Kt",round(c)) for k,s1,d,c in sorted(RED,key=lambda x:-(x[2]+x[3]))[:14]]
CP=C.defaultdict(dict)
for (k,s1),(d,c) in B.items():
    if k[:2] in("12","16","33","35","17","31") and (d or c):CP[s1][k]=d-c
ZZ=[(s1,v) for s1,v in CP.items() if any(x>1000 for x in v.values()) and any(x<-1000 for x in v.values())]
print("== ODIN KONTRAGENT i v dolgah i v avansah:",len(ZZ));[print("  ",s1[:34],"|",{k:round(x) for k,x in v.items()}) for s1,v in sorted(ZZ,key=lambda z:-sum(abs(x) for x in z[1].values()))[:12]]
print("== NALOGI po mesjacam 2026 (tys): schet Dt/Kt oborot, ostatok")
TX=C.defaultdict(lambda:C.defaultdict(lambda:[0,0]))
for r in Q(f'ВЫБРАТЬ О.Период П,О.Счет.Код К,О.СуммаОборотДт Д,О.СуммаОборотКт Кт ИЗ РегистрБухгалтерии.{RG}.Обороты(&Н,&К,Месяц,Счет.Код ПОДОБНО "31%" ИЛИ Счет.Код ПОДОБНО "32%" ИЛИ Счет.Код ПОДОБНО "142%",,,,) О',Н=DT.datetime(2026,1,1),К=D1):
    x=TX[S(r["К"])][str(r["П"])[2:7]];x[0]+=float(r["Д"] or 0);x[1]+=float(r["Кт"] or 0)
for k in sorted(TX):print(" ",k,AC.get(k,"")[:18],"|"," ".join(f"{m}:{a/1e3:.0f}/{b/1e3:.0f}" for m,(a,b) in sorted(TX[k].items())),"| ost",round((T[k][0]-T[k][1])/1e3))
print("== 8xxx ostatki na konec mesjacev 2026 (tys)")
for m in range(1,11):
    d=DT.datetime(2026,m+1,1)-DT.timedelta(seconds=1) if m<10 else D1
    o={S(r["К"]):round(float(r["Д"] or 0)-float(r["Кт"] or 0)) for r in Q(f'ВЫБРАТЬ О.Счет.Код К,О.СуммаОстатокДт Д,О.СуммаОстатокКт Кт ИЗ РегистрБухгалтерии.{RG}.Остатки(&Д,Счет.Код ПОДОБНО "8%",,) О',Д=d)}
    o={k:v for k,v in o.items() if abs(v)>1000}
    if o:print("  ",m,{k:round(v/1e3) for k,v in o.items()})
with open(r"D:\anescom_edo\data\reports\21-15\osv_31102026.csv","w",encoding="utf-8-sig",newline="") as fh:
    w=csv.writer(fh,delimiter=";");w.writerow(["Счет","Наименование","Вид","Субконто1","ОстатокДт","ОстатокКт"])
    for (k,s1),(d,c) in sorted(B.items()):w.writerow([k,AC.get(k,""),VID.get(k,""),s1,round(d,2),round(c,2)])
print("CSV osv")
