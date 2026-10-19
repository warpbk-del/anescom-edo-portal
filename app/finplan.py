"""6о. Вкладка «Фин. план» /dash/finplan (19.10.2026).

Практика FP&A: одна структура статей для плана и факта (справочник «статья → отдел (ЦФО) → город»),
план-факт по месяцам и с начала года, отклонение в ₸ и %, светофор, прогноз до конца года (rolling forecast),
БДДС с делением денег на белые и вторые.

Факт:
  • заявки на оплату Bitrix24 — таблица an_fin_fact (legacy/finplan_build.py: статья, отдел, город, белая/вторая);
  • ФОТ, налоги с ФОТ, КПН, НДС — из 1С (an_cashflow, расход), если за этот год в 1С они есть; тогда заявки
    по этим статьям за год не считаются (иначе — двойной учёт).
План:
  • 2026 — факт 2025 по статьям, городам и месяцам; IT-отдел — 13,2 млн ₸ из плана пользователя (PDF) в той же разбивке;
  • 2027 — прогноз 2026 (факт по дату заявок + остаток плана 2026);
  • годовую сумму любой статьи можно поправить на странице (админ, директор) — таблица an_fin_plan, последняя правка
    действует, разбивка по месяцам и городам сохраняется пропорционально.
Доступ: администратор, директор, бухгалтер (бухгалтер — без правки плана).
"""
import calendar
from collections import defaultdict
from datetime import date, datetime

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from . import analytics, config
from .dashboards import (MONTHS_SHORT, _last_local, _q, branch_short, cached, chart_svg, money, num, pct,
                         templates, NAV)

router = APIRouter()

YEARS = list(range(2021, date.today().year + 1))
PLAN_YEARS = (2026, 2027)
IT_PLAN_2026 = 13_200_000          # план IT-отдела на 2026 из PDF пользователя (19.10.2026)
WARN_PCT, WARN_ABS = 5.0, 1_000_000  # светофор: перерасход больше 5% и больше 1 млн ₸ — красный
CITIES = ["Актобе", "Астана", "Атырау", "Актау", "Уральск", "Костанай"]
ONEC = ("HR.01", "HR.02", "FIN.01", "FIN.02")   # из 1С, когда там есть данные за год

# статья ДДС 1С (an_cashflow.article, нижний регистр) → код фин. плана; первое совпадение
ONEC_RULES = [
    ("кпн", "FIN.01"), ("корпоратив", "FIN.01"),
    ("индивидуальн", "HR.02"), ("ипн", "HR.02"), ("опв", "HR.02"), ("пенсион", "HR.02"), ("социальн", "HR.02"),
    ("осмс", "HR.02"), ("медицинск", "HR.02"),
    ("ндс", "FIN.02"),
    ("зарплат", "HR.01"), ("заработн", "HR.01"), ("оплата труда", "HR.01"), ("оплат труда", "HR.01"),
    ("фот", "HR.01"), ("отпускн", "HR.01"), ("депонент", "HR.01"),
    ("налог", "FIN.02"),
]
EDIT_ROLES = ("admin", "director")
VIEW_ROLES = ("admin", "director", "accountant")


def onec_article(a: str):
    s = " " + (a or "").lower() + " "
    for k, code in ONEC_RULES:
        if k in s:
            return code
    return None


def city_of_branch(b: str) -> str:
    c = branch_short(b)
    for x in CITIES:
        if x in c:
            return x
    return "Прочие"


def _has(c, t):
    return bool(c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone())


# ------------------------------------------------------------------ данные
def _ref(c):
    if not _has(c, "an_fin_articles"):
        return [], {}
    depts = [dict(r) for r in _q(c, "SELECT code, name, note FROM an_fin_depts ORDER BY pos")]
    arts = {r["code"]: dict(r) for r in _q(c, "SELECT code, name, dept, section, pos FROM an_fin_articles ORDER BY pos")}
    return depts, arts


def _meta(c):
    if not _has(c, "an_fin_meta"):
        return {}
    return {r["k"]: r["v"] for r in _q(c, "SELECT k, v FROM an_fin_meta")}


