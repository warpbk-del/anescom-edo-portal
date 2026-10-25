import collections as C,statistics as S,re
def fam(n):
    u=n.upper()
    if "УГОЛОК" in u:return "уголок"
    m=re.search(r"\b([FWD]\d\d)",u.replace("А","A"));return m.group(1) if m else "проч"
X=C.defaultdict(lambda:{"L":0,"K":0,"O":0,"f":C.Counter(),"paint":0,"prot":0})
for r in SP:
    if r["doc"]!="ПроизводствоБезЗаказа" or not r["dep"].startswith("Участок полим"):continue
    d=X[r["ref"]];u=r["n"].upper();e=r["e"][:3].lower()
    if r["ts"]=="ВыходныеИзделия":
        if e=="пог":d["L"]+=r["q"];d["f"][fam(u)]+=r["q"]
        elif "6М" in u.replace(" ",""):d["L"]+=6*r["q"];d["f"][fam(u)]+=6*r["q"]
        elif e=="ком":d["K"]+=r["q"]
        else:d["O"]+=r["q"]
    else:
        k=mk(r["n"])
        if k in("paint","prot"):d[k]+=r["q"]
P=[d for d in X.values() if d["L"]>0 and d["K"]==0 and d["O"]==0]
Q=lambda v:(round(S.median(v),3),round(S.quantiles(v,n=4)[0],3),round(S.quantiles(v,n=4)[2],3)) if len(v)>3 else [round(x,3) for x in v]
print("PROFIL dok",len(P),"pm",round(sum(d["L"] for d in P)),"paint/pm",Q([d["paint"]/d["L"] for d in P]),"prot/pm",Q([d["prot"]/d["L"] for d in P]),"sum",round(sum(d["paint"] for d in P)/sum(d["L"] for d in P),3))
for f in ("F50","W65","D65","W45","уголок","проч"):
    v=[d for d in P if len(d["f"])==1 and f in d["f"]]
    if v:print(" ",f,"dok",len(v),"pm",round(sum(d["L"] for d in v)),"paint",Q([d["paint"]/d["L"] for d in v]),"prot",Q([d["prot"]/d["L"] for d in v]))
K=[d for d in X.values() if d["K"]>0 and d["L"]==0 and d["O"]==0];print("KOMPL dok",len(K),round(sum(d["K"] for d in K)),"paint/kompl",Q([d["paint"]/d["K"] for d in K]) if K else 0)
O=[d for d in X.values() if d["O"]>0 and d["L"]==0 and d["K"]==0];print("SHT dok",len(O),round(sum(d["O"] for d in O)),"paint/sht",Q([d["paint"]/d["O"] for d in O]) if O else 0)
A=[d for d in X.values() if d["L"]+d["K"]+d["O"]>0];print("VSEGO dok",len(A),"pm",round(sum(d["L"] for d in A)),"kompl",round(sum(d["K"] for d in A)),"sht",round(sum(d["O"] for d in A)),"paint",round(sum(d["paint"] for d in A)),"prot",round(sum(d["prot"] for d in A)))
