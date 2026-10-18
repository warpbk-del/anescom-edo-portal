"""Портал v4, этап B: дашборды по данным 1С (база analytics.sqlite3, см. app/analytics.py).

Маршрут /dash?p=<period>&org=&branch=&d=YYYY-MM-DD — экран «Компания» (директор / администратор).
Вход — пока общим паролем кабинета (is_staff); вход из Битрикс24 и роли — этап A, часть 2.
Администратор видит все вкладки (решение пользователя 18.10 10:04); вкладки других ролей
добавляются по мере готовности, ещё не готовые показаны в меню серым.

Опорная дата: по умолчанию — последняя дата продаж в выгрузке (в копии базы данные старые,
поэтому «сегодня» по календарю было бы пустым). Её можно задать параметром d.
"""
import re
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from . import analytics, config

router = APIRouter()
templates = Jinja2Templates(directory=str(config.BASE_DIR / "app" / "templates"))


def _me(request):
    from . import b24auth
    return b24auth.me(request)


templates.env.globals["edo_me"] = _me

PERIODS = [("today", "Сегодня"), ("yesterday", "Вчера"), ("week", "Неделя"), ("month", "Месяц"), ("year", "Год")]
PERIOD_TITLES = {"today": "сегодня", "yesterday": "вчера", "week": "последние 7 дней",
                 "month": "с начала месяца", "year": "с начала года"}
MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября",
          "октября", "ноября", "декабря"]
MONTHS_SHORT = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]
PAY_LABELS = {"card": "Карта", "cash": "Наличные", "bank": "Безнал"}
ILLIQUID_DAYS = 90      # неликвид: остаток есть, продаж нет 90 дней (решение 18.10 09:31)
REORDER_DAYS = 14       # дозаказ: запаса меньше чем на 14 дней по продажам за 30 дней

# Меню: (ключ, название, готово)
NAV = [
    ("Аналитика", [("company", "Компания", True), ("branches", "Продажи по филиалам", True),
                   ("stock", "Склады", True), ("purchase", "Закупки", True), ("money", "Деньги и расходы", True),
                   ("acc", "Долги и переплаты", True), ("prod", "Производство АВТОКОМП", True),
                   ("history", "История по годам", True)]),
    ("Роли", [("mgr", "Менеджер", True), ("stock", "Кладовщик", True), ("purchase", "Закупщик", True),
              ("acc", "Бухгалтер", True), ("branches", "РОП", True)]),
]


# прошлые годы рядом с «Сегодня … Год» (решение пользователя 18.10.2026): p = «2024» — весь 2024 год
def _yearp(p) -> bool:
    return isinstance(p, str) and len(p) == 4 and p.isdigit() and "1990" < p < "2100"


def _isyear(p) -> bool:
    return p == "year" or _yearp(p)


def _valid_p(p) -> bool:
    return p in dict(PERIODS) or (_yearp(p) and int(p) < date.today().year)


def _ptitle(p) -> str:
    return f"{p} год" if _yearp(p) else PERIOD_TITLES[p]


_YEARS_CACHE = {"t": None, "v": []}


def periods_all():
    """«Сегодня…Год» + прошлые годы, за которые есть продажи (с начала базы), по убыванию."""
    now = datetime.now()
    if _YEARS_CACHE["t"] is None or (now - _YEARS_CACHE["t"]).seconds > 300:
        try:
            with analytics.conn() as c:
                ys = [r["y"] for r in _q(c, "SELECT DISTINCT substr(date,1,4) y FROM an_sales WHERE date<>'' ORDER BY y DESC")]
        except Exception:
            ys = []
        cur = str(date.today().year)
        _YEARS_CACHE.update(t=now, v=[y for y in ys if _yearp(y) and y < cur])
    return PERIODS + [(y, y) for y in _YEARS_CACHE["v"]]


# ------------------------------------------------------------------ форматирование
def money(v: float, short: bool = True) -> str:
    v = float(v or 0)
    a = abs(v)
    if short and a >= 1e9:
        s = f"{v / 1e9:.1f} млрд"
    elif short and a >= 1e6:
        s = f"{v / 1e6:.1f} млн"
    elif short and a >= 1e4:
        s = f"{v / 1e3:.0f} тыс"
    else:
        s = f"{v:,.0f}".replace(",", " ")
    return s.replace(".", ",")


def num(v: float) -> str:
    v = float(v or 0)
    return (f"{v:,.0f}" if abs(v - round(v)) < 0.005 else f"{v:,.1f}").replace(",", " ").replace(".", ",")


def pct(a: float, b: float) -> Optional[float]:
    return None if not b else (a - b) / abs(b) * 100


def ddate(s: str) -> date:
    return date.fromisoformat(s)


def human_date(d: date) -> str:
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def is_internal(name: str) -> bool:
    """Свои компании (внутригрупповые расчёты) — показываются отдельно от долгов клиентов."""
    n = (name or "").upper()
    return any(k in n for k in config.INTERNAL_CLIENTS)


def branch_short(b: str) -> str:
    """«Филиал ТОО "ANESCOM/АНЕСКОМ" г: Атырау» → «Атырау»; головное ТОО → «Актобе (головное)»; GREENTE помечается."""
    b = b or ""
    m = re.search(r"г[\.:]\s*([^,\"]+)", b)
    city = m.group(1).strip() if m else ""
    up = b.upper()
    if "GREENTE" in up or "ГРИНТЕ" in up:
        return "GREENTE" + (" · " + city if city else "")
    if city:
        return city
    if "ANESCOM" in up or "АНЕСКОМ" in up:
        return "Актобе (головное)"
    return b or "(не указан)"


templates.env.filters["brs"] = branch_short


def cname(s: str) -> str:
    """Имя клиента для сопоставления: в долгах 1С ключ — контрагент, в продажах и оплатах — партнёр,
    поэтому сверяем ещё и по названию."""
    return " ".join((s or "").replace("«", '"').replace("»", '"').upper().split())


def client_branches(c) -> dict:
    """Филиал клиента = где больше всего продаж за всю историю. Ключи: client_key и название."""
    best = {}
    for r in _q(c, "SELECT client_key k, client n, branch b, SUM(sum) s FROM an_sales WHERE branch<>'' "
                   "GROUP BY k, b"):
        for key in (r["k"], cname(r["n"])):
            if key and (key not in best or r["s"] > best[key][1]):
                best[key] = (r["b"], r["s"])
    return best


def abc_split(rows) -> list:
    """ABC по выручке: A — первые 80%, B — следующие 15%, C — остальные 5%."""
    total = sum(r["s"] or 0 for r in rows) or 1
    cats = {k: {"k": k, "items": [], "s": 0.0} for k in "ABC"}
    acc = 0.0
    for r in rows:
        k = "A" if acc < total * 0.8 else ("B" if acc < total * 0.95 else "C")
        acc += r["s"] or 0
        cats[k]["items"].append(dict(r))
        cats[k]["s"] += r["s"] or 0
    n_all = len(rows) or 1
    out = []
    for k, title in (("A", "дают 80% выручки"), ("B", "ещё 15%"), ("C", "последние 5%")):
        x = cats[k]
        x.update(title=title, n=len(x["items"]), share=x["s"] / total * 100, n_share=len(x["items"]) / n_all * 100)
        out.append(x)
    return out


# ------------------------------------------------------------------ периоды
def period_range(p: str, anchor: date):
    """Текущий период и предыдущий такой же длины. p = «2024» — весь календарный год и прошлый год целиком."""
    if _yearp(p):
        yy = int(p)
        return date(yy, 1, 1), date(yy, 12, 31), date(yy - 1, 1, 1), date(yy - 1, 12, 31)
    if p == "yesterday":
        a = b = anchor - timedelta(days=1)
    elif p == "week":
        a, b = anchor - timedelta(days=6), anchor
    elif p == "month":
        a, b = anchor.replace(day=1), anchor
    elif p == "year":
        a, b = anchor.replace(month=1, day=1), anchor
    else:
        a = b = anchor
    if p == "month":                       # тот же отрезок прошлого месяца
        pm_end = a - timedelta(days=1)
        pa = pm_end.replace(day=1)
        pb = min(pa + (b - a), pm_end)
    elif p == "year":                      # тот же отрезок прошлого года
        pa = a.replace(year=a.year - 1)
        try:
            pb = b.replace(year=b.year - 1)
        except ValueError:
            pb = b.replace(year=b.year - 1, day=28)
    else:
        n = (b - a).days + 1
        pa, pb = a - timedelta(days=n), b - timedelta(days=n)
    return a, b, pa, pb


# ------------------------------------------------------------------ запросы
import contextvars
_MGR = contextvars.ContextVar("edo_mgr", default="")   # ФИО менеджера 1С — для роли «Менеджер»


def _where(org: str, branch: str, dated: bool = True, has_branch: bool = True, has_mgr: bool = True):
    w, args = [], []
    if dated:
        w.append("date BETWEEN ? AND ?")
    if has_mgr and _MGR.get():
        w.append("manager = ?")
        args.append(_MGR.get())
    if org:
        w.append("org = ?")
        args.append(org)
    if branch and has_branch:
        w.append("branch = ?")
        args.append(branch)
    return w, args


def _q(c, sql, args=()):
    return c.execute(sql, args).fetchall()


