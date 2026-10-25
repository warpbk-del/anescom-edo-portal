import csv,statistics as St
N5,K6=DT.datetime(2025,1,1),DT.datetime(2026,10,31,23,59,59)
def mkQ(cn):
    def f(t,**p):
        z=cn.NewObject("Запрос");z.Текст=t
        for k,v in p.items():z.УстановитьПараметр(k,v)
        r=z.Выполнить();cols=[r.Колонки.Получить(i).Имя for i in range(r.Колонки.Количество())];s=r.Выбрать();o=[]
        while s.Следующий():o.append({c:getattr(s,c) for c in cols})
        return o
    return f
def typ(d):
    for k,v in (("Реализация","ПРОДАЖА"),("Возврат","ВОЗВРАТ"),("Перемещение","ПЕРЕМЕЩ"),("Списание недостач","НЕДОСТАЧА"),("Оприходование излишков","ИЗЛИШЕК"),("Пересортица","ПЕРЕСОРТ"),("Приобретение","ПОКУПКА"),("Поступление от переработ","ОТ_ПЕРЕРАБ"),("Передача сырья","ДАВАЛЬЧ"),("Производство","ПРОИЗВОДСТВО"),("Списание на расходы","СПИС_РАСХОД"),("Внутреннее потребление","СПИС_РАСХОД"),("Сборка","СБОРКА"),("Передача материалов","В_ПРОИЗВ"),("Отчет переработчика","ОТЧ_ПЕРЕРАБ"),("Ввод остатков","ВВОД_ОСТ")):
        if d.startswith(k):return v
    return d.split(" ")[0][:14]
