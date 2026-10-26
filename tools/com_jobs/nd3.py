os.system('cls'); from collections import Counter
PMO=[]
for t in ['Справочник.БанковскиеСчетаОрганизаций','Справочник.СтруктураПредприятия','ПланСчетов.Хозрасчетный']:
    extra=', Т.Код КАК Кд, Т.Предопределенный КАК Пд' if t.startswith('План') else ', "" КАК Кд, Т.Предопределенный КАК Пд'
    for x in q('ВЫБРАТЬ Т.Ссылка КАК Сс, Т.Наименование КАК Нм'+extra+' ИЗ '+t+' КАК Т ГДЕ Т.ПометкаУдаления'): PMO.append((t,x))
for t,x in PMO:
    a=ib.NewObject('Массив'); a.Добавить(x['Сс']); tb=ib.НайтиПоСсылкам(a)
    c=Counter(tb.Получить(i).Метаданные.ПолноеИмя() for i in range(tb.Количество()))
    c.pop(t,None); c.pop('РегистрСведений.ВерсииОбъектов',None)
    print('R',t.split('.')[-1][:14],x['Кд'],x['Нм'][:30],'pred' if x['Пд'] else '','|',sum(c.values()),c.most_common(4),flush=True)
