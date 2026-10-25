print("== AMORT vse KorScheta, mln 2025/2026")
A16=C.defaultdict(lambda:[0,0]);KK=C.defaultdict(lambda:[0,0])
for r in Q(f'ВЫБРАТЬ О.Период П,О.Субконто1 С1,О.КорСчет.Код К,О.СуммаОборотКт Кт ИЗ РегистрБухгалтерии.{RG}.Обороты(&Н,&К,Год,Счет.Код ПОДОБНО "24%",,,,) О',Н=N,К=K):
    i=0 if str(r["П"])[:4]=="2025" else 1;v=float(r["Кт"] or 0)
    if not v:continue
    A16[S(r["С1"])[:44]][i]+=v;KK[S(r["К"])][i]+=v
print({k:(round(a/1e6,2),round(b/1e6,2)) for k,(a,b) in KK.items()})
print("OS:",len(A16),"itogo",round(sum(v[0] for v in A16.values())/1e6,2),round(sum(v[1] for v in A16.values())/1e6,2))
for n,v in sorted(A16.items(),key=lambda x:-x[1][1]-x[1][0])[:36]:print(f"{v[0]/1e6:6.2f} {v[1]/1e6:6.2f} {n}")
print("== 8410 Proizv.rashody 2026 rasshifrovka")
P16=C.Counter()
for r in Q(f'ВЫБРАТЬ О.Субконто1 С1,О.Субконто2 С2,О.КорСчет.Код К,О.КорСубконто1 КС,О.СуммаОборотДт Д ИЗ РегистрБухгалтерии.{RG}.Обороты(&Н,&К,,Счет.Код ПОДОБНО "84%",,,,) О',Н=DT.datetime(2026,1,1),К=K):
    t=S(r["С1"])+" "+S(r["С2"])
    if "АРЕНД" in t.upper():continue
    P16[(t[:34],S(r["К"]),S(r["КС"])[:28])]+=float(r["Д"] or 0)
for k,v in P16.most_common(14):print(round(v/1e3),"тыс |",*k)
