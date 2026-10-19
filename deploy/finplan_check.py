"""Проверка вкладки «Фин. план» на сервере (из D:\\anescom_edo): расчёт и шаблон без входа на портал."""
import sqlite3, sys, time, types
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")
from app import finplan as F, dashboards as D, analytics as A

D.templates.env.globals["edo_me"] = lambda r: types.SimpleNamespace(as_banner=False, admin=True, initial="П", name="Проверка",
                                                                     role="админ", role_key="admin")
tpl = D.templates.env.get_template("dash_finplan.html")
for y in (2026, 2025, 2027):
    t = time.time()
    d = F.build_finplan.uncached(y, "", False)
    if d.get("empty"):
        print(y, "ПУСТО — нет an_fin_fact"); continue
    T = d["T"]
    h = tpl.render(request=None, brand="", base="", p="month", org="", branch="", d="", nav=D.NAV, tab="finplan",
                   page_title="Фин. план", show_branch=False, data=d, money=D.money, num=D.num, years=F.YEARS + [2027],
                   opex=False, can_edit=True, msg="", last_local="", human_date=str)
    print(y, "план", round(T["plan"] / 1e6, 1), "факт", round(T["fact"] / 1e6, 1), "исп.%", T["exec"] and round(T["exec"]),
          "бел/вт", round(T["white"] / 1e6), round(T["second"] / 1e6), "ФОТ/налоги:", d["src"],
          f"{time.time() - t:.1f} с, страница {len(h) // 1024} КБ")
    for r in d["rows"]:
        print("   ", r["name"], round(r["plan"] / 1e6, 1), round(r["fact"] / 1e6, 1), r["light"])
c = sqlite3.connect(str(A.DB_PATH))
print("Статьи ДДС 1С, расход 2025 (топ-25) → код фин. плана:")
for a, s in c.execute("SELECT article, SUM(sum) s FROM an_cashflow WHERE direction='out' AND date LIKE '2025%' "
                      "GROUP BY article ORDER BY s DESC LIMIT 25"):
    print("   ", round(s / 1e6, 1), a, "→", F.onec_article(a) or "")
