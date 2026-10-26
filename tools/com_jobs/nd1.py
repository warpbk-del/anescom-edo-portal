os.system('cls')
rs=ib.РегистрыСведений.НеудаленныеОбъекты.СоздатьНаборЗаписей(); rs.Прочитать()
print('ND total',rs.Количество())
from collections import Counter
C=Counter(); ND=[]
for r in rs:
    o=r.Объект
    try: t=o.Метаданные().ПолноеИмя(); nm=str(o)[:40]; pm=o.ПометкаУдаления
    except Exception as e: t='?'; nm=str(e)[-30:]; pm='?'
    C[t]+=1; ND.append((t,nm,pm,o))
for k,v in C.most_common(): print('T',k,v)
for t,nm,pm,o in ND[:60]: print('O',t.split('.')[-1][:25],'|',nm,'| пометка',pm)
