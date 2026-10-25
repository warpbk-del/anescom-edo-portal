# Чтение (21-17): «круговые» перемещения в месяце — тот же товар A→B и B→A (в т.ч. через третий склад) — тормозят расчёт себестоимости
from collections import defaultdict
Н = globals().get("MONTH", datetime.datetime(2025, 7, 1))
К = datetime.datetime(Н.year + (Н.month == 12), Н.month % 12 + 1, 1) - datetime.timedelta(seconds=1)
rows = q("""ВЫБРАТЬ Т.Ссылка КАК Д, Т.Ссылка.СкладОтправитель КАК О, Т.Ссылка.СкладПолучатель КАК П, Т.Номенклатура КАК Н, Т.Количество КАК К,
  ВЫБОР КОГДА Т.Ссылка.Комментарий ПОДОБНО "%аудит 24.10.2026%" ТОГДА 1 ИНАЧЕ 0 КОНЕЦ КАК Аудит
 ИЗ Документ.ПеремещениеТоваров.Товары КАК Т ГДЕ Т.Ссылка.Проведен И Т.Ссылка.Дата МЕЖДУ &Н И &К""", Н=Н, К=К)
print("строк перемещений за месяц:", len(rows), "из них аудит:", sum(r["Аудит"] for r in rows))
edges = defaultdict(set)   # товар -> {(откуда, куда)}
docs = defaultdict(list)
for r in rows:
    e = (s(r["О"]), s(r["П"])); n = s(r["Н"])
    edges[n].add(e); docs[(n,) + e].append((s(r["Д"])[-35:], r["Аудит"]))
cyc = []
for n, es in edges.items():
    g = defaultdict(set)
    for a, b in es: g[a].add(b)
    # поиск цикла DFS
    def has_cycle():
        color = {}
        def dfs(u):
            color[u] = 1
            for v in g[u]:
                if color.get(v) == 1 or (color.get(v) is None and dfs(v)): return True
            color[u] = 2; return False
        return any(color.get(u) is None and dfs(u) for u in list(g))
    if has_cycle(): cyc.append(n)
print("товаров с круговыми перемещениями:", len(cyc))
for n in cyc[:40]:
    print(" ", n[:50], "|", "; ".join(f"{a[:18]}→{b[:18]} {[d for d in docs[(n, a, b)]][:2]}" for a, b in edges[n])[:300])