def _fact(c, y: int, cutoff: str):
    """→ {(article, city, month, color): sum}, источники {article: 'b24'|'1С'} за год y (до cutoff включительно)."""
    out = defaultdict(float)
    hi = min(f"{y}-12-31", cutoff) if cutoff else f"{y}-12-31"
    onec = defaultdict(float)
    for r in _q(c, "SELECT article, branch, substr(date,6,2) m, SUM(sum) s FROM an_cashflow WHERE direction='out' "
                   "AND date BETWEEN ? AND ? GROUP BY article, branch, m", (f"{y}-01-01", hi)):
        code = onec_article(r["article"])
        if code:
            onec[(code, city_of_branch(r["branch"]), int(r["m"]))] += r["s"] or 0
    have = {k[0] for k, v in onec.items() if v}
    for r in _q(c, "SELECT article, city, month, color, SUM(sum) s FROM an_fin_fact WHERE year=? AND date<=? "
                   "GROUP BY article, city, month, color", (y, hi)):
        if r["article"] in ONEC and r["article"] in have:
            continue
        out[(r["article"], r["city"] if r["city"] in CITIES else "Прочие", r["month"], r["color"])] += r["s"]
    for (code, city, m), s in onec.items():
        if code in ONEC:
            out[(code, city, m, "white")] += s
    src = {a: ("1С" if a in have else "заявки") for a in ONEC}
    return out, src


def _edits(c, y):
    if not _has(c, "an_fin_plan"):
        return {}
    return {r["article"]: dict(r) for r in _q(c, "SELECT article, sum, who, ts FROM an_fin_plan WHERE id IN "
                                                 "(SELECT MAX(id) FROM an_fin_plan WHERE year=? GROUP BY article)", (y,))}


def _apply_edits(base, edits):
    """base {(article, city, month): sum} → с правками годовых сумм статей (пропорционально, иначе поровну по месяцам)."""
    tot = defaultdict(float)
    for (a, _c, _m), s in base.items():
        tot[a] += s
    out = defaultdict(float)
    for (a, ci, m), s in base.items():
        if a in edits:
            if tot[a]:
                out[(a, ci, m)] += s * edits[a]["sum"] / tot[a]
        else:
            out[(a, ci, m)] += s
    for a, e in edits.items():
        if not tot[a] and e["sum"]:
            for m in range(1, 13):
                out[(a, "Прочие", m)] += e["sum"] / 12
    return out


def _collapse(fact):
    out = defaultdict(float)
    for (a, ci, m, _col), s in fact.items():
        out[(a, ci, m)] += s
    return out


def _plan(c, y: int, cutoff: str, arts):
    """→ {(article, city, month): sum} для 2026 или 2027, с правками."""
    if y == 2026:
        f25, _ = _fact(c, 2025, cutoff)
        base = _collapse(f25)
        it = {k: v for k, v in base.items() if arts.get(k[0], {}).get("dept") == "IT"}
        tot = sum(it.values())
        if tot:
            for k, v in it.items():
                base[k] = v * IT_PLAN_2026 / tot
        return _apply_edits(base, _edits(c, 2026))
    if y == 2027:
        return _apply_edits(_forecast(c, 2026, cutoff, arts), _edits(c, 2027))
    return {}


def _cut(y, cutoff):
    """→ (последний месяц факта, доля этого месяца, прошедшая к дате факта) для года y."""
    if not cutoff or int(cutoff[:4]) > y:
        return 12, 1.0
    if int(cutoff[:4]) < y:
        return 0, 0.0
    d = date.fromisoformat(cutoff)
    return d.month, d.day / calendar.monthrange(d.year, d.month)[1]


def _forecast(c, y, cutoff, arts):
    """Прогноз года: факт по прошедшим месяцам + план на остаток (текущий месяц — факт + непрошедшая доля плана)."""
    fact = _collapse(_fact(c, y, cutoff)[0])
    plan = _plan(c, y, cutoff, arts) if y in PLAN_YEARS else {}
    cm, share = _cut(y, cutoff)
    out = defaultdict(float)
    for (a, ci, m), s in fact.items():
        out[(a, ci, m)] += s
    for (a, ci, m), s in plan.items():
        if m > cm:
            out[(a, ci, m)] += s
        elif m == cm:
            out[(a, ci, m)] += s * (1 - share)
    return out


def _sum(d, pred=lambda k: True):
    return sum(v for k, v in d.items() if pred(k))


