S3=[]
for (tg,n,w),(o,L) in DOSS.items():
    days=C.OrderedDict()
    for dt,t,d,k in L:days.setdefault(dt,[]).append((t,d,k))
    b=o;sh=None
    def fl():
        if sh and sh[3]>sh[5]+0.001:S3.append((tg,n,w,sh[0],sh[1],round(sh[2],3),round(sh[5],3),round(sh[3],3),round(min(sh[2],sh[3]-max(sh[5],0)),3),"; ".join(sh[4][:3])))
    for dt,ops in days.items():
        for t,d,k in ops:
            if sh and dt>sh[0] and k>0 and t in INS:fl();sh=None
            if sh and t in("ПРОДАЖА","СПИС_РАСХОД","ПРОИЗВОДСТВО","В_ПРОИЗВ","ПЕРЕМЕЩ","СБОРКА") and k<0 and dt>=sh[0]:sh[3]+=-k;sh[4].append(t+" "+d[:34])
        b+=sum(k for t,d,k in ops)
        for t,d,k in ops:
            if t=="НЕДОСТАЧА" and k<0:fl();sh=[dt,d,-k,0,[],b]
    fl()
print("СПИСАЛИ, А ПОТОМ ОТГРУЗИЛИ БОЛЬШЕ ОСТАТКА:",C.Counter(x[0] for x in S3),"| ложно списано ед.:",{f:round(sum(x[8] for x in S3 if x[0]==f)) for f in("AN","AV")})
for x in sorted(S3,key=lambda x:-x[8])[:14]:print(" ",x[0],x[1][:32],"|",x[2][:16],"|",x[3],"спис",x[5],"ост.после",x[6],"ушло",x[7],"=> ложно",x[8])
fn=r"D:\anescom_edo\data\reports\inv26_lozhnye_spisaniya.csv"
with open(fn,"w",encoding="utf-8-sig",newline="") as fh:
    w=csv.writer(fh,delimiter=";");w.writerow(["Фирма","Товар","Склад","Дата списания","Документ списания","Списано","Остаток после списания","Отгружено/израсходовано без нового прихода","Ложно списано (товар был)","Куда ушло"])
    for x in sorted(S3,key=lambda x:-x[8]):w.writerow(x)
print("CSV",fn,len(S3))