SIG=[];DOSS={}
def dossier(tag,cn,names):
    q=mkQ(cn);s=cn.String;M=cn.NewObject("Массив")
    for n in names:M.Добавить(n)
    R=q('ВЫБРАТЬ Н.Ссылка Р ИЗ Справочник.Номенклатура Н ГДЕ Н.Наименование В (&М) И НЕ Н.ЭтоГруппа',М=M);A=cn.NewObject("Массив")
    for r in R:A.Добавить(r["Р"])
    op=C.Counter()
    for r in q('ВЫБРАТЬ Т.Номенклатура Н,Т.Склад С,Т.ВНаличииОстаток К ИЗ РегистрНакопления.ТоварыНаСкладах.Остатки(&Д,Номенклатура В (&А)) Т',Д=N5,А=A):op[(s(r["Н"]),s(r["С"]))]+=float(r["К"] or 0)
    mv=q('''ВЫБРАТЬ Т.Период П,Т.Регистратор Р,Т.Склад С,Т.Номенклатура Н,СУММА(ВЫБОР КОГДА Т.ВидДвижения=ЗНАЧЕНИЕ(ВидДвиженияНакопления.Приход) ТОГДА Т.ВНаличии ИНАЧЕ -Т.ВНаличии КОНЕЦ) К
 ИЗ РегистрНакопления.ТоварыНаСкладах Т ГДЕ Т.Активность И Т.Номенклатура В (&А) И Т.Период МЕЖДУ &Н И &К СГРУППИРОВАТЬ ПО Т.Период,Т.Регистратор,Т.Склад,Т.Номенклатура''',А=A,Н=N5,К=K6)
    TL=C.defaultdict(list);RF={}
    for r in mv:
        d=s(r["Р"]);TL[(s(r["Н"]),s(r["С"]))].append((str(r["П"])[:10],typ(d),d,float(r["К"] or 0)));RF[d]=r["Р"]
    print(tag,"tovarov",len(R),"dvizhenij",len(mv),"sklad-tovar",len(TL))
    for (n,w),L in TL.items():
        L.sort(key=lambda x:x[0]);b=op[(n,w)];lastshort=None;lastin=None
        DOSS[(tag,n,w)]=(op[(n,w)],L)
        for dt,t,d,k in L:
            b+=k
            if k<0 and b<-0.001 and t not in("НЕДОСТАЧА","ПЕРЕСОРТ"):SIG.append((tag,n,w,"РАСХОД ПРИ ОТРИЦ.ОСТАТКЕ",dt,d,k,round(b,3)))
            if t=="НЕДОСТАЧА":lastshort=(dt,d,-k)
            if t=="ПРОДАЖА" and lastshort and dt>=lastshort[0]:SIG.append((tag,n,w,"ПРОДАЖА ПОСЛЕ СПИСАНИЯ НЕДОСТАЧИ",dt,d,k,"недост "+lastshort[0]+" "+str(round(lastshort[2],2))))
            if t=="ПЕРЕМЕЩ" and k>0:lastin=(dt,d,k)
            if t=="НЕДОСТАЧА" and lastin and lastin[0]>=str(DT.date(2025,1,1)):SIG.append((tag,n,w,"НЕДОСТАЧА ПОСЛЕ ПЕРЕМЕЩЕНИЯ НА СКЛАД",dt,d,k,"пришло "+lastin[0]+" "+str(round(lastin[2],2))))
    # перерасход в производство: месячный расход vs медиана
    PM=C.defaultdict(C.Counter)
    for (n,w),L in TL.items():
        for dt,t,d,k in L:
            if t in("ПРОИЗВОДСТВО","СПИС_РАСХОД","В_ПРОИЗВ","СБОРКА") and k<0:PM[n][dt[:7]]+=-k
    for n,m in PM.items():
        v=[x for x in m.values() if x>0]
        if len(v)>=3:
            md=St.median(v)
            for mo,x in m.items():
                if x>2.5*md and x-md>10:SIG.append((tag,n,"","ПЕРЕРАСХОД В ПРОИЗВОДСТВО/РАСХОДЫ",mo,"",-x,"медиана "+str(round(md,1))))
    # себестоимость единицы по месяцам (бухучёт 13xx, Кт)
    RG_=cn.Метаданные.РегистрыБухгалтерии.Получить(0).Имя;U=C.defaultdict(dict);PU=C.defaultdict(list)
    for r in q(f'ВЫБРАТЬ О.Период П,О.Субконто1 Н,О.КорСчет.Код К,О.КоличествоОборотДт КД,О.СуммаОборотДт СД,О.КоличествоОборотКт КК,О.СуммаОборотКт СК ИЗ РегистрБухгалтерии.{RG_}.Обороты(&Н,&К,Месяц,Счет.Код ПОДОБНО "13%",,Субконто1 В (&А),,) О',Н=N5,К=K6,А=A):
        n=s(r["Н"]);mo=str(r["П"])[:7];kk=float(r["КК"] or 0);sk=float(r["СК"] or 0)
        if kk>0 and not s(r["К"]).startswith("13"):x=U[n].setdefault(mo,[0,0]);x[0]+=kk;x[1]+=sk
        if s(r["К"]).startswith("33") and float(r["КД"] or 0)>0:PU[n].append(float(r["СД"])/float(r["КД"]))
    for n,m in U.items():
        pp=St.median(PU[n]) if PU[n] else None;prev=None
        for mo in sorted(m):
            c=m[mo][1]/m[mo][0] if m[mo][0] else 0
            if prev and c>prev*1.3 and c-prev>1:SIG.append((tag,n,"","СКАЧОК СЕБЕСТОИМОСТИ ЕДИНИЦЫ",mo,"",round(c,2),"было "+str(round(prev,2))))
            if pp and c>pp*1.3 and c-pp>1:SIG.append((tag,n,"","СЕБЕСТОИМОСТЬ ВЫШЕ ЦЕНЫ ЗАКУПКИ",mo,"",round(c,2),"закупка "+str(round(pp,2))))
            prev=c if c else prev
    return RF
NAMES={e["n"] for e in EV}
RFA=dossier("AN",ANc,[n for n in NAMES])
RFV=dossier("AV",AVc,[n for n in NAMES])
G=C.Counter((x[0],x[3]) for x in SIG)
for k,v in sorted(G.items()):print(k,v)
fn=r"D:\anescom_edo\data\reports\inv26_signals.csv"
with open(fn,"w",encoding="utf-8-sig",newline="") as fh:
    w=csv.writer(fh,delimiter=";");w.writerow(["Фирма","Товар","Склад","Сигнал","Дата/месяц","Документ","Кол-во/цена","Подробно"])
    for x in SIG:w.writerow(x)
fn2=r"D:\anescom_edo\data\reports\inv26_dossier.csv"
with open(fn2,"w",encoding="utf-8-sig",newline="") as fh:
    w=csv.writer(fh,delimiter=";");w.writerow(["Фирма","Товар","Склад","Дата","Операция","Документ","Кол-во","Остаток после"])
    for (tg,n,wh),(o,L) in sorted(DOSS.items()):
        b=o;w.writerow([tg,n,wh,"2025-01-01","ОСТАТОК НАЧ","",o,o])
        for dt,t,d,k in L:b+=k;w.writerow([tg,n,wh,dt,t,d,round(k,3),round(b,3)])
print("CSV:",fn,len(SIG),"|",fn2)
