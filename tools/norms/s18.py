R18=C.defaultdict(lambda:[0,0,None])
for r in Q(f'ВЫБРАТЬ Т.Регистратор Р,Т.Сумма С ИЗ РегистрБухгалтерии.{RG} Т ГДЕ Т.Период МЕЖДУ &Н И &К И Т.СчетДт.Код ПОДОБНО "84%" И Т.СчетКт.Код ПОДОБНО "13%"',Н=DT.datetime(2026,1,1),К=K):
    x=R18[S(r["Р"])];x[0]+=float(r["С"] or 0);x[1]+=1;x[2]=r["Р"]
print("dokumentov",len(R18),"summa",round(sum(v[0] for v in R18.values())/1e6,2))
def ga(o,n):
    try:return S(getattr(o,n))
    except Exception:return ""
for n,v in sorted(R18.items(),key=lambda x:-x[1][0])[:20]:
    o=v[2];print(round(v[0]/1e3),"тыс |",n[:62],"| стр",v[1],"| отв:",(ga(o,"Ответственный") or ga(o,"Автор"))[:22],"| подр:",ga(o,"Подразделение")[:20],"| ком:",ga(o,"Комментарий")[:50])
