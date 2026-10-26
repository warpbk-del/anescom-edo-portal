QK='ВЫБРАТЬ ВКИ.Наименование КАК Нм, ВКИ.ИмяПредопределенныхДанных КАК Пр, ВКИ.Родитель.Наименование КАК Рд, ВКИ.ЭтоГруппа КАК Гр, ВКИ.ПометкаУдаления КАК Пм, ВКИ.Используется КАК Исп ИЗ Справочник.ВидыКонтактнойИнформации КАК ВКИ'
def KI(conn):
    qq=conn.NewObject('Запрос',QK); out=[]; s=qq.Выполнить().Выбрать()
    while s.Следующий(): out.append(dict(r=s.Рд or '',n=s.Нм,p=s.Пр or '',g=s.Гр,d=s.Пм,u=s.Исп))
    return out
A=KI(ib); V=KI(AVc)
print('AN',len(A),'del',sum(x['d'] for x in A),'AV',len(V),'del',sum(x['d'] for x in V))
from collections import Counter
c=Counter((x['r'],x['n']) for x in A); dup=[k for k,v in c.items() if v>1]
print('DUPS',len(dup)); [print('D',k[0][:30],'|',k[1][:40],'x',c[k]) for k in dup[:40]]
vs={(x['r'],x['n']) for x in V}
extra=[x for x in A if (x['r'],x['n']) not in vs]
print('ONLY_AN',len(extra)); [print('E',x['r'][:28],'|',x['n'][:40],'|',x['p'][:25],'del' if x['d'] else '','use' if x['u'] else 'NOUSE') for x in extra[:60]]