def build(p: str, org: str, branch: str, d: str):
    with analytics.conn() as c:
        mx = c.execute("SELECT MAX(date) m FROM an_sales").fetchone()["m"]
        last = c.execute("SELECT MAX(ts) t FROM an_loads WHERE kind IN ('sales','stock')").fetchone()["t"]
        orgs = [r["org"] for r in _q(c, "SELECT DISTINCT org FROM an_sales WHERE org<>'' ORDER BY org")]
        branches = [r["branch"] for r in _q(c, "SELECT DISTINCT branch FROM an_sales WHERE branch<>''"
                                               + (" AND org=?" if org else "") + " ORDER BY branch",
                                               (org,) if org else ())]
        if not mx:
            return {"empty": True, "orgs": orgs, "branches": branches, "last": last}
        try:
            anchor = ddate(d) if d else ddate(mx)
        except ValueError:
            anchor = ddate(mx)
        a, b, pa, pb = period_range(p, anchor)
        w, wa = _where(org, branch)
        W = " WHERE " + " AND ".join(w)

        # Себестоимость берём только по правдоподобным строкам: 0 < cost <= 5 × сумма.
        # (В копии базы регистр себестоимости местами испорчен — миллиардные минусы по отдельным позициям.)
        ok_cost = "(cost > 0 AND sum > 0 AND cost <= sum * 5)"

        def sales_sum(x, y):
            r = c.execute("SELECT COALESCE(SUM(sum),0) s, COUNT(DISTINCT doc_key) n, COUNT(DISTINCT client_key) k, "
                          f"COALESCE(SUM(CASE WHEN {ok_cost} THEN sum END),0) s_ok, "
                          f"COALESCE(SUM(CASE WHEN {ok_cost} THEN cost END),0) c_ok, "
                          "SUM(CASE WHEN cost <> 0 AND NOT " + ok_cost + " THEN 1 ELSE 0 END) bad "
                          "FROM an_sales" + W, [str(x), str(y)] + wa).fetchone()
            return dict(r)

        cur, prev = sales_sum(a, b), sales_sum(pa, pb)
        cost_known = cur["c_ok"] > 0
        gross = cur["s_ok"] - cur["c_ok"] if cost_known else None

        # расходы (ДДС, расход) за период — по организации; филиал в ДДС часто пустой, фильтр не применяем
        wc, wca = _where(org, "", True, False, False)
        exp = c.execute("SELECT COALESCE(SUM(sum),0) s FROM an_cashflow WHERE direction='out' AND "
                        + " AND ".join(wc), [str(a), str(b)] + wca).fetchone()["s"]
        exp_prev = c.execute("SELECT COALESCE(SUM(sum),0) s FROM an_cashflow WHERE direction='out' AND "
                             + " AND ".join(wc), [str(pa), str(pb)] + wca).fetchone()["s"]
        exp_by = _q(c, "SELECT CASE WHEN article='' THEN 'Без статьи' ELSE article END a, SUM(sum) s FROM an_cashflow "
                       "WHERE direction='out' AND " + " AND ".join(wc) + " GROUP BY a ORDER BY s DESC LIMIT 12",
                    [str(a), str(b)] + wca)

        # долги/переплаты — снимок на момент выгрузки; свои компании (АВТОКОМП и др.) — отдельно
        wd, wda = _where(org, "", False, False)
        Wd = (" WHERE " + " AND ".join(wd)) if wd else ""
        all_d = [dict(r) for r in _q(c, "SELECT org, client, manager, debt, prepay FROM an_debts" + Wd, wda)]
        own = [r for r in all_d if is_internal(r["client"])]
        ext = [r for r in all_d if not is_internal(r["client"])]
        dsum = {"d": sum(r["debt"] for r in ext), "p": sum(r["prepay"] for r in ext),
                "nd": sum(1 for r in ext if r["debt"] > 0), "np": sum(1 for r in ext if r["prepay"] > 0)}
        debtors = sorted([r for r in ext if r["debt"] > 0], key=lambda r: -r["debt"])[:8]
        prepays = sorted([r for r in ext if r["prepay"] > 0], key=lambda r: -r["prepay"])[:6]
        own = sorted([r for r in own if r["debt"] or r["prepay"]], key=lambda r: -(r["debt"] - r["prepay"]))

        # оплаты по способам
        wp, wpa = _where(org, branch)
        pays = {r["kind"]: r["s"] for r in _q(c, "SELECT kind, SUM(sum) s FROM an_payments WHERE "
                                                 + " AND ".join(wp) + " GROUP BY kind", [str(a), str(b)] + wpa)}
        pay_total = sum(pays.values())

        # филиалы
        wb, wba = _where(org, "")
        by_branch = _q(c, "SELECT CASE WHEN branch='' THEN '(не указан)' ELSE branch END br, SUM(sum) s, SUM(cost) c, "
                          "COUNT(DISTINCT doc_key) n FROM an_sales WHERE " + " AND ".join(wb)
                       + " GROUP BY br ORDER BY s DESC", [str(a), str(b)] + wba)

        # топ материалов
        top = _q(c, "SELECT item, item_group g, SUM(qty) q, SUM(sum) s FROM an_sales" + W
                 + " GROUP BY item_key ORDER BY s DESC LIMIT 10", [str(a), str(b)] + wa)
        abc = abc_split(_q(c, "SELECT item, item_group g, SUM(qty) q, SUM(sum) s FROM an_sales" + W
                           + " GROUP BY item_key HAVING SUM(sum) > 0 ORDER BY s DESC", [str(a), str(b)] + wa))

        # график
        if _isyear(p):
            ser = {r["k"]: r["s"] for r in _q(c, "SELECT substr(date,1,7) k, SUM(sum) s FROM an_sales" + W
                                                 + " GROUP BY k", [str(a), str(b)] + wa)}
            sep = {r["k"]: r["s"] for r in _q(c, "SELECT substr(date,1,7) k, SUM(sum) s FROM an_sales" + W
                                                 + " GROUP BY k", [str(pa), str(pb)] + wa)}
            labels, cv, pv = [], [], []
            for m in range(a.month, b.month + 1):
                labels.append(MONTHS_SHORT[m - 1])
                cv.append(ser.get(f"{a.year}-{m:02d}", 0))
                pv.append(sep.get(f"{a.year - 1}-{m:02d}", 0))
        else:
            if (b - a).days >= 6:
                ca, cb, shift = a, b, a - pa
            else:                          # день — показываем последние 14 дней
                ca, cb, shift = anchor - timedelta(days=13), anchor, timedelta(days=14)
            n = (cb - ca).days + 1
            ser = {r["date"]: r["s"] for r in _q(c, "SELECT date, SUM(sum) s FROM an_sales" + W + " GROUP BY date",
                                                 [str(ca), str(cb)] + wa)}
            sep = {r["date"]: r["s"] for r in _q(c, "SELECT date, SUM(sum) s FROM an_sales" + W + " GROUP BY date",
                                                 [str(ca - shift), str(cb - shift)] + wa)}
            labels, cv, pv = [], [], []
            for i in range(n):
                x = ca + timedelta(days=i)
                labels.append(f"{x.day}.{x.month:02d}")
                cv.append(ser.get(str(x), 0))
                pv.append(sep.get(str(x - shift), 0))

        # склад: неликвид и дозаказ (снимок)
        ws, wsa = _where(org, branch, False, True, False)
        Ws = (" AND " + " AND ".join(ws)) if ws else ""
        cutoff = str(anchor - timedelta(days=ILLIQUID_DAYS))
        ill_n = c.execute("SELECT COUNT(*) n FROM an_stock WHERE qty>0 AND sold_90=0 AND (last_sale='' OR last_sale<?)"
                          + Ws, [cutoff] + wsa).fetchone()["n"]
        illiquid = _q(c, "SELECT item, warehouse, qty, unit, last_sale FROM an_stock WHERE qty>0 AND sold_90=0 "
                         "AND (last_sale='' OR last_sale<?)" + Ws + " ORDER BY qty DESC LIMIT 8", [cutoff] + wsa)
        reorder = _q(c, "SELECT item, warehouse, qty, unit, sold_30, qty/(sold_30/30.0) days FROM an_stock "
                        "WHERE sold_30>0 AND qty < sold_30/30.0*?" + Ws + " ORDER BY days ASC LIMIT 8",
                     [REORDER_DAYS] + wsa)
        reorder_n = c.execute("SELECT COUNT(*) n FROM an_stock WHERE sold_30>0 AND qty < sold_30/30.0*?" + Ws,
                              [REORDER_DAYS] + wsa).fetchone()["n"]

    return {
        "empty": False, "orgs": orgs, "branches": branches, "last": last, "anchor": anchor, "max_date": mx,
        "a": a, "b": b, "pa": pa, "pb": pb,
        "cur": cur, "prev": prev, "rev_delta": pct(cur["s"], prev["s"]), "cost_known": cost_known, "gross": gross,
        "margin": (gross / cur["s_ok"] * 100) if (gross is not None and cur["s_ok"]) else None,
        "cost_cover": (cur["s_ok"] / cur["s"] * 100) if cur["s"] else 0, "cost_bad": cur["bad"] or 0,
        "exp": exp, "exp_delta": pct(exp, exp_prev), "exp_by": exp_by,
        "debt": dsum["d"], "prepay": dsum["p"], "n_debt": dsum["nd"] or 0, "n_prepay": dsum["np"] or 0,
        "debtors": debtors, "prepays": prepays, "own": own,
        "own_debt": sum(r["debt"] for r in own), "own_prepay": sum(r["prepay"] for r in own),
        "pays": [(k, PAY_LABELS[k], pays.get(k, 0)) for k in ("card", "cash", "bank")], "pay_total": pay_total,
        "by_branch": [dict(r, short=branch_short(r["br"])) for r in by_branch], "br_total": sum(r["s"] or 0 for r in by_branch), "top": top, "abc": abc,
        "chart": chart_svg(labels, cv, pv, w=700, h=330),
        "illiquid": illiquid, "ill_n": ill_n, "reorder": reorder, "reorder_n": reorder_n,
    }


