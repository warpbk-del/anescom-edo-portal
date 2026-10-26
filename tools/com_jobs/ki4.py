KEEP=('Адрес на казахском языке','АдресКаз')
R2=q('ВЫБРАТЬ ВКИ.Ссылка КАК Сс, ВКИ.Наименование КАК Нм, ВКИ.ЭтоГруппа КАК Гр ИЗ Справочник.ВидыКонтактнойИнформации КАК ВКИ ГДЕ НЕ ВКИ.Предопределенный')
DRY=globals().get('DRY',True); dn=0; kept=[]
for x in sorted(R2,key=lambda x:x['Гр']):
    if x['Нм'] in KEEP: kept.append(x['Нм']); continue
    a=ib.NewObject('Массив'); a.Добавить(x['Сс']); t=ib.НайтиПоСсылкам(a)
    refs=[r for r in [t.Получить(i) for i in range(t.Количество())] if r.Метаданные.ПолноеИмя()not in ('Справочник.ВидыКонтактнойИнформации','РегистрСведений.ВерсииОбъектов')]
    if refs:
        kept.append(x['Нм']+' REF:'+str(len(refs))+' '+str(refs[0].Метаданные.ПолноеИмя())); continue
    if not DRY:
        ob=x['Сс'].ПолучитьОбъект(); ob.ОбменДанными.Загрузка=True; ob.Удалить()
    dn+=1
print('DRY' if DRY else 'WRITE','deleted',dn,'kept',kept)
if not DRY: log(f'21-31 виды КИ: удалено {dn} лишних видов; оставлено {kept}')
