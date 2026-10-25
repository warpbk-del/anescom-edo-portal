PN=["ANESCOM","QAZAQGAZ","Энергосистема","Баканов","Арсенал Ойл","Тобыл","PetroRetail","Этус"]
for reg in ("РасчетыСПоставщиками","РасчетыСКлиентами"):
    m=AVc.Метаданные.РегистрыНакопления.Найти(reg)
    if m is None:print(reg,"NET");continue
    dims=[m.Измерения.Получить(i).Имя for i in range(m.Измерения.Количество())];res=[m.Ресурсы.Получить(i).Имя for i in range(m.Ресурсы.Количество())]
    print("==",reg,"dims",dims,"res",res)
    sel=",".join(f"О.{d} {d}" for d in dims)+","+",".join(f"О.{r}Остаток {r}" for r in res)
    rows=Q(f'ВЫБРАТЬ {sel} ИЗ РегистрНакопления.{reg}.Остатки(&Д,) О',Д=DT.datetime(2026,10,31,23,59,59))
    for r in rows:
        an=S(r[dims[0]])
        if any(p.lower() in an.lower() for p in PN):print("  ",an[:40],"|",{d:S(r[d])[:34] for d in dims[1:]},"|",{x:round(float(r[x] or 0)) for x in res if float(r[x] or 0)})
