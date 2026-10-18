"""Портал v4, этап B: дашборды по данным 1С (база analytics.sqlite3, см. app/analytics.py).

Маршрут /dash?p=<period>&org=&branch=&d=YYYY-MM-DD — экран «Компания» (директор / администратор).
Вход — пока общим паролем кабинета (is_staff); вход из Битрикс24 и роли — этап A, часть 2.
Администратор видит все вкладки (решение пользователя 18.10 10:04); вкладки других ролей
добавляются по мере готовности, ещё не готовые показаны в меню серым.

Опорная дата: по умолчанию — последняя дата продаж в выгрузке (в копии базы данные старые,
поэтому «сегодня» по календарю было бы пустым). Её можно задать параметром d.
"""
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from . import analytics, config

router = APIRouter()
templates = Jinja2Templates(directory=str(config.BASE_DIR / "app" / "templates"))

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
                   ("stock", "Склады и закупки", False), ("money", "Деньги и расходы", False),
                   ("debts", "Долги и переплаты", False)]),
    ("Роли", [("manager", "Менеджер", False), ("storekeeper", "Кладовщик", False),
              ("purchaser", "Закупщик", False), ("accountant", "Бухгалтер", False), ("rop", "РОП", False)]),
]


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


# ------------------------------------------------------------------ периоды
def period_range(p: str, anchor: date):
    """Текущий период и предыдущий такой же длины."""
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
def _where(org: str, branch: str, dated: bool = True, has_branch: bool = True):
    w, args = [], []
    if dated:
        w.append("date BETWEEN ? AND ?")
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
        wc, wca = _where(org, "", True, False)
        exp = c.execute("SELECT COALESCE(SUM(sum),0) s FROM an_cashflow WHERE direction='out' AND "
                        + " AND ".join(wc), [str(a), str(b)] + wca).fetchone()["s"]
        exp_prev = c.execute("SELECT COALESCE(SUM(sum),0) s FROM an_cashflow WHERE direction='out' AND "
                             + " AND ".join(wc), [str(pa), str(pb)] + wca).fetchone()["s"]
        exp_by = _q(c, "SELECT CASE WHEN article='' THEN 'Без статьи' ELSE article END a, SUM(sum) s FROM an_cashflow "
                       "WHERE direction='out' AND " + " AND ".join(wc) + " GROUP BY a ORDER BY s DESC LIMIT 8",
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

        # график
        if p == "year":
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
        ws, wsa = _where(org, branch, False, True)
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
        "by_branch": by_branch, "top": top,
        "chart": chart_svg(labels, cv, pv),
        "illiquid": illiquid, "ill_n": ill_n, "reorder": reorder, "reorder_n": reorder_n,
    }


# ------------------------------------------------------------------ графики (SVG на сервере, без библиотек)
def chart_svg(labels, cur, prev, w=1200, h=300):
    """Столбцы текущего периода (свечение) + пунктир прошлого периода. Тёмная тема."""
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
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Выручка: текущий и прошлый период" '
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
                   f'fill="url(#gb)"><title>{labels[i]}: {money(v, False)} ₸</title></rect>')
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
        if p == "year":
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
            "chart": lines_svg(labels, series), "managers": managers, "groups": groups, "pay_rows": pay_rows}


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


@router.get("/dash/branches", response_class=HTMLResponse)
def dash_branches(request: Request, p: str = "month", org: str = "", d: str = ""):
    from . import main as m
    if not m.is_staff(request):
        return m.templates.TemplateResponse("login.html", {
            "request": request, "brand": config.BRAND, "company": config.COMPANY, "base": m._root()})
    if p not in dict(PERIODS):
        p = "month"
    data = build_branches(p, org.strip(), d.strip())
    return templates.TemplateResponse("dash_branches.html", {
        "request": request, "brand": config.BRAND, "base": m._root(), "p": p, "org": org, "branch": "", "d": d,
        "periods": PERIODS, "period_title": PERIOD_TITLES[p], "nav": NAV, "tab": "branches",
        "page_title": "Продажи по филиалам", "show_branch": False,
        "data": data, "money": money, "num": num, "human_date": human_date, "last_local": _last_local(data.get("last")),
        "ring": ring_svg,
    })


@router.get("/dash", response_class=HTMLResponse)
def dash(request: Request, p: str = "month", org: str = "", branch: str = "", d: str = ""):
    from . import main as m  # поздний импорт: main подключает этот роутер
    if not m.is_staff(request):
        return m.templates.TemplateResponse("login.html", {
            "request": request, "brand": config.BRAND, "company": config.COMPANY, "base": m._root()})
    if p not in dict(PERIODS):
        p = "month"
    data = build(p, org.strip(), branch.strip(), d.strip())
    tz = timezone(timedelta(hours=config.TZ_OFFSET_HOURS))
    last_local = ""
    if data.get("last"):
        try:
            last_local = datetime.fromisoformat(data["last"]).astimezone(tz).strftime("%d.%m %H:%M")
        except ValueError:
            last_local = data["last"]
    return templates.TemplateResponse("dash.html", {
        "request": request, "brand": config.BRAND, "base": m._root(), "p": p, "org": org, "branch": branch, "d": d,
        "periods": PERIODS, "period_title": PERIOD_TITLES[p], "nav": NAV, "tab": "company",
        "page_title": "Компания", "show_branch": True,
        "data": data, "money": money, "num": num, "human_date": human_date, "last_local": last_local,
        "illiquid_days": ILLIQUID_DAYS, "reorder_days": REORDER_DAYS, "ring": ring_svg,
    })
