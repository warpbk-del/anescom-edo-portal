AR={S(r["Н"]):float(r["ПЧ"])/float(r["ПЗ"] or 1) for r in q13 if r["ПИ"] and float(r["ПЧ"] or 0)>0}
Y14=C.defaultdict(lambda:[0,0,C.Counter(),0]);DD=C.defaultdict(lambda:[0,0,0])
for r in SP:
    if r["doc"]!="ПроизводствоБезЗаказа" or not r["dep"].startswith("Участок полим"):continue
    y=r["d"][:4];d=DD[r["ref"]]
    if r["ts"]=="ВыходныеИзделия":
        a=AR.get(r["n"])
        if a:Y14[y][0]+=r["q"]*a;d[0]+=r["q"]*a
        else:Y14[y][2][r["e"][:4]]+=r["q"];d[2]+=1
    elif mk(r["n"])=="paint":Y14[y][1]+=r["q"];d[1]+=r["q"]
for y,v in sorted(Y14.items()):print(y,"m2 po spravochniku",round(v[0]),"| kraska kg",round(v[1]),"| g/m2",round(v[1]/v[0]*1000) if v[0] else 0,"| bez ploshadi:",dict(v[2]))
g=[d[1]/d[0]*1000 for d in DD.values() if d[0]>0 and d[2]==0 and d[1]>0]
import statistics as St;print("dok tolko s ploshadju:",len(g),"g/m2 mediana",round(St.median(g)),"Q",[round(x) for x in St.quantiles(g,n=4)])
print("nom pokraski bez ploshadi top:",[(n[:30],round(q)) for n,q in C.Counter({r["n"]:0 for r in []}).items()])
nb=C.Counter()
for r in SP:
    if r["doc"]=="ПроизводствоБезЗаказа" and r["dep"].startswith("Участок полим") and r["ts"]=="ВыходныеИзделия" and r["n"] not in AR:nb[(r["n"][:34],r["e"][:4])]+=r["q"]
print(nb.most_common(10))