def _light(fact, plan):
    dev = fact - plan
    if plan <= 0 and fact <= 0:
        return ""
    if dev > max(plan * WARN_PCT / 100, WARN_ABS):
        return "red"
    if dev > 0:
        return "warn"
    return "ok"


@cached
def build_finplan(y: int, dep: str, opex: bool):
    with analytics.conn() as c:
        depts, arts = _ref(c)
        meta = _meta(c)
        if not arts or not _has(c, "an_fin_fact"):
            return {"empty": True}
        cutoff = meta.get("fact_to", "")
        keep = (lambda a: arts.get(a, {}).get("dept") != "PUR") if opex else (lambda a: True)
        is_plan_only = y == 2027
        fact_c, src = ({}, {}) if is_plan_only else _fact(c, y, cutoff)
        fact_c = {k: v for k, v in fact_c.items() if k[0] in arts and keep(k[0])}
        fact = _collapse(fact_c)
        plan = {k: v for k, v in (_plan(c, y, cutoff, arts) if y in PLAN_YEARS else {}).items() if keep(k[0])}
        cm, share = _cut(y, cutoff)
        pfac = lambda m: 1.0 if m < cm else (share if m == cm else 0.0)   # доля плана месяца к дате факта
        # прошлый год — для сравнения
        prev_c = _collapse({k: v for k, v in _fact(c, y - 1, cutoff)[0].items() if k[0] in arts and keep(k[0])})
        if y == 2027:
            fc26 = {k: v for k, v in _forecast(c, 2026, cutoff, arts).items() if k[0] in arts and keep(k[0])}

        dept_of = lambda a: arts[a]["dept"]
        D = {d["code"]: d for d in depts}

        # по отделам
        rows = []
        for d in depts:
            k = d["code"]
            if opex and k == "PUR":
                continue
            inD = lambda key, k=k: dept_of(key[0]) == k
            py = _sum(plan, inD)
            pytd = sum(v * pfac(key[2]) for key, v in plan.items() if inD(key))
            fy = _sum(fact, inD)
            fc = fy + sum(v * (1 - pfac(key[2])) for key, v in plan.items() if inD(key))
            prev = sum(v * pfac(key[2]) for key, v in prev_c.items() if inD(key))   # прошлый год, тот же период
            if y == 2027:
                fc = _sum(fc26, inD)
            if not (py or fy or prev or fc):
                continue
            rows.append({"code": k, "name": d["name"], "plan": py, "plan_ytd": pytd, "fact": fy, "fc": fc,
                         "dev": fy - pytd, "dev_pct": pct(fy, pytd), "light": _light(fy, pytd) if py and y != 2027 else "",
                         "prev": prev, "yoy": pct(fy, prev), "growth": pct(py, fc) if y == 2027 else None})
        T = {"plan": _sum(plan), "fact": _sum(fact),
             "plan_ytd": sum(v * pfac(k[2]) for k, v in plan.items())}
        T["fc"] = (_sum(fc26) if y == 2027 else T["fact"] + sum(v * (1 - pfac(k[2])) for k, v in plan.items()))
        T["exec"] = (T["fact"] / T["plan_ytd"] * 100) if T["plan_ytd"] else None
        T["prev"] = _sum(prev_c)
        T["prev_same"] = sum(v * pfac(k[2]) for k, v in prev_c.items())
        T["yoy"] = pct(T["fact"], T["prev_same"])
        T["growth"] = pct(T["plan"], T["fc"]) if y == 2027 else None
        T["white"] = _sum(fact_c, lambda k: k[3] == "white")
        T["second"] = _sum(fact_c, lambda k: k[3] == "second")
        T["light"] = _light(T["fact"], T["plan_ytd"]) if T["plan"] and y != 2027 else ""

        # по месяцам
        labels = MONTHS_SHORT[:]
        mf = [_sum(fact, lambda k, m=m: k[2] == m) for m in range(1, 13)]
        mp = [_sum(plan, lambda k, m=m: k[2] == m) for m in range(1, 13)] if plan else [
            _sum(prev_c, lambda k, m=m: k[2] == m) for m in range(1, 13)]
        if y == 2027:
            mf = [_sum(plan, lambda k, m=m: k[2] == m) for m in range(1, 13)]
            mp = [_sum(fc26, lambda k, m=m: k[2] == m) for m in range(1, 13)]
        months = [{"m": MONTHS_SHORT[i], "plan": mp[i], "fact": mf[i], "dev": mf[i] - mp[i] * (pfac(i + 1) if plan else 1),
                   "light": _light(mf[i], mp[i] * pfac(i + 1)) if plan and pfac(i + 1) else ""} for i in range(12)]

        # отделы × города (факт; для 2027 — план)
        base = plan if y == 2027 else fact
        cities = [ci for ci in CITIES + ["Прочие"] if _sum(base, lambda k, ci=ci: k[1] == ci)]
        grid = []
        for r in rows:
            cells = []
            for ci in cities:
                f = _sum(base, lambda k, ci=ci, d=r["code"]: k[1] == ci and dept_of(k[0]) == d)
                p = sum(v * pfac(k[2]) for k, v in plan.items() if k[1] == ci and dept_of(k[0]) == r["code"]) if y != 2027 else 0
                cells.append({"f": f, "p": p, "light": _light(f, p) if p else ""})
            grid.append({"name": r["name"], "cells": cells, "tot": sum(x["f"] for x in cells)})
        city_tot = [_sum(base, lambda k, ci=ci: k[1] == ci) for ci in cities]

        # статьи отдела × месяцы
        dep = dep if dep in D else (rows[0]["code"] if rows else "")
        arows = []
        for a, ar in arts.items():
            if ar["dept"] != dep:
                continue
            fm = [_sum(base, lambda k, a=a, m=m: k[0] == a and k[2] == m) for m in range(1, 13)]
            pa = _sum(plan, lambda k, a=a: k[0] == a)
            pytd = sum(v * pfac(k[2]) for k, v in plan.items() if k[0] == a)
            fa = sum(fm)
            if not (fa or pa):
                continue
            arows.append({"code": a, "name": ar["name"], "months": fm, "fact": fa, "plan": pa, "plan_ytd": pytd,
                          "light": _light(fa, pytd) if pa and y != 2027 else "",
                          "src": src.get(a, "") if a in ONEC else "заявки"})

        # белая / вторая по годам
        wy = []
        for yy in range(2020, date.today().year + 1):
            r = c.execute("SELECT SUM(CASE WHEN color='white' THEN sum ELSE 0 END) w, SUM(CASE WHEN color='second' THEN sum ELSE 0 END) s, "
                          "COUNT(*) n FROM an_fin_fact WHERE year=?", (yy,)).fetchone()
            if r["n"]:
                tot = (r["w"] or 0) + (r["s"] or 0)
                wy.append({"y": yy, "w": r["w"] or 0, "s": r["s"] or 0, "n": r["n"], "sp": (r["s"] or 0) / tot * 100 if tot else 0})
        basis = _q(c, "SELECT basis, color, COUNT(*) n, SUM(sum) s FROM an_fin_fact WHERE year=? GROUP BY basis, color "
                      "ORDER BY s DESC", (y,)) if y != 2027 else []

        # правки плана (для формы)
        edits = _edits(c, y) if y in PLAN_YEARS else {}
        plan_full = _plan(c, y, cutoff, arts) if y in PLAN_YEARS else {}
        form = []
        for d in depts:
            items = []
            for a, ar in arts.items():
                if ar["dept"] == d["code"]:
                    items.append({"code": a, "name": ar["name"], "plan": _sum(plan_full, lambda k, a=a: k[0] == a),
                                  "edit": edits.get(a)})
            form.append({"code": d["code"], "name": d["name"], "lst": items,
                         "tot": sum(i["plan"] for i in items)})
        hist = _q(c, "SELECT year, article, sum, who, ts FROM an_fin_plan ORDER BY id DESC LIMIT 15") if _has(c, "an_fin_plan") else []

    chart = chart_svg(labels, mf, mp, w=900, h=300)
    return {"empty": False, "y": y, "cutoff": cutoff, "meta": meta, "cm": cm, "T": T, "rows": rows, "months": months,
            "chart": chart, "cities": cities, "grid": grid, "city_tot": city_tot, "dep": dep, "dep_name": D.get(dep, {}).get("name", ""),
            "depts": [(d["code"], d["name"]) for d in depts if not (opex and d["code"] == "PUR")], "arows": arows,
            "wy": wy, "basis": basis, "form": form, "hist": hist, "has_plan": bool(plan), "src": src,
            "arts": arts, "depts_full": depts}