# ------------------------------------------------------------------ графики (SVG на сервере, без библиотек)
def chart_svg(labels, cur, prev, w=1200, h=300, unit="₸"):
    """Столбцы текущего периода (свечение) + пунктир прошлого периода. Тёмная тема.
    unit — единица в подсказке столбца («₸» для денег, «м²»/«т»/«» для производства)."""
    if not labels:
        return ""
    pad_l, pad_r, pad_t, pad_b = 54, 12, 14, 28
    iw, ih = w - pad_l - pad_r, h - pad_t - pad_b
    top = max(max(cur or [0]), max(prev or [0]), 1)
    mag = 10 ** (len(str(int(top))) - 1)
    for k in (1, 2, 2.5, 5, 10):
        if top <= k * mag:
            top = k * mag
            break
    n = len(labels)
    bw = iw / n
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="График: текущий и прошлый период" '
           f'style="width:100%;height:auto;display:block">'
           '<defs><linearGradient id="gb" x1="0" y1="0" x2="0" y2="1">'
           '<stop offset="0" stop-color="#7fc3ff"/><stop offset="1" stop-color="#1b4f8f" stop-opacity=".55"/></linearGradient>'
           '<filter id="gl" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="2.2" result="b"/>'
           '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>']
    for i in range(5):
        y = pad_t + ih * i / 4
        v = top * (1 - i / 4)
        out.append(f'<line x1="{pad_l}" x2="{w - pad_r}" y1="{y:.1f}" y2="{y:.1f}" stroke="rgba(143,190,240,.12)"/>')
        out.append(f'<text x="{pad_l - 8}" y="{y + 4:.1f}" text-anchor="end" class="ax">{money(v)}</text>')
    for i, v in enumerate(cur):
        bh = ih * (v / top)
        x = pad_l + i * bw + bw * 0.22
        out.append(f'<rect x="{x:.1f}" y="{pad_t + ih - bh:.1f}" width="{bw * 0.56:.1f}" height="{bh:.1f}" rx="2" '
                   f'fill="url(#gb)"><title>{labels[i]}: {(money(v, False) + ' ' + unit) if unit == '₸' else (num(v) + (' ' + unit if unit else ''))}</title></rect>')
    pts = " ".join(f"{pad_l + i * bw + bw / 2:.1f},{pad_t + ih - ih * (v / top):.1f}" for i, v in enumerate(prev))
    out.append(f'<polyline points="{pts}" fill="none" stroke="#ff4d47" stroke-width="2" stroke-dasharray="5 4" filter="url(#gl)"/>')
    step = max(1, n // 10)
    for i, lab in enumerate(labels):
        if i % step == 0 or i == n - 1:
            out.append(f'<text x="{pad_l + i * bw + bw / 2:.1f}" y="{h - 8}" text-anchor="middle" class="ax">{lab}</text>')
    out.append("</svg>")
    return "".join(out)


def ring_svg(pct, color="#ff4d47", size=120, width=10, label=""):
    """Кольцевой индикатор 0–100% с делениями (как на «диспетчерских» панелях)."""
    pct = max(0.0, min(100.0, float(pct or 0)))
    r = (size - width) / 2 - 6
    c = size / 2
    import math
    circ = 2 * math.pi * r
    ticks = []
    for k in range(40):
        a = math.radians(k * 9 - 90)
        r1, r2 = r + width / 2 + 3, r + width / 2 + (7 if k % 5 == 0 else 5)
        on = k / 40 * 100 < pct
        ticks.append(f'<line x1="{c + r1 * math.cos(a):.1f}" y1="{c + r1 * math.sin(a):.1f}" '
                     f'x2="{c + r2 * math.cos(a):.1f}" y2="{c + r2 * math.sin(a):.1f}" '
                     f'stroke="{color if on else "rgba(143,190,240,.22)"}" stroke-width="1.4"/>')
    return (f'<svg viewBox="0 0 {size} {size}" width="{size}" height="{size}" role="img" aria-label="{label} {pct:.0f}%">'
            f'<circle cx="{c}" cy="{c}" r="{r:.1f}" fill="none" stroke="rgba(143,190,240,.14)" stroke-width="{width}"/>'
            f'<circle cx="{c}" cy="{c}" r="{r:.1f}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" '
            f'stroke-dasharray="{circ * pct / 100:.1f} {circ:.1f}" transform="rotate(-90 {c} {c})" '
            f'style="filter:drop-shadow(0 0 5px {color})"/>' + "".join(ticks) +
            f'<text x="{c}" y="{c + 7}" text-anchor="middle" class="rv">{pct:.0f}%</text></svg>')


# ------------------------------------------------------------------ страница
# ------------------------------------------------------------------ вкладка «Продажи по филиалам»
SERIES_COLORS = ["#5fb2ff", "#ff4d47", "#f2b84b", "#3fd38b", "#b48cff", "#4fe0e0", "#ff8fc8", "#c9d6e4"]


def _context(c, org):
    mx = c.execute("SELECT MAX(date) m FROM an_sales").fetchone()["m"]
    last = c.execute("SELECT MAX(ts) t FROM an_loads WHERE kind IN ('sales','stock')").fetchone()["t"]
    orgs = [r["org"] for r in _q(c, "SELECT DISTINCT org FROM an_sales WHERE org<>'' ORDER BY org")]
    return mx, last, orgs


def build_branches(p: str, org: str, d: str):
    ok_cost = "(cost > 0 AND sum > 0 AND cost <= sum * 5)"
    br_expr = "CASE WHEN branch='' THEN '(не указан)' ELSE branch END"
    with analytics.conn() as c:
        mx, last, orgs = _context(c, org)
        if not mx:
            return {"empty": True, "orgs": orgs, "branches": [], "last": last}
        try:
            anchor = ddate(d) if d else ddate(mx)
        except ValueError:
            anchor = ddate(mx)
        a, b, pa, pb = period_range(p, anchor)
        w, wa = _where(org, "")
        W = " WHERE " + " AND ".join(w)

        def agg(x, y):
            return {r["br"]: dict(r) for r in _q(c,
                f"SELECT {br_expr} br, SUM(sum) s, COUNT(DISTINCT doc_key) n, COUNT(DISTINCT client_key) k, "
                f"SUM(CASE WHEN {ok_cost} THEN sum END) s_ok, SUM(CASE WHEN {ok_cost} THEN cost END) c_ok "
                "FROM an_sales" + W + " GROUP BY br", [str(x), str(y)] + wa)}

        cur, prev = agg(a, b), agg(pa, pb)
        total = sum(r["s"] or 0 for r in cur.values())
        total_prev = sum(r["s"] or 0 for r in prev.values())
        rows = []
        for br, r in cur.items():
            s_ = r["s"] or 0
            ps = (prev.get(br) or {}).get("s") or 0
            gross = (r["s_ok"] or 0) - (r["c_ok"] or 0) if r["c_ok"] else None
            rows.append({"br": br, "s": s_, "prev": ps, "delta": pct(s_, ps), "share": (s_ / total * 100) if total else 0,
                         "n": r["n"], "k": r["k"], "avg": (s_ / r["n"]) if r["n"] else 0, "gross": gross,
                         "margin": (gross / r["s_ok"] * 100) if (gross is not None and r["s_ok"]) else None})
        for br, r in prev.items():          # филиалы без продаж в текущем периоде
            if br not in cur:
                rows.append({"br": br, "s": 0, "prev": r["s"] or 0, "delta": -100.0, "share": 0, "n": 0, "k": 0,
                             "avg": 0, "gross": None, "margin": None})
        rows.sort(key=lambda x: -x["s"])
        for i, r in enumerate(rows):
            r["color"] = SERIES_COLORS[i % len(SERIES_COLORS)]

        # график по филиалам (топ-6)
        top_br = [r["br"] for r in rows[:6]]
        if _isyear(p):
            keyf, labels, keys = "substr(date,1,7)", [], []
            for mth in range(a.month, b.month + 1):
                labels.append(MONTHS_SHORT[mth - 1])
                keys.append(f"{a.year}-{mth:02d}")
            ca, cb = a, b
        else:
            ca, cb = (a, b) if (b - a).days >= 6 else (anchor - timedelta(days=13), anchor)
            keyf, labels, keys = "date", [], []
            for i in range((cb - ca).days + 1):
                x = ca + timedelta(days=i)
                labels.append(f"{x.day}.{x.month:02d}")
                keys.append(str(x))
        data = {}
        for r in _q(c, f"SELECT {br_expr} br, {keyf} k, SUM(sum) s FROM an_sales" + W + " GROUP BY br, k",
                    [str(ca), str(cb)] + wa):
            data.setdefault(r["br"], {})[r["k"]] = r["s"]
        series = [(br, rows[i]["color"], [data.get(br, {}).get(k, 0) for k in keys]) for i, br in enumerate(top_br)]

        managers = _q(c, "SELECT CASE WHEN manager='' THEN '(не указан)' ELSE manager END m, "
                         f"{br_expr} br, SUM(sum) s, COUNT(DISTINCT doc_key) n FROM an_sales" + W
                      + " GROUP BY m ORDER BY s DESC LIMIT 10", [str(a), str(b)] + wa)
        groups = _q(c, "SELECT CASE WHEN item_group='' THEN '(без группы)' ELSE item_group END g, SUM(sum) s "
                       "FROM an_sales" + W + " GROUP BY g ORDER BY s DESC LIMIT 8", [str(a), str(b)] + wa)
        wp, wpa = _where(org, "")
        pays = {}
        for r in _q(c, f"SELECT {br_expr} br, kind, SUM(sum) s FROM an_payments WHERE " + " AND ".join(wp)
                    + " GROUP BY br, kind", [str(a), str(b)] + wpa):
            pays.setdefault(r["br"], {"card": 0, "cash": 0, "bank": 0})[r["kind"]] = r["s"] or 0
        pay_rows = sorted(({"br": k, **v, "t": sum(v.values())} for k, v in pays.items()), key=lambda x: -x["t"])

    return {"empty": False, "orgs": orgs, "branches": [], "last": last, "anchor": anchor, "max_date": mx,
            "a": a, "b": b, "pa": pa, "pb": pb, "total": total, "total_prev": total_prev,
            "total_delta": pct(total, total_prev), "rows": rows, "n_branches": len([r for r in rows if r["s"]]),
            "chart": lines_svg(labels, series, w=700, h=330), "managers": managers, "groups": groups, "pay_rows": pay_rows}


def lines_svg(labels, series, w=1200, h=300):
    """Несколько неоновых линий (по филиалам). series: [(имя, цвет, значения)]."""
    if not labels or not series:
        return ""
    pad_l, pad_r, pad_t, pad_b = 54, 12, 14, 28
    iw, ih = w - pad_l - pad_r, h - pad_t - pad_b
    top = max([max(v or [0]) for _, _, v in series] + [1])
    mag = 10 ** (len(str(int(top))) - 1)
    for k in (1, 2, 2.5, 5, 10):
        if top <= k * mag:
            top = k * mag
            break
    n = len(labels)
    step_x = iw / max(n - 1, 1)
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Выручка по филиалам" style="width:100%;height:auto;display:block">'
           '<defs><filter id="gl2" x="-10%" y="-30%" width="120%" height="160%"><feGaussianBlur stdDeviation="2.4" result="b"/>'
           '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>']
    for i in range(5):
        y = pad_t + ih * i / 4
        out.append(f'<line x1="{pad_l}" x2="{w - pad_r}" y1="{y:.1f}" y2="{y:.1f}" stroke="rgba(143,190,240,.12)"/>')
        out.append(f'<text x="{pad_l - 8}" y="{y + 4:.1f}" text-anchor="end" class="ax">{money(top * (1 - i / 4))}</text>')
    for name, color, vals in series:
        pts = " ".join(f"{pad_l + i * step_x:.1f},{pad_t + ih - ih * (v / top):.1f}" for i, v in enumerate(vals))
        out.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.2" stroke-linejoin="round" '
                   f'filter="url(#gl2)"><title>{name}</title></polyline>')
        if n <= 31:
            for i, v in enumerate(vals):
                out.append(f'<circle cx="{pad_l + i * step_x:.1f}" cy="{pad_t + ih - ih * (v / top):.1f}" r="2.6" '
                           f'fill="{color}"><title>{name}, {labels[i]}: {money(v, False)} ₸</title></circle>')
    stp = max(1, n // 10)
    for i, lab in enumerate(labels):
        if i % stp == 0 or i == n - 1:
            out.append(f'<text x="{pad_l + i * step_x:.1f}" y="{h - 8}" text-anchor="middle" class="ax">{lab}</text>')
    out.append("</svg>")
    return "".join(out)


def _last_local(last):
    if not last:
        return ""
    try:
        return datetime.fromisoformat(last).astimezone(timezone(timedelta(hours=config.TZ_OFFSET_HOURS))).strftime("%d.%m %H:%M")
    except ValueError:
        return last



def _gate(request: Request, tab: str):
    """→ (ответ-заглушка или None, limited). Роли: полная аналитика / менеджер (свои) / остальные — пока нет вкладки."""
    from . import main as m, access
    if not m.is_staff(request):
        return m.templates.TemplateResponse("login.html", {
            "request": request, "brand": config.BRAND, "company": config.COMPANY, "base": m._root(),
            "b24": True}), False
    s = access.scope(request)
    _MGR.set("")
    if s.password or s.full_dash:
        return None, False
    def stub(title, text):
        return m.templates.TemplateResponse("noaccess.html", {
            "request": request, "brand": config.BRAND, "base": m._root(), "title": title, "text": text}), False
    if s.role == "manager" and tab == "company":
        if not s.mgr_1c:
            return stub("Мои продажи", "Не нашли ваше ФИО среди менеджеров в выгрузке 1С. Администратор может указать его на странице «Роли и доступ».")
        _MGR.set(s.mgr_1c)
        return None, True
    if s.role == "manager":
        return stub("Нет доступа", "Эта вкладка — для руководителей. Ваши продажи — в разделе «Аналитика».")
    if s.role in ("storekeeper", "purchaser"):
        from fastapi.responses import RedirectResponse
        return RedirectResponse(f"{m._root()}/dash/{'stock' if s.role == 'storekeeper' else 'purchase'}", status_code=303), False
    titles = {}
    return stub(titles.get(s.role, "Аналитика"),
                "Ваша вкладка аналитики появится на следующем шаге (склад, дозаказ, неликвиды). Документы на подпись — в «Мои задачи».")

@router.get("/dash/branches", response_class=HTMLResponse)
def dash_branches(request: Request, p: str = "month", org: str = "", d: str = ""):
    from . import main as m
    resp, _lim = _gate(request, "branches")
    if resp:
        return resp
    if not _valid_p(p):
        p = "month"
    data = build_branches(p, org.strip(), d.strip())
    return templates.TemplateResponse("dash_branches.html", {
        "request": request, "brand": config.BRAND, "base": m._root(), "p": p, "org": org, "branch": "", "d": d,
        "periods": periods_all(), "period_title": _ptitle(p), "nav": NAV, "tab": "branches",
        "page_title": "Продажи по филиалам", "show_branch": False,
        "data": data, "money": money, "num": num, "human_date": human_date, "last_local": _last_local(data.get("last")),
        "ring": ring_svg,
    })


@router.get("/dash", response_class=HTMLResponse)
def dash(request: Request, p: str = "month", org: str = "", branch: str = "", d: str = ""):
    from . import main as m  # поздний импорт: main подключает этот роутер
    resp, limited = _gate(request, "company")
    if resp:
        return resp
    if not _valid_p(p):
        p = "month"
    data = build(p, org.strip(), branch.strip(), d.strip())
    _MGR.set("")
    prod = None
    if not limited:
        try:
            prod = build_prod(p, org.strip(), d.strip())
        except Exception:  # производство — дополнительный блок, не ломаем «Компанию»
            prod = None
    tz = timezone(timedelta(hours=config.TZ_OFFSET_HOURS))
    last_local = ""
    if data.get("last"):
        try:
            last_local = datetime.fromisoformat(data["last"]).astimezone(tz).strftime("%d.%m %H:%M")
        except ValueError:
            last_local = data["last"]
    return templates.TemplateResponse("dash.html", {
        "request": request, "brand": config.BRAND, "base": m._root(), "p": p, "org": org, "branch": branch, "d": d,
        "periods": periods_all(), "period_title": _ptitle(p), "tab": "company",
        "nav": [("Аналитика", [("company", "Мои продажи", True)])] if limited else NAV,
        "page_title": "Мои продажи" if limited else "Компания", "show_branch": True, "limited": limited,
        "data": data, "money": money, "num": num, "human_date": human_date, "last_local": last_local,
        "illiquid_days": ILLIQUID_DAYS, "reorder_days": REORDER_DAYS, "ring": ring_svg, "P": prod,
    })


# ================================================================== склад и закупки (этап B)
# мин/макс остатка в днях продаж (средние за 90 дн.) по классу ABC склада — решение пользователя 18.10
MINMAX_DAYS = {"A": (14, 30), "B": (10, 21), "C": (7, 14)}
ABC_DAYS = 90
TARGET_DAYS = 30   # дозаказ «до запаса на 30 дней» по средним продажам за 30 дней


AK_MARK = "АВТОКОМП · "


def _stock_views(c):
    """Остатки и продажи обеих баз вместе (18.10.2026): склады базы АВТОКОМП — с пометкой «АВТОКОМП · »."""
    st = "org, branch, warehouse, item, item_key, item_group, unit, qty, cost_sum, last_sale, sold_30, sold_90"
    sa = "date, doc_key, doc_no, org, branch, warehouse, manager, client, client_key, item, item_key, item_group, qty, sum, cost"
    mark = (f"CASE WHEN warehouse LIKE '%АВТОКОМП%' OR warehouse LIKE '%Автокомп%' THEN warehouse "
            f"ELSE '{AK_MARK}' || warehouse END")
    c.execute("DROP VIEW IF EXISTS temp.v_stock")
    c.execute("DROP VIEW IF EXISTS temp.v_sales")
    c.execute(f"CREATE TEMP VIEW v_stock AS SELECT {st} FROM an_stock UNION ALL SELECT "
              + st.replace("warehouse,", f"{mark} warehouse,", 1) + " FROM an_stock_avtokomp")
    c.execute(f"CREATE TEMP VIEW v_sales AS SELECT {sa} FROM an_sales UNION ALL SELECT "
              + sa.replace("warehouse,", f"{mark} warehouse,", 1) + " FROM an_sales_avtokomp")


def build_stock(org: str, wh: str, allowed: Optional[list] = None, limit: int = 60):
    """Снимок остатков: дозаказ, неликвиды, склады, группы, перемещение вместо закупки.
    allowed — склады, доступные пользователю (кладовщик — склады своего города); None — все."""
    with analytics.conn() as c:
        _stock_views(c)
        mx = c.execute("SELECT MAX(date) m FROM an_sales").fetchone()["m"]
        last = c.execute("SELECT MAX(ts) t FROM an_loads WHERE kind='stock'").fetchone()["t"]
        orgs = [r["org"] for r in _q(c, "SELECT DISTINCT org FROM v_stock WHERE org<>'' ORDER BY org")]
        whs = [r["warehouse"] for r in _q(c, "SELECT DISTINCT warehouse FROM v_stock WHERE warehouse<>''"
                                             + (" AND org=?" if org else "") + " ORDER BY warehouse",
                                          (org,) if org else ())]
        if allowed is not None:
            whs = [w for w in whs if w in allowed]
        if wh and wh not in whs:
            wh = ""
        scope_whs = [wh] if wh else whs
        if not scope_whs:
            return {"empty": True, "orgs": orgs, "warehouses": whs, "last": last, "wh": wh}
        try:
            anchor = ddate(mx) if mx else date.today()
        except ValueError:
            anchor = date.today()
        cutoff = str(anchor - timedelta(days=ILLIQUID_DAYS))
        has_cost = c.execute("SELECT COUNT(*) n FROM v_stock WHERE cost_sum > 0").fetchone()["n"] > 0
        # стоимость запаса: себестоимость из 1С, а если её нет — оценка по средней цене продаж за 180 дней
        since = str(anchor - timedelta(days=180))
        # себестоимость 1С берётся, если правдоподобна (не больше 5 × оценки по цене продаж) — как у продаж
        SV = ("(SELECT st.*, CASE WHEN st.cost_sum > 0 AND (pr.p IS NULL OR st.cost_sum <= 5 * st.qty * pr.p) "
              "THEN st.cost_sum ELSE st.qty * COALESCE(pr.p, 0) END val "
              "FROM v_stock st LEFT JOIN (SELECT item_key, SUM(sum) / NULLIF(SUM(qty), 0) p FROM v_sales "
              f"WHERE date >= '{since}' AND qty > 0 AND sum > 0 GROUP BY item_key) pr ON pr.item_key = st.item_key)")
        ph = ",".join("?" * len(scope_whs))
        W = f" WHERE warehouse IN ({ph})" + (" AND org=?" if org else "")
        wa = scope_whs + ([org] if org else [])
        ill_cond = "qty>0 AND sold_90=0 AND (last_sale='' OR last_sale<?)"
        reo_cond = "sold_30>0 AND qty < sold_30/30.0*?"

        tot = dict(c.execute("SELECT COUNT(*) n, COALESCE(SUM(val),0) v, COALESCE(SUM(sold_30),0) s30 "
                             "FROM " + SV + W + " AND qty>0", wa).fetchone())
        ill = dict(c.execute(f"SELECT COUNT(*) n, COALESCE(SUM(val),0) v FROM {SV}{W} AND {ill_cond}",
                             wa + [cutoff]).fetchone())
        reo_n = c.execute(f"SELECT COUNT(*) n FROM v_stock{W} AND {reo_cond}", wa + [REORDER_DAYS]).fetchone()["n"]
        reorder = [dict(r) for r in _q(c, f"""SELECT warehouse, item, item_key, item_group, unit, qty, sold_30,
                        qty/(sold_30/30.0) days FROM v_stock{W} AND {reo_cond} ORDER BY days ASC LIMIT ?""",
                                       wa + [REORDER_DAYS, limit])]
        for r in reorder:
            r["need"] = max(0.0, r["sold_30"] / 30.0 * TARGET_DAYS - (r["qty"] or 0))
            # перемещение вместо закупки: на другом складе есть лишнее (больше своих 30 дней)
            src = c.execute("""SELECT warehouse, qty, sold_30 FROM v_stock WHERE item_key=? AND warehouse<>?
                               AND qty - sold_30/30.0*? > ? ORDER BY qty - sold_30 DESC LIMIT 1""",
                            (r["item_key"], r["warehouse"], TARGET_DAYS, r["need"] * 0.5)).fetchone()
            r["move_from"] = dict(src) if src else None
            # где ещё есть остатки этой позиции (другие склады, по убыванию; «лишнее» — больше своих 30 дней)
            others = [dict(x) for x in c.execute(
                """SELECT warehouse, qty, unit, (qty - sold_30/30.0*?) spare FROM v_stock
                   WHERE item_key=? AND warehouse<>? AND qty>0 ORDER BY spare DESC, qty DESC""",
                (TARGET_DAYS, r["item_key"], r["warehouse"]))]
            r["elsewhere"] = sorted(others, key=lambda x: -x["qty"])[:4]
            # план: сначала забрать лишнее с других складов, остальное — закупить
            left, plan = r["need"], []
            for x in others:
                if left < 1:
                    break
                take = min(left, float(int(x["spare"] or 0)))
                if take >= 1:
                    plan.append({"warehouse": x["warehouse"], "qty": take})
                    left -= take
            r["move_plan"] = plan
            r["movable"] = r["need"] - left
            r["buy"] = round(left) if left >= 1 else 0
        illiquid = _q(c, f"""SELECT warehouse, item, item_group, unit, qty, val cost_sum, last_sale FROM {SV}{W}
                             AND {ill_cond} ORDER BY val DESC, qty DESC LIMIT 30""", wa + [cutoff])
        by_wh = _q(c, f"""SELECT warehouse w, COUNT(CASE WHEN qty>0 THEN 1 END) n, COALESCE(SUM(val),0) v,
                          SUM(CASE WHEN {reo_cond} THEN 1 ELSE 0 END) r,
                          SUM(CASE WHEN {ill_cond} THEN 1 ELSE 0 END) i,
                          COALESCE(SUM(CASE WHEN {ill_cond} THEN val END),0) iv
                          FROM {SV}{W} GROUP BY warehouse ORDER BY v DESC""",
                      [REORDER_DAYS, cutoff, cutoff] + wa)
        groups = _q(c, f"""SELECT CASE WHEN item_group='' THEN 'Без группы' ELSE item_group END g,
                           COALESCE(SUM(val),0) v, COUNT(*) n FROM {SV}{W} AND qty>0
                           GROUP BY g ORDER BY v DESC LIMIT 10""", wa)
        mm = abc_minmax(c, scope_whs, org, anchor, SV)
    return {"empty": False, "orgs": orgs, "warehouses": whs, "wh": wh, "last": last, "anchor": anchor, **mm,
            "positions": tot["n"], "value": tot["v"], "ill_n": ill["n"], "ill_v": ill["v"],
            "ill_share": (ill["v"] / tot["v"] * 100) if tot["v"] else 0,
            "reorder_n": reo_n, "reorder": reorder, "illiquid": illiquid, "by_wh": by_wh, "groups": groups,
            "moves": sum(1 for r in reorder if r["move_plan"]), "by_price": not has_cost,
            "buy_rows": [r for r in reorder if r["buy"] > 0],
            "move_rows": [dict(item=r["item"], unit=r["unit"], to=r["warehouse"], src=pl["warehouse"], qty=pl["qty"],
                               group=r["item_group"]) for r in reorder for pl in r["move_plan"]]}


def _abc_marks(rows, key="s"):
    """Буквы ABC по убыванию суммы: A — первые 80%, B — следующие 15%, C — остальное."""
    total = sum(r[key] or 0 for r in rows) or 1
    acc = 0.0
    for r in sorted(rows, key=lambda x: -(x[key] or 0)):
        r["abc"] = "A" if acc < total * 0.8 else ("B" if acc < total * 0.95 else "C")
        acc += r[key] or 0
        r["share"] = (r[key] or 0) / total * 100
    return rows


def abc_minmax(c, whs, org, anchor, SV):
    """ABC каждого склада по продажам за 90 дней (товары и группы) и мин/макс остатка по классу.
    Мин/макс = средние продажи в день (90 дн.) × дни класса (MINMAX_DAYS)."""
    since = str(anchor - timedelta(days=ABC_DAYS))
    ph = ",".join("?" * len(whs))
    wo = " AND org=?" if org else ""
    args = [since] + list(whs) + ([org] if org else [])
    sales = _q(c, f"""SELECT warehouse, item_key, MAX(item) item, MAX(item_group) g, SUM(sum) s, SUM(qty) q
                      FROM v_sales WHERE date >= ? AND warehouse IN ({ph}){wo} AND sum > 0
                      GROUP BY warehouse, item_key""", args)
    per = {}
    for r in sales:
        per.setdefault(r["warehouse"], []).append(dict(r))
    cls = {}
    for w, rows in per.items():
        for r in _abc_marks(rows):
            cls[(w, r["item_key"])] = r["abc"]
    # группы: ABC по всем выбранным складам вместе
    gs = {}
    for r in sales:
        g = r["g"] or "Без группы"
        gs[g] = gs.get(g, 0) + (r["s"] or 0)
    groups_abc = _abc_marks([{"g": g, "s": v} for g, v in gs.items()])
    groups_abc.sort(key=lambda x: -x["s"])
    stock = _q(c, f"""SELECT warehouse, item, item_key, item_group, unit, qty, sold_90, val FROM {SV}
                      WHERE warehouse IN ({ph}){wo}""", list(whs) + ([org] if org else []))
    by_wh, low, high = {}, [], []
    for r in stock:
        w = r["warehouse"]
        k = cls.get((w, r["item_key"]))
        x = by_wh.setdefault(w, {"w": w, "A": 0, "B": 0, "C": 0, "low": 0, "high": 0, "high_v": 0.0})
        if not k:
            continue
        x[k] += 1
        day = (r["sold_90"] or 0) / ABC_DAYS
        if day <= 0:
            continue
        dmin, dmax = MINMAX_DAYS[k]
        qmin, qmax, q = day * dmin, day * dmax, r["qty"] or 0
        unit_v = (r["val"] or 0) / q if q > 0 else 0
        row = {"w": w, "item": r["item"], "group": r["item_group"], "unit": r["unit"], "abc": k, "qty": q,
               "min": qmin, "max": qmax, "days": q / day}
        if q < qmin:
            row["order"] = qmax - q
            low.append(row); x["low"] += 1
        elif q > qmax:
            row["excess"] = q - qmax
            row["excess_v"] = row["excess"] * unit_v
            high.append(row); x["high"] += 1; x["high_v"] += row["excess_v"]
    low.sort(key=lambda r: ("ABC".index(r["abc"]), r["days"]))
    high.sort(key=lambda r: -r["excess_v"])
    abc_wh = sorted(by_wh.values(), key=lambda x: -(x["A"] + x["B"] + x["C"]))
    return {"abc_wh": [x for x in abc_wh if x["A"] + x["B"] + x["C"]], "abc_groups": groups_abc[:14],
            "mm_low": low, "mm_high": high, "mm_low_n": len(low), "mm_high_n": len(high),
            "mm_high_v": sum(r["excess_v"] for r in high), "minmax_days": MINMAX_DAYS}


def _stock_gate(request: Request, want: str = "stock"):
    """→ (ответ-заглушка | None, allowed_warehouses | None, title).
    want: stock — «Склады» (кладовщик видит только свой склад), purchase — «Закупки» (закупщик и руководители)."""
    from . import main as m, access
    if not m.is_staff(request):
        return m.templates.TemplateResponse("login.html", {
            "request": request, "brand": config.BRAND, "company": config.COMPANY, "base": m._root(),
            "b24": True}), None, ""
    s = access.scope(request)
    _MGR.set("")
    deny = lambda text: (m.templates.TemplateResponse("noaccess.html", {
        "request": request, "brand": config.BRAND, "base": m._root(), "title": "Нет доступа", "text": text}), None, "")
    if want == "purchase":
        if s.password or s.full_dash or s.role == "purchaser":
            return None, None, "Закупки"
        return deny("Вкладка «Закупки» — для закупщика и руководителей. Кладовщику — «Мой склад».")
    if s.password or s.full_dash or s.role == "purchaser":
        return None, None, "Склады"
    if s.role == "storekeeper":
        if not s.city:
            return m.templates.TemplateResponse("noaccess.html", {
                "request": request, "brand": config.BRAND, "base": m._root(), "title": "Мой склад",
                "text": "Не удалось определить ваш склад: в названии отдела в Битрикс24 нет города. Администратор может исправить отдел."}), None, ""
        with analytics.conn() as c:
            _stock_views(c)
            whs = [r["warehouse"] for r in c.execute("SELECT DISTINCT warehouse FROM v_stock")
                   if s.city.lower() in (r["warehouse"] or "").lower()]
        return None, whs, f"Мой склад — {s.city}"
    return deny("Вкладка «Склады» — для кладовщиков, закупщика и руководителей.")


def _stock_nav(request: Request):
    from . import access
    s = access.scope(request)
    if s.password or s.full_dash:
        return NAV
    if s.role == "purchaser":
        return [("Аналитика", [("purchase", "Закупки", True), ("stock", "Склады", True)])]
    return [("Аналитика", [("stock", "Мой склад", True)])]


def _stock_page(request: Request, mode: str, org: str, wh: str):
    from . import main as m
    resp, allowed, title = _stock_gate(request, mode)
    if resp:
        return resp
    data = build_stock(org.strip(), wh.strip(), allowed, limit=60 if mode == "stock" else 300)
    return templates.TemplateResponse("dash_stock.html", {
        "request": request, "brand": config.BRAND, "base": m._root(), "p": "month", "org": org, "branch": "",
        "d": "", "periods": periods_all(), "period_title": "", "nav": _stock_nav(request), "tab": mode,
        "page_title": title, "show_branch": False, "data": data, "money": money, "num": num,
        "human_date": human_date, "last_local": _last_local(data.get("last")), "ring": ring_svg,
        "illiquid_days": ILLIQUID_DAYS, "reorder_days": REORDER_DAYS, "target_days": TARGET_DAYS,
        "storekeeper": allowed is not None, "mode": mode,
    })


@router.get("/dash/stock", response_class=HTMLResponse)
def dash_stock(request: Request, org: str = "", wh: str = ""):
    return _stock_page(request, "stock", org, wh)


@router.get("/dash/purchase", response_class=HTMLResponse)
def dash_purchase(request: Request, org: str = "", wh: str = ""):
    return _stock_page(request, "purchase", org, wh)


@router.get("/dash/purchase/order.xlsx")
def dash_order_xlsx(request: Request, org: str = "", wh: str = "", kind: str = "buy"):
    """Excel: заказ поставщику (kind=buy) или заявка на перемещение (kind=move)."""
    from fastapi.responses import Response
    from . import xlsx_out, b24auth
    resp, allowed, title = _stock_gate(request, "purchase" if kind == "buy" else "stock")
    if resp:
        return resp
    data = build_stock(org.strip(), wh.strip(), allowed, limit=5000)
    who = b24auth.me(request)["name"]
    body = xlsx_out.order_book(data, kind, org.strip(), data.get("wh") or ("; ".join(allowed) if allowed else ""), who)
    b24auth.log_access(request, "report", b24auth.current_user(request), f"Excel {kind} {org} {wh}")
    name = ("zakaz_postavshiku_" if kind == "buy" else "peremeshchenie_") + date.today().strftime("%Y%m%d") + ".xlsx"
    return Response(body, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/dash/stock/order.csv")
def dash_stock_csv(request: Request, org: str = "", wh: str = ""):
    """Старая ссылка — теперь Excel."""
    from fastapi.responses import RedirectResponse
    from . import main as m
    import urllib.parse as up
    return RedirectResponse(f"{m._root()}/dash/purchase/order.xlsx?" + up.urlencode({"org": org, "wh": wh}), status_code=303)


# ================================================================== бухгалтер (этап B)
AGING = [(0, 30, "до 30 дн."), (31, 60, "31–60 дн."), (61, 90, "61–90 дн."), (91, 100000, "больше 90 дн.")]


def build_acc(p: str, org: str, branch: str, d: str):
    """Дебиторка и переплаты по филиалам и организациям, возраст долга, поступления по способам
    по филиалам, расходы по статьям ДДС, крупные платежи."""
    with analytics.conn() as c:
        mx, last, orgs = _context(c, org)
        if not mx:
            return {"empty": True, "orgs": orgs, "branches": [], "last": last}
        try:
            anchor = ddate(d) if d else ddate(mx)
        except ValueError:
            anchor = ddate(mx)
        a, b, pa, pb = period_range(p, anchor)
        # 1С не присылает филиал у долгов и оплат — берём филиал, где клиент покупает (больше всего продаж за всю историю)
        cmap = client_branches(c)

        def br_of(b0, key, name=""):
            return b0 or (cmap.get(key) or cmap.get(cname(name)) or ("(не указан)",))[0]

        branches = sorted({v[0] for v in cmap.values()})

        # долги — снимок; свои компании отдельно (как на «Компании»)
        wd, wda = _where(org, "", False, False)
        Wd = (" WHERE " + " AND ".join(wd)) if wd else ""
        rows = []
        for r in _q(c, "SELECT org, branch, client_key, manager, client, debt, prepay, overdue, overdue_days "
                       "FROM an_debts" + Wd, wda):
            r = dict(r)
            r["br"] = br_of(r["branch"], r["client_key"], r["client"])
            if not branch or r["br"] == branch:
                rows.append(r)
        ext = [r for r in rows if not is_internal(r["client"])]
        own = [r for r in rows if is_internal(r["client"])]
        debt = sum(r["debt"] or 0 for r in ext)
        prepay = sum(r["prepay"] or 0 for r in ext)
        by_br = {}
        for r in ext:
            x = by_br.setdefault(r["br"], {"br": r["br"], "debt": 0, "prepay": 0, "n": 0, "over": 0})
            x["debt"] += r["debt"] or 0
            x["prepay"] += r["prepay"] or 0
            x["over"] += r["overdue"] or 0
            x["n"] += 1 if (r["debt"] or 0) > 0 else 0
        by_br = sorted(by_br.values(), key=lambda x: -x["debt"])
        by_org = {}
        for r in ext:
            x = by_org.setdefault(r["org"] or "(не указана)", {"org": r["org"] or "(не указана)", "debt": 0, "prepay": 0})
            x["debt"] += r["debt"] or 0
            x["prepay"] += r["prepay"] or 0
        by_org = sorted(by_org.values(), key=lambda x: -x["debt"])
        has_age = any((r["overdue_days"] or 0) > 0 for r in ext)
        aging = []
        if has_age:
            for lo, hi, title in AGING:
                s = sum(r["debt"] or 0 for r in ext if (r["debt"] or 0) > 0 and lo <= (r["overdue_days"] or 0) <= hi)
                aging.append({"t": title, "s": s})
        overdue = sum(r["overdue"] or 0 for r in ext)
        debtors = sorted([r for r in ext if (r["debt"] or 0) > 0], key=lambda r: -r["debt"])[:20]
        prepays = sorted([r for r in ext if (r["prepay"] or 0) > 0], key=lambda r: -r["prepay"])[:10]

        # поступления по способам и филиалам за период
        wp, wpa = _where(org, "", True, False)
        pay_rows = []
        for r in _q(c, "SELECT branch, client_key, MAX(client) client, kind, SUM(sum) s FROM an_payments WHERE " + " AND ".join(wp)
                    + " GROUP BY branch, client_key, kind", [str(a), str(b)] + wpa):
            br = br_of(r["branch"], r["client_key"], r["client"])
            if not branch or br == branch:
                pay_rows.append({"br": br, "kind": r["kind"], "s": r["s"]})
        prev_total = 0
        for r in _q(c, "SELECT branch, client_key, MAX(client) client, SUM(sum) s FROM an_payments WHERE " + " AND ".join(wp)
                    + " GROUP BY branch, client_key", [str(pa), str(pb)] + wpa):
            if not branch or br_of(r["branch"], r["client_key"], r["client"]) == branch:
                prev_total += r["s"] or 0
        pays = {}
        for r in pay_rows:
            x = pays.setdefault(r["br"], {"br": r["br"], "card": 0, "cash": 0, "bank": 0, "total": 0})
            x[r["kind"]] = (x.get(r["kind"]) or 0) + (r["s"] or 0)
            x["total"] += r["s"] or 0
        pays = sorted(pays.values(), key=lambda x: -x["total"])
        kinds = {k: sum(x[k] for x in pays) for k in ("card", "cash", "bank")}
        pay_total = sum(kinds.values())

        # расходы по статьям ДДС и крупные платежи
        wc, wca = _where(org, "", True, False, False)
        exp_by = _q(c, "SELECT CASE WHEN article='' THEN 'Без статьи' ELSE article END a, SUM(sum) s, COUNT(*) n "
                       "FROM an_cashflow WHERE direction='out' AND " + " AND ".join(wc)
                    + " GROUP BY a ORDER BY s DESC LIMIT 12", [str(a), str(b)] + wca)
        exp = sum(r["s"] or 0 for r in exp_by)
        exp_all = c.execute("SELECT COALESCE(SUM(sum),0) s FROM an_cashflow WHERE direction='out' AND "
                            + " AND ".join(wc), [str(a), str(b)] + wca).fetchone()["s"]
        big = _q(c, "SELECT date, counterparty, article, sum, doc_no FROM an_cashflow WHERE direction='out' AND "
                    + " AND ".join(wc) + " ORDER BY sum DESC LIMIT 10", [str(a), str(b)] + wca)
    return {"empty": False, "orgs": orgs, "branches": branches, "last": last, "anchor": anchor, "max_date": mx,
            "a": a, "b": b, "pa": pa, "pb": pb,
            "debt": debt, "prepay": prepay, "overdue": overdue, "n_debt": sum(1 for r in ext if (r["debt"] or 0) > 0),
            "n_prepay": sum(1 for r in ext if (r["prepay"] or 0) > 0),
            "own_debt": sum(r["debt"] or 0 for r in own), "own_prepay": sum(r["prepay"] or 0 for r in own),
            "by_br": by_br, "by_org": by_org, "aging": aging, "has_age": has_age,
            "debtors": debtors, "prepays": prepays,
            "pays": pays, "kinds": [(k, PAY_LABELS[k], kinds[k]) for k in ("card", "cash", "bank")],
            "pay_total": pay_total, "pay_delta": pct(pay_total, prev_total),
            "exp_by": exp_by, "exp": exp_all, "big": big}


@router.get("/dash/acc", response_class=HTMLResponse)
def dash_acc(request: Request, p: str = "month", org: str = "", branch: str = "", d: str = ""):
    from . import main as m, access
    if not m.is_staff(request):
        return m.templates.TemplateResponse("login.html", {
            "request": request, "brand": config.BRAND, "company": config.COMPANY, "base": m._root(), "b24": True})
    s = access.scope(request)
    _MGR.set("")
    if not (s.password or s.role in ("admin", "director", "accountant")):
        return m.templates.TemplateResponse("noaccess.html", {
            "request": request, "brand": config.BRAND, "base": m._root(), "title": "Нет доступа",
            "text": "Вкладка «Бухгалтер» — для бухгалтера, директора и администратора."})
    if not _valid_p(p):
        p = "month"
    data = build_acc(p, org.strip(), branch.strip(), d.strip())
    nav = NAV if (s.password or s.role in ("admin", "director")) else \
        [("Аналитика", [("acc", "Бухгалтер", True), ("company", "Компания", True), ("branches", "Продажи по филиалам", True)])]
    return templates.TemplateResponse("dash_acc.html", {
        "request": request, "brand": config.BRAND, "base": m._root(), "p": p, "org": org, "branch": branch, "d": d,
        "periods": periods_all(), "period_title": _ptitle(p), "nav": nav, "tab": "acc",
        "page_title": "Бухгалтер", "show_branch": True, "data": data, "money": money, "num": num,
        "human_date": human_date, "last_local": _last_local(data.get("last")), "ring": ring_svg,
    })


@router.get("/dash/acc/report", response_class=HTMLResponse)
def dash_acc_report(request: Request, p: str = "month", org: str = "", branch: str = "", d: str = ""):
    """Красивый отчёт бухгалтера для печати / сохранения в PDF (светлый, A4)."""
    from . import main as m, access, b24auth
    resp = dash_acc(request, p, org, branch, d)
    if getattr(resp, "template", None) is None or resp.template.name != "dash_acc.html":
        return resp
    ctx = resp.context
    tz = timezone(timedelta(hours=config.TZ_OFFSET_HOURS))
    b24auth.log_access(request, "report", b24auth.current_user(request), f"отчёт бухгалтера {ctx['p']} {org} {branch}")
    return templates.TemplateResponse("report_acc.html", {
        **{k: v for k, v in ctx.items() if k != "request"}, "request": request,
        "now": datetime.now(tz).strftime("%d.%m.%Y %H:%M"), "who": b24auth.me(request)["name"],
    })


# ================================================================== деньги и расходы (этап B)
def _series(c, table_sql, args, p, a, b, anchor):
    """Суммы по дням (или месяцам для «Год») → (labels, values)."""
    if _isyear(p):
        ser = {r["k"]: r["s"] for r in _q(c, f"SELECT substr(date,1,7) k, SUM(sum) s FROM {table_sql} GROUP BY k", args)}
        labels = [MONTHS_SHORT[m - 1] for m in range(a.month, b.month + 1)]
        vals = [ser.get(f"{a.year}-{m:02d}", 0) for m in range(a.month, b.month + 1)]
        return labels, vals
    ser = {r["date"]: r["s"] for r in _q(c, f"SELECT date, SUM(sum) s FROM {table_sql} GROUP BY date", args)}
    n = (b - a).days + 1
    days = [a + timedelta(days=i) for i in range(n)]
    return [f"{x.day}.{x.month:02d}" for x in days], [ser.get(str(x), 0) for x in days]


def build_money(p: str, org: str, d: str):
    with analytics.conn() as c:
        mx, last, orgs = _context(c, org)
        if not mx:
            return {"empty": True, "orgs": orgs, "branches": [], "last": last}
        try:
            anchor = ddate(d) if d else ddate(mx)
        except ValueError:
            anchor = ddate(mx)
        a, b, pa, pb = period_range(p, anchor)
        if p in ("today", "yesterday"):          # для графика — две недели
            ga, gb = anchor - timedelta(days=13), anchor
        else:
            ga, gb = a, b
        wc, wca = _where(org, "", True, False, False)
        Wc = " AND ".join(wc)

        def tot(direction, x, y):
            return c.execute(f"SELECT COALESCE(SUM(sum),0) s, COUNT(*) n FROM an_cashflow WHERE direction=? AND {Wc}",
                             [direction, str(x), str(y)] + wca).fetchone()

        cin, cout = tot("in", a, b), tot("out", a, b)
        pin, pout = tot("in", pa, pb), tot("out", pa, pb)
        labels, vin = _series(c, f"an_cashflow WHERE direction='in' AND {Wc}", [str(ga), str(gb)] + wca, p, ga, gb, anchor)
        _l, vout = _series(c, f"an_cashflow WHERE direction='out' AND {Wc}", [str(ga), str(gb)] + wca, p, ga, gb, anchor)
        art = lambda direction, lim: _q(c, "SELECT CASE WHEN article='' THEN 'Без статьи' ELSE article END a, SUM(sum) s, "
                                           f"COUNT(*) n FROM an_cashflow WHERE direction=? AND {Wc} GROUP BY a ORDER BY s DESC LIMIT {lim}",
                                        [direction, str(a), str(b)] + wca)
        out_prev = {r["a"]: r["s"] for r in _q(c, "SELECT CASE WHEN article='' THEN 'Без статьи' ELSE article END a, "
                                                  f"SUM(sum) s FROM an_cashflow WHERE direction='out' AND {Wc} GROUP BY a",
                                               [str(pa), str(pb)] + wca)}
        out_by = [dict(r) | {"delta": pct(r["s"], out_prev.get(r["a"], 0))} for r in art("out", 14)]
        in_by = art("in", 8)
        cps = _q(c, "SELECT CASE WHEN counterparty='' THEN '(не указан)' ELSE counterparty END k, SUM(sum) s, COUNT(*) n "
                    f"FROM an_cashflow WHERE direction='out' AND {Wc} GROUP BY k ORDER BY s DESC LIMIT 12",
                 [str(a), str(b)] + wca)
        by_org = _q(c, "SELECT CASE WHEN org='' THEN '(не указана)' ELSE org END o, "
                       "SUM(CASE WHEN direction='in' THEN sum ELSE 0 END) i, SUM(CASE WHEN direction='out' THEN sum ELSE 0 END) o2 "
                       f"FROM an_cashflow WHERE {Wc} GROUP BY o ORDER BY i DESC", [str(a), str(b)] + wca)
        # поступления от клиентов (оплаты) — для сравнения с ДДС
        wp, wpa = _where(org, "", True, False)
        pays = {r["kind"]: r["s"] for r in _q(c, "SELECT kind, SUM(sum) s FROM an_payments WHERE " + " AND ".join(wp)
                                             + " GROUP BY kind", [str(a), str(b)] + wpa)}
        cf_last = c.execute("SELECT MAX(date) m FROM an_cashflow").fetchone()["m"]
    return {"empty": False, "orgs": orgs, "branches": [], "last": last, "anchor": anchor, "max_date": mx,
            "a": a, "b": b, "pa": pa, "pb": pb, "cf_last": cf_last,
            "in": cin["s"], "out": cout["s"], "net": cin["s"] - cout["s"], "n_out": cout["n"],
            "in_delta": pct(cin["s"], pin["s"]), "out_delta": pct(cout["s"], pout["s"]),
            "net_prev": pin["s"] - pout["s"],
            "chart": chart_svg(labels, vin, vout, w=700, h=330), "out_by": out_by, "in_by": in_by, "cps": cps, "by_org": by_org,
            "pays": [(k, PAY_LABELS[k], pays.get(k, 0)) for k in ("card", "cash", "bank")],
            "pay_total": sum(pays.get(k, 0) for k in ("card", "cash", "bank"))}


@router.get("/dash/money", response_class=HTMLResponse)
def dash_money(request: Request, p: str = "month", org: str = "", d: str = ""):
    from . import main as m, access
    if not m.is_staff(request):
        return m.templates.TemplateResponse("login.html", {
            "request": request, "brand": config.BRAND, "company": config.COMPANY, "base": m._root(), "b24": True})
    s = access.scope(request)
    _MGR.set("")
    if not (s.password or s.role in ("admin", "director", "accountant")):
        return m.templates.TemplateResponse("noaccess.html", {
            "request": request, "brand": config.BRAND, "base": m._root(), "title": "Нет доступа",
            "text": "Вкладка «Деньги и расходы» — для директора, бухгалтера и администратора."})
    if not _valid_p(p):
        p = "month"
    data = build_money(p, org.strip(), d.strip())
    return templates.TemplateResponse("dash_money.html", {
        "request": request, "brand": config.BRAND, "base": m._root(), "p": p, "org": org, "branch": "", "d": d,
        "periods": periods_all(), "period_title": _ptitle(p), "nav": NAV if (s.password or s.role != "accountant") else
        [("Аналитика", [("acc", "Бухгалтер", True), ("money", "Деньги и расходы", True), ("company", "Компания", True)])],
        "tab": "money", "page_title": "Деньги и расходы", "show_branch": False, "data": data, "money": money, "num": num,
        "human_date": human_date, "last_local": _last_local(data.get("last")), "ring": ring_svg,
    })


# ================================================================== менеджер глазами руководителя
@router.get("/dash/mgr", response_class=HTMLResponse)
def dash_mgr(request: Request, p: str = "month", org: str = "", branch: str = "", d: str = "", mg: str = ""):
    """Экран менеджера с выбором менеджера — для админа, директора, РОП."""
    from . import main as m, access
    if not m.is_staff(request):
        return m.templates.TemplateResponse("login.html", {
            "request": request, "brand": config.BRAND, "company": config.COMPANY, "base": m._root(), "b24": True})
    s = access.scope(request)
    if not (s.password or s.role in ("admin", "director", "rop")):
        return m.templates.TemplateResponse("noaccess.html", {
            "request": request, "brand": config.BRAND, "base": m._root(), "title": "Нет доступа",
            "text": "Выбор менеджера — для руководителей. Ваши продажи — в разделе «Аналитика»."})
    with analytics.conn() as c:
        managers = [r["manager"] for r in _q(c, "SELECT manager, SUM(sum) s FROM an_sales WHERE manager<>'' "
                                                "AND date >= ? GROUP BY manager ORDER BY s DESC",
                                             (str(date.today() - timedelta(days=365)),))]
    if not mg and managers:
        mg = managers[0]
    if not _valid_p(p):
        p = "month"
    _MGR.set(mg)
    try:
        data = build(p, org.strip(), branch.strip(), d.strip())
    finally:
        _MGR.set("")
    return templates.TemplateResponse("dash.html", {
        "request": request, "brand": config.BRAND, "base": m._root(), "p": p, "org": org, "branch": branch, "d": d,
        "periods": periods_all(), "period_title": _ptitle(p), "tab": "mgr", "nav": NAV,
        "page_title": f"Менеджер: {mg}" if mg else "Менеджер", "show_branch": True, "limited": True,
        "managers": managers, "mg": mg,
        "data": data, "money": money, "num": num, "human_date": human_date, "last_local": _last_local(data.get("last")),
        "illiquid_days": ILLIQUID_DAYS, "reorder_days": REORDER_DAYS, "ring": ring_svg,
    })


# ================================================================== производство АВТОКОМП (18.10.2026)
PROD_ROLES = ("admin", "director", "rop", "purchaser")
_DONE_STATUS = ("закрыт", "выполнен", "отмен")


def _qty_series(c, where, args, p, a, b):
    """Количество по дням (или месяцам для «Год»)."""
    if _isyear(p):
        ser = {r["k"]: r["s"] for r in _q(c, f"SELECT substr(date,1,7) k, SUM(qty) s FROM an_prod_in WHERE {where} GROUP BY k", args)}
        return ([MONTHS_SHORT[m - 1] for m in range(a.month, b.month + 1)],
                [ser.get(f"{a.year}-{m:02d}", 0) for m in range(a.month, b.month + 1)])
    ser = {r["date"]: r["s"] for r in _q(c, f"SELECT date, SUM(qty) s FROM an_prod_in WHERE {where} GROUP BY date", args)}
    days = [a + timedelta(days=i) for i in range((b - a).days + 1)]
    return [f"{x.day}.{x.month:02d}" for x in days], [ser.get(str(x), 0) for x in days]


OWN_TABLES = ("an_prod_out_avtokomp", "an_prod_out")


def _ton(w, u):
    u = (u or "").strip().lower()
    if u in ("т", "тн", "тонна", "t"):
        return w
    if u in ("г", "гр", "g"):
        return w / 1e6
    return w / 1000.0  # кг (по умолчанию)


def _m2(v, u):
    u = (u or "").strip().lower().replace("²", "2")
    if u in ("см2",):
        return v / 1e4
    if u in ("мм2",):
        return v / 1e6
    return v


def _dept_short(dp):
    d = (dp or "").strip()
    low = d.lower()
    for k, v in (("покраск", "Покраска"), ("ламинац", "Ламинация"), ("хим", "Химобработка алюминия"),
                 ("маркир", "Маркировка и упаковка"), ("упаков", "Маркировка и упаковка"), ("пвх", "ПВХ"),
                 ("алюмин", "Алюминий"), ("производствен", "Производственный отдел")):
        if k in low:
            return v
    return d or "(участок не указан)"


def build_own(c, p, a, b, pa, pb, ga, gb):
    """Выпуск «Производство без заказа» (база АВТОКОМП): штуки/метры, тонны, м² по участкам."""
    tbl = None
    for t in OWN_TABLES:
        try:
            if c.execute(f"SELECT COUNT(*) n FROM {t}").fetchone()["n"]:
                tbl = t
                break
        except Exception:
            continue
    if not tbl:
        return None
    rows = _q(c, f"SELECT date, doc_key, dept, item, item_key, item_group, qty, unit, weight, weight_unit, area, area_unit "
                 f"FROM {tbl} WHERE date BETWEEN ? AND ?", (str(min(pa, ga)), str(max(b, gb))))

    def agg(x, y):
        t = {"qty": 0.0, "t": 0.0, "m2": 0.0, "docs": set(), "dept": {}, "item": {}}
        for r in rows:
            if not (str(x) <= r["date"] <= str(y)):
                continue
            q, tn, m2 = r["qty"] or 0, _ton(r["weight"] or 0, r["weight_unit"]), _m2(r["area"] or 0, r["area_unit"])
            t["qty"] += q; t["t"] += tn; t["m2"] += m2; t["docs"].add(r["doc_key"])
            dp = t["dept"].setdefault(_dept_short(r["dept"]), {"qty": 0.0, "t": 0.0, "m2": 0.0, "docs": set()})
            dp["qty"] += q; dp["t"] += tn; dp["m2"] += m2; dp["docs"].add(r["doc_key"])
            it = t["item"].setdefault(r["item_key"] or r["item"], {"item": r["item"], "unit": r["unit"] or "",
                                                                   "qty": 0.0, "t": 0.0, "m2": 0.0, "group": r["item_group"] or ""})
            it["qty"] += q; it["t"] += tn; it["m2"] += m2
        return t

    cur, prev = agg(a, b), agg(pa, pb)

    def series(x, y):
        if _isyear(p):
            labs = [MONTHS_SHORT[m - 1] for m in range(x.month, y.month + 1)]
            keys = [f"{x.year}-{m:02d}" for m in range(x.month, y.month + 1)]
            cut = 7
        else:
            days = [x + timedelta(days=i) for i in range((y - x).days + 1)]
            labs, keys, cut = [f"{dd.day}.{dd.month:02d}" for dd in days], [str(dd) for dd in days], 10
        acc = {}
        for r in rows:
            if str(x) <= r["date"] <= str(y):
                acc[r["date"][:cut]] = acc.get(r["date"][:cut], 0) + _m2(r["area"] or 0, r["area_unit"])
        return labs, [acc.get(k, 0) for k in keys]

    labels, vals = series(ga, gb)
    if _isyear(p):
        _l, pvals = series(ga.replace(year=ga.year - 1), gb.replace(year=gb.year - 1))
    else:
        sh = timedelta(days=len(labels))
        _l, pvals = series(ga - sh, gb - sh)
    depts = []
    for k, v in sorted(cur["dept"].items(), key=lambda kv: -kv[1]["m2"] - kv[1]["t"]):
        pv = prev["dept"].get(k, {"qty": 0, "t": 0, "m2": 0})
        depts.append({"k": k, "qty": v["qty"], "t": v["t"], "m2": v["m2"], "docs": len(v["docs"]),
                      "d_m2": pct(v["m2"], pv["m2"]), "d_t": pct(v["t"], pv["t"])})
    items = sorted(cur["item"].values(), key=lambda r: -r["m2"] - r["t"] * 10)[:20]
    last = c.execute(f"SELECT MAX(date) m, MIN(date) n FROM {tbl}").fetchone()
    return {"qty": cur["qty"], "t": cur["t"], "m2": cur["m2"], "docs": len(cur["docs"]),
            "d_qty": pct(cur["qty"], prev["qty"]), "d_t": pct(cur["t"], prev["t"]), "d_m2": pct(cur["m2"], prev["m2"]),
            "depts": depts, "items": items, "chart": chart_svg(labels, vals, pvals, w=700, h=330, unit="м²"),
            "last": last["m"], "first": last["n"], "src": tbl}


def build_prod(p: str, org: str, d: str):
    with analytics.conn() as c:
        mx, last, orgs = _context(c, org)
        has = {k: c.execute(f"SELECT COUNT(*) n FROM {t}").fetchone()["n"]
               for k, t in (("in", "an_prod_in"), ("orders", "an_prod_orders"), ("raw", "an_prod_raw"))}
        own_any = 0
        for t in OWN_TABLES:
            try:
                own_any += c.execute(f"SELECT COUNT(*) n FROM {t}").fetchone()["n"]
            except Exception:
                pass
        if not any(has.values()) and not own_any:
            return {"empty": True, "orgs": orgs, "branches": [], "last": last}
        today = date.today()
        try:
            anchor = ddate(d) if d else today
        except ValueError:
            anchor = today
        a, b, pa, pb = period_range(p, anchor)
        ga, gb = (anchor - timedelta(days=13), anchor) if p in ("today", "yesterday") else (a, b)
        W = "date BETWEEN ? AND ?" + (" AND org=?" if org else "")
        wa = lambda x, y: [str(x), str(y)] + ([org] if org else [])
        units = {r["item_key"]: r["unit"] for r in _q(c, "SELECT item_key, MAX(unit) unit FROM an_stock GROUP BY item_key")}

        def tot(x, y):
            return c.execute(f"SELECT COALESCE(SUM(qty),0) q, COUNT(DISTINCT doc_key) n, COUNT(DISTINCT item_key) i "
                             f"FROM an_prod_in WHERE {W}", wa(x, y)).fetchone()

        cur, prev = tot(a, b), tot(pa, pb)
        own = build_own(c, p, a, b, pa, pb, ga, gb)
        labels, vals = _qty_series(c, W, wa(ga, gb), p, ga, gb)
        n = len(labels)
        if _isyear(p):
            _l, pvals = _qty_series(c, W, wa(ga.replace(year=ga.year - 1), gb.replace(year=gb.year - 1)), p,
                                    ga.replace(year=ga.year - 1), gb.replace(year=gb.year - 1))
        else:
            shift = timedelta(days=n)
            _l, pvals = _qty_series(c, W, wa(ga - shift, gb - shift), p, ga - shift, gb - shift)
        by_item = [dict(r) | {"unit": units.get(r["item_key"], "")} for r in
                   _q(c, f"SELECT item, item_key, SUM(qty) s, COUNT(DISTINCT color) nc FROM an_prod_in WHERE {W} "
                         "GROUP BY item_key ORDER BY s DESC LIMIT 15", wa(a, b))]
        by_color = _q(c, f"SELECT CASE WHEN color='' THEN 'без цвета' ELSE color END k, SUM(qty) s FROM an_prod_in "
                         f"WHERE {W} GROUP BY k ORDER BY s DESC LIMIT 12", wa(a, b))
        partners = [r["partner"] for r in _q(c, "SELECT partner, SUM(qty) s FROM an_prod_in WHERE partner<>'' "
                                                "GROUP BY partner ORDER BY s DESC LIMIT 5")]
        # заказы переработчику: в работе — поступило меньше заказанного и статус не «закрыт/выполнен»
        Wo = " AND org=?" if org else ""
        orders = {}
        for r in _q(c, f"SELECT * FROM an_prod_orders WHERE 1=1{Wo}", [org] if org else []):
            o = orders.setdefault(r["order_key"] or r["order_no"], {
                "no": r["order_no"], "date": r["order_date"], "partner": r["partner"], "status": r["status"],
                "qty": 0.0, "qty_in": 0.0, "due": "", "n": 0, "items": []})
            o["qty"] += r["qty"] or 0
            o["qty_in"] += min(r["qty_in"] or 0, r["qty"] or 0)
            o["n"] += 1
            if r["due_date"] and (not o["due"] or r["due_date"] < o["due"]):
                o["due"] = r["due_date"]
            if (r["qty_in"] or 0) < (r["qty"] or 0) - 1e-6:
                o["items"].append(f"{r['item']}{(' · ' + r['color']) if r['color'] else ''}: "
                                  f"{num((r['qty'] or 0) - (r['qty_in'] or 0))}")
        work = []
        for o in orders.values():
            st = (o["status"] or "").lower()
            if o["qty_in"] >= o["qty"] - 1e-6 or any(x in st for x in _DONE_STATUS):
                continue
            o["left"] = o["qty"] - o["qty_in"]
            o["pct"] = o["qty_in"] / o["qty"] * 100 if o["qty"] else 0
            o["late"] = bool(o["due"] and o["due"] < str(today))
            o["late_days"] = (today - ddate(o["due"])).days if o["late"] else 0
            work.append(o)
        work.sort(key=lambda o: (not o["late"], o["due"] or "9999", o["date"] or ""))
        raw = [dict(r) | {"unit": units.get(r["item_key"], "")} for r in
               _q(c, "SELECT item, item_key, color, SUM(qty) q FROM an_prod_raw GROUP BY item_key, color "
                     "HAVING q > 0 ORDER BY q DESC LIMIT 40")]
        raw_tot = c.execute("SELECT COALESCE(SUM(qty),0) q, COUNT(*) n FROM an_prod_raw WHERE qty > 0").fetchone()
        last_in = c.execute("SELECT MAX(date) m FROM an_prod_in").fetchone()["m"]
        loaded = c.execute("SELECT MAX(ts) t FROM an_loads WHERE kind LIKE 'prod_%'").fetchone()["t"]
    return {"empty": False, "orgs": orgs, "branches": [], "last": loaded or last, "anchor": anchor, "max_date": mx,
            "a": a, "b": b, "pa": pa, "pb": pb, "has": has,
            "qty": cur["q"], "docs": cur["n"], "items": cur["i"], "qty_delta": pct(cur["q"], prev["q"]),
            "chart": chart_svg(labels, vals, pvals, w=700, h=330, unit=""), "by_item": by_item, "by_color": by_color,
            "partners": partners, "work": work, "n_work": len(work),
            "in_work": [o for o in work if o["qty_in"] > 1e-6], "queue": [o for o in work if o["qty_in"] <= 1e-6], "n_late": sum(1 for o in work if o["late"]),
            "left": sum(o["left"] for o in work), "raw": raw, "raw_qty": raw_tot["q"], "raw_n": raw_tot["n"],
            "last_in": last_in, "own": own}


@router.get("/dash/prod", response_class=HTMLResponse)
def dash_prod(request: Request, p: str = "month", org: str = "", d: str = ""):
    from . import main as m, access
    if not m.is_staff(request):
        return m.templates.TemplateResponse("login.html", {
            "request": request, "brand": config.BRAND, "company": config.COMPANY, "base": m._root(), "b24": True})
    s = access.scope(request)
    _MGR.set("")
    if not (s.password or s.role in PROD_ROLES):
        return m.templates.TemplateResponse("noaccess.html", {
            "request": request, "brand": config.BRAND, "base": m._root(), "title": "Нет доступа",
            "text": "Вкладка «Производство АВТОКОМП» — для директора, РОП, закупщика и администратора."})
    if not _valid_p(p):
        p = "month"
    data = build_prod(p, org.strip(), d.strip())
    return templates.TemplateResponse("dash_prod.html", {
        "request": request, "brand": config.BRAND, "base": m._root(), "p": p, "org": org, "branch": "", "d": d,
        "periods": periods_all(), "period_title": _ptitle(p), "nav": NAV,
        "tab": "prod", "page_title": "Производство АВТОКОМП", "show_branch": False, "data": data, "money": money,
        "num": num, "human_date": human_date, "last_local": _last_local(data.get("last")), "ring": ring_svg,
    })


# ================================================================== история по годам (6л, 18.10.2026)
HISTORY_ROLES = ("admin", "director", "rop", "accountant")
RECON_TITLES = {"sales": "Продажи (БП реализации ↔ УНФ расходные)", "purchases": "Закупки (БП поступления ↔ УНФ приходные)",
                "cash_in": "Поступления денег", "cash_out": "Расходы денег"}


def _has_table(c, t):
    return bool(c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone())


def build_history(y: str):
    """Помесячно за год: продажи, закупки, расход материалов, деньги. До начала базы КА — данные старых БП/УНФ
    (таблицы *_legacy, сверены legacy/build.py), с начала КА — текущие выгрузки."""
    with analytics.conn() as c:
        L = {k: _has_table(c, f"an_{k}_legacy") for k in ("sales", "purchases", "materials", "cashflow")}
        ka_first = (c.execute("SELECT MIN(date) m FROM an_sales").fetchone()["m"] or "9999")[:7]
        years = set()
        for t in ("an_sales", "an_cashflow") + tuple(f"an_{k}_legacy" for k, v in L.items() if v):
            for r in _q(c, f"SELECT DISTINCT substr(date,1,4) y FROM {t} WHERE date<>''"):
                if r["y"] and r["y"][:2] in ("19", "20"):
                    years.add(r["y"])
        years = sorted(years)
        if not years:
            return {"empty": True, "orgs": [], "branches": [], "last": None}
        if y not in years:
            y = years[-1] if years[-1] < str(date.today().year) or len(years) == 1 else years[-1]
        py = str(int(y) - 1)

        def monthly(t, expr, where="", yy=y):
            if not _has_table(c, t):
                return {}
            return {r["m"]: r["s"] or 0 for r in _q(c, f"SELECT substr(date,1,7) m, SUM({expr}) s FROM {t} "
                                                       f"WHERE substr(date,1,4)=? {where} GROUP BY m", (yy,))}

        def series(yy):
            s_leg, s_ka = monthly("an_sales_legacy", "sum", yy=yy), monthly("an_sales", "sum", yy=yy)
            pur = monthly("an_purchases_legacy", "sum", yy=yy)
            mat_u = monthly("an_materials_legacy", "sum", "AND base='unf'", yy=yy)
            mat_b = monthly("an_materials_legacy", "sum", "AND base='bp'", yy=yy)
            cin = monthly("an_cashflow_legacy", "sum", "AND direction='in' AND article<>'Внутреннее перемещение'", yy=yy)
            cout = monthly("an_cashflow_legacy", "sum", "AND direction='out' AND article<>'Внутреннее перемещение'", yy=yy)
            kin = monthly("an_cashflow", "sum", "AND direction='in'", yy=yy)
            kout = monthly("an_cashflow", "sum", "AND direction='out'", yy=yy)
            res = []
            for mth in range(1, 13):
                k = f"{yy}-{mth:02d}"
                ka = k >= ka_first
                res.append({"m": k, "label": MONTHS_SHORT[mth - 1], "src": "КА" if ka else "БП/УНФ",
                            "sales": s_ka.get(k, 0) if ka else s_leg.get(k, 0),
                            "purch": None if ka else pur.get(k, 0),
                            "mat": None if ka else (mat_u.get(k, 0) or mat_b.get(k, 0)),
                            "mat_src": "" if ka else ("УНФ" if mat_u.get(k) else ("БП" if mat_b.get(k) else "")),
                            "cin": kin.get(k, 0) if ka else cin.get(k, 0), "cout": kout.get(k, 0) if ka else cout.get(k, 0)})
            return res

        cur, prev = series(y), series(py)
        tot = lambda s, f: sum((x[f] or 0) for x in s)
        T = {f: tot(cur, f) for f in ("sales", "purch", "mat", "cin", "cout")}
        TP = {f: tot(prev, f) for f in ("sales", "purch", "mat", "cin", "cout")}
        for i, x in enumerate(cur):
            x["d_sales"] = pct(x["sales"], prev[i]["sales"])
            x["net"] = (x["cin"] or 0) - (x["cout"] or 0)
        top = lambda t, col, where="": (_q(c, f"SELECT {col} k, SUM(sum) s, COUNT(DISTINCT doc_key) n FROM {t} WHERE "
                                             f"substr(date,1,4)=? AND {col}<>'' {where} GROUP BY {col} ORDER BY s DESC LIMIT 12", (y,))
                                        if _has_table(c, t) else [])
        clients = top("an_sales_legacy", "client") if y < ka_first[:4] else top("an_sales", "client")
        suppliers = top("an_purchases_legacy", "supplier", "AND kind IN ('goods','services')")
        mats = top("an_materials_legacy", "item")
        recon, diff_n = [], {}
        if _has_table(c, "an_legacy_recon"):
            for r in _q(c, "SELECT kind, SUM(bp_n) bp_n, SUM(bp_sum) bp_sum, SUM(unf_n) unf_n, SUM(unf_sum) unf_sum, "
                           "SUM(matched) matched, SUM(only_bp_n) obn, SUM(only_bp_sum) obs, SUM(only_unf_n) oun, "
                           "SUM(only_unf_sum) ous FROM an_legacy_recon WHERE substr(month,1,4)=? GROUP BY kind", (y,)):
                recon.append(dict(r) | {"title": RECON_TITLES.get(r["kind"], r["kind"])})
            recon.sort(key=lambda r: list(RECON_TITLES).index(r["kind"]) if r["kind"] in RECON_TITLES else 9)
        built = None
        for r in _q(c, "SELECT ts, body FROM an_meta ORDER BY id DESC LIMIT 30"):
            if '"legacy_build"' in r["body"]:
                built = r["ts"]
                break
        labels = [x["label"] for x in cur]
    return {"empty": False, "orgs": [], "branches": [], "last": built, "y": y, "py": py, "years": years,
            "cur": cur, "T": T, "TP": TP, "d": {f: pct(T[f], TP[f]) for f in T}, "ka_first": ka_first,
            "chart": chart_svg(labels, [x["sales"] for x in cur], [x["sales"] for x in prev], w=700, h=330),
            "clients": clients, "suppliers": suppliers, "mats": mats, "recon": recon, "has_legacy": any(L.values()),
            "anchor": date(int(y), 12, 31), "a": date(int(y), 1, 1), "b": date(int(y), 12, 31),
            "pa": date(int(py), 1, 1), "pb": date(int(py), 12, 31)}


@router.get("/dash/history", response_class=HTMLResponse)
def dash_history(request: Request, y: str = "", p: str = "year", org: str = "", d: str = ""):
    from . import main as m, access
    if not m.is_staff(request):
        return m.templates.TemplateResponse("login.html", {
            "request": request, "brand": config.BRAND, "company": config.COMPANY, "base": m._root(), "b24": True})
    s = access.scope(request)
    _MGR.set("")
    if not (s.password or s.role in HISTORY_ROLES):
        return m.templates.TemplateResponse("noaccess.html", {
            "request": request, "brand": config.BRAND, "base": m._root(), "title": "Нет доступа",
            "text": "История по годам — для директора, РОП, бухгалтера и администратора."})
    data = build_history(y.strip())
    return templates.TemplateResponse("dash_history.html", {
        "request": request, "brand": config.BRAND, "base": m._root(), "p": "year", "org": "", "branch": "", "d": "",
        "periods": periods_all(), "period_title": data.get("y", ""), "nav": NAV, "tab": "history",
        "page_title": "История по годам", "show_branch": False, "data": data, "money": money, "num": num,
        "human_date": human_date, "last_local": _last_local(data.get("last")), "ring": ring_svg, "pct": pct,
    })


@router.get("/dash/history/diff.xlsx")
def dash_history_diff(request: Request, y: str = ""):
    """Excel: документы, которые есть только в одной из баз (БП или УНФ), — для проверки бухгалтером."""
    from . import main as m, access, xlsx_out
    from fastapi.responses import Response
    if not m.is_staff(request):
        return Response(status_code=401)
    s = access.scope(request)
    if not (s.password or s.role in HISTORY_ROLES):
        return Response(status_code=403)
    with analytics.conn() as c:
        rows = _q(c, "SELECT kind, base, date, doc_no, client, sum, doc FROM an_legacy_diff "
                     + ("WHERE substr(date,1,4)=? " if y else "") + "ORDER BY kind, date", (y,) if y else ()) \
            if _has_table(c, "an_legacy_diff") else []
    from . import b24auth
    rep = {"title": f"Сверка БП ↔ УНФ: документы только в одной базе{(' — ' + y) if y else ''}", "kick": "EDO.ANESCOM · история",
           "sub": ["Старые базы: Бухгалтерия 3.0 (БК ТОО ANESCOM 63.1) и УНФ 1.6",
                   "Сопоставление: дата + сумма + БИН, затем дата + номер, затем сумма + БИН ±3 дня"], "kpis": [], "tables": [{
        "title": "Расхождения", "cols": [("Раздел", "text", 26), ("Где есть", "text", 10), ("Дата", "text", 11),
                                         ("Номер", "text", 16), ("Контрагент", "text", 40), ("Сумма, ₸", "money", 16),
                                         ("Документ 1С", "text", 30)],
        "rows": [[RECON_TITLES.get(r["kind"], r["kind"]), "только БП" if r["base"] == "bp" else "только УНФ", r["date"],
                  r["doc_no"], r["client"], float(r["sum"] or 0), r["doc"]] for r in rows]}]}
    data = xlsx_out.report_book(rep, b24auth.me(request)["name"])
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename=sverka_bp_unf{('_' + y) if y else ''}.xlsx"})
