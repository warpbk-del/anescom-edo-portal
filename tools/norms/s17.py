print("== 8110 Dt 2026 po statje x KorSchet, mln")
D17=C.Counter()
for r in Q(f'ВЫБРАТЬ О.Субконто1 С1,О.Субконто2 С2,О.КорСчет.Код К,О.СуммаОборотДт Д ИЗ РегистрБухгалтерии.{RG}.Обороты(&Н,&К,,Счет.Код ПОДОБНО "811%",,,,) О',Н=DT.datetime(2026,1,1),К=K):
    a=S(r["С1"]);b=S(r["С2"])
    if a.startswith("Материал"):b="(материалы)"
    D17[(b[:28],S(r["К"]))]+=float(r["Д"] or 0)
for k,v in D17.most_common(16):print(round(v/1e6,2),*k)
print("== AMORT tolko 242x 2026 po OS (top), KorSchet")
A17=C.Counter();K17=C.Counter()
for r in Q(f'ВЫБРАТЬ О.Субконто1 С1,О.КорСчет.Код К,О.СуммаОборотКт Кт ИЗ РегистрБухгалтерии.{RG}.Обороты(&Н,&К,,Счет.Код ПОДОБНО "242%",,,,) О',Н=DT.datetime(2026,1,1),К=K):
    v=float(r["Кт"] or 0);A17[S(r["С1"])[:40]]+=v;K17[S(r["К"])]+=v
print({k:round(v/1e6,2) for k,v in K17.items()},"itogo",round(sum(K17.values())/1e6,2))
print(" ; ".join(f"{n} {v/1e6:.2f}" for n,v in A17.most_common(12)))
