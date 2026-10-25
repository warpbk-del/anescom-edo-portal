import collections as C
P=[r for r in SP if r["doc"]=="ПроизводствоБезЗаказа"]
for dp in ("Участок ламинации","Участок полимерной покраски","Основное"):
    o=[r for r in P if r["dep"].startswith(dp) and r["ts"]=="ВыходныеИзделия"];m=[r for r in P if r["dep"].startswith(dp) and r["ts"]!="ВыходныеИзделия"]
    print("==",dp,"dok",len({r["ref"] for r in o}),"vyhod",C.Counter(r["e"][:6] for r in o).most_common(3),round(sum(r["q"] for r in o)))
    g=C.defaultdict(float)
    for r in m:g[(r["n"][:34],r["e"][:5])]+=r["q"]
    for k,v in sorted(g.items(),key=lambda x:-x[1])[:7]:print("  ",round(v),k)
v=[r for r in SP if r["doc"].startswith("Внутр")];g=C.defaultdict(float)
for r in v:g[(r["dep"][:14],r["n"][:30],r["e"][:5])]+=r["q"]
print("== VnutrPotr",len(v))
for k,x in sorted(g.items(),key=lambda x:-x[1])[:8]:print("  ",round(x),k)