# ------------------------------------------------------------------ страницы
def _access(request):
    from . import main as m, access
    if not m.is_staff(request):
        return m.templates.TemplateResponse("login.html", {
            "request": request, "brand": config.BRAND, "company": config.COMPANY, "base": m._root(), "b24": True}), None
    s = access.scope(request)
    if not (s.password or s.role in VIEW_ROLES):
        return m.templates.TemplateResponse("noaccess.html", {
            "request": request, "brand": config.BRAND, "base": m._root(), "title": "Нет доступа",
            "text": "Вкладка «Фин. план» — для директоров, бухгалтера и администратора."}), None
    return None, s


@router.get("/dash/finplan", response_class=HTMLResponse)
def dash_finplan(request: Request, y: str = "", dep: str = "", opex: str = "", msg: str = ""):
    from . import main as m
    resp, s = _access(request)
    if resp:
        return resp
    try:
        yy = int(y)
    except ValueError:
        yy = date.today().year
    if yy not in YEARS and yy != 2027:
        yy = date.today().year
    data = build_finplan(yy, dep.strip(), opex == "1")
    can_edit = s.password or s.role in EDIT_ROLES
    nav = NAV if (s.password or s.role != "accountant") else \
        [("Аналитика", [("acc", "Бухгалтер", True), ("money", "Деньги и расходы", True), ("finplan", "Фин. план", True),
                        ("company", "Компания", True)])]
    return templates.TemplateResponse("dash_finplan.html", {
        "request": request, "brand": config.BRAND, "base": m._root(), "p": "month", "org": "", "branch": "", "d": "",
        "nav": nav, "tab": "finplan", "page_title": "Фин. план", "show_branch": False, "data": data, "money": money,
        "num": num, "years": YEARS + [2027], "opex": opex == "1", "can_edit": can_edit, "msg": msg,
        "last_local": _last_local(data.get("meta", {}).get("built")) if not data.get("empty") else "",
        "human_date": lambda x: x,
    })


