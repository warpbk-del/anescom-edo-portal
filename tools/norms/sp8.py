import collections as C
KW=[("упак","РУКАВ","СКОТЧ","СТРЕЙЧ","ПОЛИЭТИЛ","КАРТОН","ЛЕНТ","МЕШ","ПАКЕТ"),("энерг","ЭЛЕКТРО","ГАЗ ","ГАЗ(","ГАЗ,","ТЕПЛО","ВОДА"),("топл","БЕНЗИН","ДИЗЕЛ"),("расх","НАЖДАК","ПЕРЧАТ","РАСТВОР","ВЕТОШ","ДИСК","ЩЕТК","ОЧИСТ")]
def kc(n):
    u=n.upper()
    for t in KW:
        if any(w in u for w in t[1:]):return t[0]
g=C.defaultdict(lambda:[0,""])
for r in SP:
    if r["ts"]=="ВыходныеИзделия":continue
    k=kc(r["n"])
    if not k:continue
    a=("ЛАМ" if r["dep"].startswith("Участок лам") else "ПОКР" if r["dep"].startswith("Участок полим") else "ОСН")
    x=g[(k,a,r["d"][:4],r["n"][:26],r["e"][:4])];x[0]+=r["q"]
for key,v in sorted(g.items(),key=lambda x:(x[0][0],x[0][1],x[0][2],-x[1][0])):print(*key,round(v[0]),sep="|")
