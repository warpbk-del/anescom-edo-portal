import collections as C
def c2(n):
    u=n.upper()
    for w,k in (("ШТАПИК","штапик"),("ИМПОСТ","импост"),("СТВОРКА","створка"),("РАМА","рама")):
        if w in u:return k
    if "ДВЕР" in u or " Z" in u or " Т " in u:return "дверь"
    return "проч"
KS=["рама","створка","импост","штапик","дверь","проч"]
X=C.defaultdict(lambda:{"o":C.Counter(),"m":C.Counter(),"y":""})
for r in SP:
    if r["doc"]!="ПроизводствоБезЗаказа" or not r["dep"].startswith("Участок лам"):continue
    d=X[r["ref"]];d["y"]=r["d"][:4]
    if r["ts"]=="ВыходныеИзделия":
        if r["e"][:2].lower()=="шт":d["o"][c2(r["n"])]+=r["q"]
    else:
        k=mk(r["n"])
        if k:d["m"][k]+=r["q"]
def lsq(mt):
    n=len(KS);A=[[0.0]*n for _ in KS];b=[0.0]*n
    for d in X.values():
        v=[d["o"][k] for k in KS]
        if not any(v):continue
        for i in range(n):
            b[i]+=v[i]*d["m"][mt]
            for j in range(n):A[i][j]+=v[i]*v[j]
    for i in range(n):A[i][i]+=1e-6
    for i in range(n):
        p=A[i][i]
        for j in range(i+1,n):
            f=A[j][i]/p;b[j]-=f*b[i]
            for k in range(n):A[j][k]-=f*A[i][k]
    x=[0]*n
    for i in reversed(range(n)):x[i]=(b[i]-sum(A[i][k]*x[k] for k in range(i+1,n)))/A[i][i]
    return x
print("vyp sht:",{k:round(sum(d["o"][k] for d in X.values())) for k in KS})
for mt in("film","prot","glue","prim"):print(mt,{k:round(v,3) for k,v in zip(KS,lsq(mt))})
Y=C.defaultdict(lambda:[0,0])
for d in X.values():Y[d["y"]][0]+=sum(d["o"].values());Y[d["y"]][1]+=d["m"]["film"]
V=C.defaultdict(float)
for r in SP:
    if r["doc"].startswith("Внутр") and mk(r["n"])=="film":V[r["d"][:7]]+=r["q"]
print("PBZ po godam (sht, film):",{k:(round(a),round(b)) for k,(a,b) in Y.items()})
print("VnPotr film po mes:",{k:round(v) for k,v in sorted(V.items())})