@router.post("/dash/finplan/plan")
async def finplan_save(request: Request):
    from . import main as m, b24auth
    resp, s = _access(request)
    if resp:
        return resp
    if not (s.password or s.role in EDIT_ROLES):
        return RedirectResponse(f"{m._root()}/dash/finplan?msg=noedit", status_code=303)
    form = await request.form()
    try:
        y = int(form.get("y") or 0)
    except ValueError:
        y = 0
    if y not in PLAN_YEARS:
        return RedirectResponse(f"{m._root()}/dash/finplan", status_code=303)
    u = b24auth.current_user(request)
    who = (u or {}).get("name") or "общий пароль"
    ts = datetime.now().isoformat(timespec="seconds")
    n = 0
    with analytics.conn() as c:
        _depts, arts = _ref(c)
        cutoff = _meta(c).get("fact_to", "")
        cur = _plan(c, y, cutoff, arts)
        c.execute("CREATE TABLE IF NOT EXISTS an_fin_plan (id INTEGER PRIMARY KEY AUTOINCREMENT, year INTEGER, article TEXT, "
                  "sum REAL, who TEXT, ts TEXT)")
        for k, v in form.items():
            if not k.startswith("a_") or k[2:] not in arts:
                continue
            a = k[2:]
            v = str(v).replace("\xa0", "").replace(" ", "").replace(",", ".").strip()
            if v == "":
                continue
            try:
                new = round(float(v) * 1_000_000)   # ввод — в млн ₸
            except ValueError:
                continue
            if new < 0:
                continue
            old = round(float('%.2f' % (_sum(cur, lambda kk, a=a: kk[0] == a) / 1e6)) * 1_000_000)   # как в форме
            if abs(new - old) >= 1:
                c.execute("INSERT INTO an_fin_plan (year, article, sum, who, ts) VALUES (?,?,?,?,?)", (y, a, new, who, ts))
                n += 1
    return RedirectResponse(f"{m._root()}/dash/finplan?y={y}&msg=saved{n}#plan", status_code=303)
