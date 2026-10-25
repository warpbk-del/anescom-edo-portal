import collections as C,statistics as S,re
def cat(n):
    u=n.upper();t=next((w for w in ("ШТАПИК","ИМПОСТ","СТВОРКА","РАМА","ПОРОГ","Z","Т-") if w in u),"ПРОЧ")
    sr=next((w for w in ("HELIOS","BAULINE","STANDART") if w in u),"")
    mm=re.search(r"(\d\d)\s*ММ",u);return t+" "+sr+" "+(mm.group(1) if mm else "")
def mk(n):
    u=n.upper()
    if "ПЛЕНКА ПВХ" in u:return "film"
    if "ЗАЩИТ" in u:return "prot"
    if "КЛЕЙ" in u:return "glue"
    if "ПРАЙМЕР" in u or "ГРУНТ" in u or "ОЧИСТ" in u:return "prim"
    if "ПК " in u or "КРАСК" in u or "ПОРОШ" in u:return "paint"
    return None
D=C.defaultdict(lambda:{"o":C.Counter(),"oq":0,"oe":set(),"m":C.Counter()})
for r in SP:
    if r["doc"]!="ПроизводствоБезЗаказа":continue
    d=D[(r["dep"][:9],r["ref"])]
    if r["ts"]=="ВыходныеИзделия":d["o"][cat(r["n"])]+=r["q"];d["oq"]+=r["q"];d["oe"].add(r["e"][:4])
    else:
        k=mk(r["n"])
        if k:d["m"][k]+=r["q"]
R=C.defaultdict(lambda:C.defaultdict(list));T=C.defaultdict(lambda:[0,C.Counter()])
for (dp,ref),d in D.items():
    if not d["oq"]:continue
    T[dp][0]+=d["oq"];T[dp][1].update(d["m"])
    if len(d["o"])==1 and len(d["oe"])==1:
        k=dp+"|"+list(d["o"])[0]+"|"+list(d["oe"])[0]
        for mt in ("film","prot","glue","prim","paint"):R[k][mt].append(d["m"][mt]/d["oq"])
        R[k]["n"].append(d["oq"])
for k in sorted(R,key=lambda k:-sum(R[k]["n"]))[:16]:
    x=R[k];print(k[:40],"dok",len(x["n"]),"vyp",round(sum(x["n"])),"|",*[f"{m}={S.median(x[m]):.3f}" for m in ("film","prot","glue","prim","paint") if any(x[m])])
for dp,(q,m) in T.items():print("TOT",dp,round(q),{k:round(v) for k,v in m.items()})
