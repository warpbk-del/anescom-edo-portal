import collections as C,datetime as DT
AVc=IB_POOL[r"D:\Base\1C\AVTOKOMP_FIX"][0];RG=AVc.Метаданные.РегистрыБухгалтерии.Получить(0).Имя
z=AVc.NewObject("Запрос");z.Текст=f"""ВЫБРАТЬ О.Период КАК П,О.Счет.Код КАК С,О.КорСчет.Код КАК К,О.Субконто1 КАК С1,О.Субконто2 КАК С2,О.СуммаОборотДт КАК Д
ИЗ РегистрБухгалтерии.{RG}.Обороты(&Н,&К,Год,Счет.Код ПОДОБНО "8%",,,,) КАК О"""
z.УстановитьПараметр("Н",DT.datetime(2025,1,1));z.УстановитьПараметр("К",DT.datetime(2026,10,31,23,59,59))
sel=z.Выполнить().Выбрать();A=C.Counter();B=C.Counter()
while sel.Следующий():
    y=str(sel.П)[:4];d=float(sel.Д or 0)
    if not d:continue
    A[(y,sel.С,sel.К)]+=d;B[(y,sel.С,AVc.String(sel.С1)[:22],AVc.String(sel.С2)[:22])]+=d
print("SCHET-KOR, mln:");print(" ; ".join(f"{k[0]} {k[1]}<{k[2]} {v/1e6:.2f}" for k,v in sorted(A.items()) if v>2e5))
print("SCHET-SUBKONTO top:")
for k,v in sorted(B.items(),key=lambda x:-x[1])[:24]:print(k[0],k[1],k[2],"|",k[3],round(v/1e6,2))
