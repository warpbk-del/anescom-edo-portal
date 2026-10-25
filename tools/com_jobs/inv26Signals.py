import csv
INS=("ПОКУПКА","ПЕРЕМЕЩ","ОТ_ПЕРЕРАБ","ИЗЛИШЕК","ВОЗВРАТ","ПРОИЗВОДСТВО","СБОРКА","ВВОД_ОСТ","ПЕРЕСОРТ")
S2=[]
def dd(a,b):
    import datetime as _x
    return (_x.date.fromisoformat(b)-_x.date.fromisoformat(a)).days
for (tg,n,w),(o,L) in DOSS.items():
    days=C.OrderedDict()
    for dt,t,d,k in L:days.setdefault(dt,[]).append((t,d,k))
    b=o;neg=None;sh=None
    for dt,ops in days.items():
        for t,d,k in ops:
            if sh and dt>sh[0] and k>0 and t in INS:sh=None
            if sh and t=="ПРОДАЖА" and k<0 and dt>=sh[0]:sh[3]+=-k;sh[4].append(d)
        for t,d,k in ops:
            if t=="НЕДОСТАЧА" and k<0:
                if sh and sh[3]>0:S2.append((tg,n,w,"А ПРОДАНО ПОСЛЕ СПИСАНИЯ (без нового прихода)",sh[0],sh[1],round(sh[2],3),round(sh[3],3),"; ".join(sh[4][:3])))
                sh=[dt,d,-k,0,[]]
        b+=sum(k for t,d,k in ops)
        if b<-0.001 and not neg:neg=[dt,b,1,ops[0][1]]
        elif b<-0.001 and neg:neg[1]=min(neg[1],b);neg[2]+=1
        elif neg and b>=-0.001:
            if neg[2]>=3 or neg[1]<-5:S2.append((tg,n,w,"ДОЛГО МИНУС НА СКЛАДЕ (продано/выдано то, чего нет)",neg[0],neg[3],round(neg[1],3),neg[2],"до "+dt))
            neg=None
    if sh and sh[3]>0:S2.append((tg,n,w,"А ПРОДАНО ПОСЛЕ СПИСАНИЯ (без нового прихода)",sh[0],sh[1],round(sh[2],3),round(sh[3],3),"; ".join(sh[4][:3])))
    if neg and (neg[2]>=3 or neg[1]<-5):S2.append((tg,n,w,"ДОЛГО МИНУС НА СКЛАДЕ (продано/выдано то, чего нет)",neg[0],neg[3],round(neg[1],3),neg[2],"до сих пор"))
    li=None
    for dt,t,d,k in L:
        if t=="ПЕРЕМЕЩ" and k>0:li=(dt,d,k)
        if t=="НЕДОСТАЧА" and li and 0<=dd(li[0],dt)<=60:S2.append((tg,n,w,"ПРИВЕЗЛИ ПЕРЕМЕЩЕНИЕМ → НЕДОСТАЧА ≤60 дн",dt,d,round(-k,3),round(li[2],3),"перемещ "+li[0]+" "+li[1][:40]))
for x in SIG:
    if x[3] in("ПЕРЕРАСХОД В ПРОИЗВОДСТВО/РАСХОДЫ","СКАЧОК СЕБЕСТОИМОСТИ ЕДИНИЦЫ","СЕБЕСТОИМОСТЬ ВЫШЕ ЦЕНЫ ЗАКУПКИ"):S2.append(x+("",))
G2=C.Counter((x[0],x[3]) for x in S2)
for k,v in sorted(G2.items()):print(k,v,"| кол",round(sum(abs(x[6]) for x in S2 if (x[0],x[3])==k and isinstance(x[6],(int,float)))))
TOP=sorted([x for x in S2 if x[3].startswith("А ПРОДАНО")],key=lambda x:-x[7])[:12]
for x in TOP:print(" ",x[0],x[1][:34],"|",x[2][:18],"| спис",x[4],x[6],"| продано",x[7])
fn=r"D:\anescom_edo\data\reports\inv26_signals.csv"
with open(fn,"w",encoding="utf-8-sig",newline="") as fh:
    w=csv.writer(fh,delimiter=";");w.writerow(["Фирма","Товар","Склад","Сигнал","Дата","Документ","Кол-во/цена","Показатель 2","Подробно"])
    for x in sorted(S2,key=lambda x:(x[3],x[0],x[1])):w.writerow(list(x)+[""]*(9-len(x)))
print("CSV",fn,len(S2))
