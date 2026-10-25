import collections as C,datetime as DT
AVc=IB_POOL[r"D:\Base\1C\AVTOKOMP_FIX"][0];RG=AVc.Метаданные.РегистрыБухгалтерии.Получить(0).Имя
def Q(t,**p):
    z=AVc.NewObject("Запрос");z.Текст=t
    for k,v in p.items():z.УстановитьПараметр(k,v)
    r=z.Выполнить();cols=[r.Колонки.Получить(i).Имя for i in range(r.Колонки.Количество())];s=r.Выбрать();o=[]
    while s.Следующий():o.append({c:getattr(s,c) for c in cols})
    return o
S=lambda v:AVc.String(v)
N,K=DT.datetime(2025,1,1),DT.datetime(2026,10,31,23,59,59)
print("== AMORT po OS (Kt 24xx -> Dt 8xxx), mln 2025/2026")
A=C.defaultdict(lambda:[0,0])
for r in Q(f'ВЫБРАТЬ О.Период П,О.Субконто1 С1,О.КорСчет.Код К,О.СуммаОборотКт Кт ИЗ РегистрБухгалтерии.{RG}.Обороты(&Н,&К,Год,Счет.Код ПОДОБНО "24%",,,КорСчет.Код ПОДОБНО "8%",) О',Н=N,К=K):
    A[S(r["С1"])[:38]][0 if str(r["П"])[:4]=="2025" else 1]+=float(r["Кт"] or 0)
for n,v in sorted(A.items(),key=lambda x:-sum(x[1]))[:18]:print(f"{v[0]/1e6:.2f}/{v[1]/1e6:.2f}",n)
print("== ARENDA/GAZ/ELEKTR po mes (8310,8410), tys")
G=C.defaultdict(C.Counter)
for r in Q(f'ВЫБРАТЬ О.Период П,О.Субконто1 С1,О.Субконто2 С2,О.КорСубконто1 КС,О.СуммаОборотДт Д ИЗ РегистрБухгалтерии.{RG}.Обороты(&Н,&К,Месяц,Счет.Код ПОДОБНО "8310%" ИЛИ Счет.Код ПОДОБНО "8410%",,,,) О',Н=N,К=K):
    t=(S(r["С1"])+" "+S(r["С2"])).upper();k="газ" if "ГАЗ" in t else "свет" if "ЭЛЕКТР" in t else "аренда" if "АРЕНД" in t else None
    if k:G[k][str(r["П"])[2:7]]+=float(r["Д"] or 0)
for k,v in G.items():print(k,{m:round(x/1e3) for m,x in sorted(v.items())})
R=C.Counter()
for r in Q(f'ВЫБРАТЬ О.КорСубконто1 КС,О.СуммаОборотДт Д ИЗ РегистрБухгалтерии.{RG}.Обороты(&Н,&К,,Счет.Код ПОДОБНО "8410%",,,КорСчет.Код ПОДОБНО "33%",) О',Н=N,К=K):R[S(r["КС"])[:30]]+=float(r["Д"] or 0)
print("8410 postavshiki:",{k:round(v/1e6,2) for k,v in R.most_common(6)})
print("== PERIMETR: rekvizity Nomenklatury")
md=AVc.Метаданные.Справочники.Номенклатура;print([md.Реквизиты.Получить(i).Имя for i in range(md.Реквизиты.Количество()) if any(w in md.Реквизиты.Получить(i).Имя.upper() for w in ("ПЕРИМ","ПЛОЩ","ДЛИН","ШИРИН","РАЗВ"))])
try:
    for r in Q('ВЫБРАТЬ Д.Свойство.Наименование Н,КОЛИЧЕСТВО(*) Ч ИЗ Справочник.Номенклатура.ДополнительныеРеквизиты Д СГРУППИРОВАТЬ ПО Д.Свойство.Наименование'):print(" dop:",S(r["Н"]),r["Ч"])
except Exception as e:print("dop err",str(e)[-80:])
