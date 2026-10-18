"""Отчёты каждой вкладки аналитики: для печати / PDF (report.html) и в Excel (xlsx_out.report_book).

/dash/report?tab=company|mgr|branches|stock|purchase|money|acc&fmt=html|xlsx&<те же отборы, что у вкладки>
Права те же, что у вкладки: отчёт строится вызовом самой вкладки, поэтому менеджер получает
только свои продажи, кладовщик — только свой склад.
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from . import config

router = APIRouter()

TAB_TITLES = {"company": "Компания", "mgr": "Менеджер", "branches": "Продажи по филиалам", "stock": "Склад",
              "purchase": "Закупки", "money": "Деньги и расходы", "acc": "Бухгалтер: долги, поступления, расходы",
              "prod": "Производство АВТОКОМП"}


def _period(ctx) -> list:
    D = ctx["data"]
    out = []
    if D.get("a"):
        p = f"{ctx.get('period_title', '').capitalize()}: {D['a']:%d.%m.%Y}"
        if D["a"] != D["b"]:
            p += f" – {D['b']:%d.%m.%Y}"
        out.append(p)
    flt = []
    if ctx.get("org"):
        flt.append(f"организация {ctx['org']}")
    if ctx.get("branch"):
        flt.append(f"филиал {ctx['branch']}")
    if D.get("wh"):
        flt.append(f"склад {D['wh']}")
    if ctx.get("mg"):
        flt.append(f"менеджер {ctx['mg']}")
    out.append("Отбор: " + (", ".join(flt) if flt else "все данные"))
    return out


def _f(v):
    return float(v or 0)


def fv(v, kind: str) -> str:
    """Значение ячейки для печатного отчёта."""
    if v is None or v == "":
        return "—" if kind != "text" else ""
    if kind == "text":
        return str(v)
    if kind == "pct":
        return f"{v:+.0f}%".replace("+", "▲ ").replace("-", "▼ ") if abs(v) < 10000 else "—"
    if kind == "money":
        return f"{v:,.0f}".replace(",", "\u202f")
    if kind == "int":
        return f"{v:,.0f}".replace(",", "\u202f")
    return (f"{v:,.2f}".rstrip("0").rstrip(".")).replace(",", "\u202f")


def build(tab: str, ctx: dict) -> dict:
    D = ctx["data"]
    title = ctx.get("page_title") or TAB_TITLES.get(tab, "Отчёт")
    rep = {"kick": "EDO.ANESCOM · отчёт", "title": title, "sub": _period(ctx), "kpis": [], "tables": [], "notes": []}
    T = rep["tables"].append
    if D.get("empty"):
        rep["notes"].append("Данных из 1С по отбору нет.")
        return rep

    if tab in ("company", "mgr"):
        rep["kpis"] = [("Выручка, ₸", _f(D["cur"]["s"]), ""), ("Прошлый период, ₸", _f(D["prev"]["s"]), ""),
                       ("Документов продажи", D["cur"]["n"], ""), ("Клиентов", D["cur"]["k"], ""),
                       ("Поступило оплат, ₸", _f(D["pay_total"]), ""), ("Нам должны, ₸", _f(D["debt"]), "red"),
                       ("Переплаты клиентов, ₸", _f(D["prepay"]), "")]
        if D.get("gross") is not None:
            rep["kpis"].insert(2, ("Валовая прибыль, ₸", _f(D["gross"]), ""))
        if not ctx.get("limited"):
            rep["kpis"].append(("Расходы (ДДС), ₸", _f(D["exp"]), "red"))
        T({"title": "Оплаты по способам", "cols": [("Способ", "text", 24), ("Сумма, ₸", "money", 16)],
           "rows": [[label, _f(v)] for _k, label, v in D["pays"]], "total": ["Итого", _f(D["pay_total"])]})
        T({"title": "Продажи по филиалам", "cols": [("Филиал", "text", 30), ("Выручка, ₸", "money", 16), ("Документов", "int", 12)],
           "rows": [[r["br"], _f(r["s"]), r["n"]] for r in D["by_branch"]]})
        for x in D.get("abc") or []:
            T({"title": f"ABC: группа {x['k']} — {x['title']} ({x['n']} поз., {x['share']:.0f}% выручки)",
               "cols": [("Номенклатура", "text", 50), ("Группа", "text", 22), ("Кол-во", "num", 10), ("Сумма, ₸", "money", 16)],
               "rows": [[r["item"], r["g"] or "", _f(r["q"]), _f(r["s"])] for r in x["items"]],
               "total": ["Итого", None, None, _f(x["s"])], "max_html": 30})
        T({"title": "Кто должен (топ)", "cols": [("Клиент", "text", 40), ("Менеджер", "text", 26), ("Долг, ₸", "money", 16)],
           "rows": [[r["client"], r["manager"] or "", _f(r["debt"])] for r in D["debtors"]]})
        T({"title": "Переплаты (топ)", "cols": [("Клиент", "text", 40), ("Менеджер", "text", 26), ("Переплата, ₸", "money", 16)],
           "rows": [[r["client"], r["manager"] or "", _f(r["prepay"])] for r in D["prepays"]]})
        if not ctx.get("limited") and D.get("exp_by"):
            T({"title": "Куда ушли деньги", "cols": [("Статья ДДС", "text", 40), ("Сумма, ₸", "money", 16)],
               "rows": [[r["a"], _f(r["s"])] for r in D["exp_by"]], "total": ["Итого", _f(D["exp"])]})

    elif tab == "branches":
        rep["kpis"] = [("Выручка, ₸", _f(D["total"]), ""), ("Прошлый период, ₸", _f(D["total_prev"]), ""),
                       ("Филиалов с продажами", D["n_branches"], "")]
        T({"title": "Филиалы", "cols": [("Филиал", "text", 28), ("Выручка, ₸", "money", 16), ("Прошлый, ₸", "money", 16),
                                        ("Изменение", "pct", 11), ("Доля", "pct", 9), ("Документов", "int", 11),
                                        ("Клиентов", "int", 10), ("Средний чек, ₸", "money", 14), ("Маржа", "pct", 9)],
           "rows": [[r["br"], _f(r["s"]), _f(r["prev"]), r["delta"], r["share"], r["n"], r["k"], _f(r["avg"]), r["margin"]]
                    for r in D["rows"]],
           "total": ["Итого", _f(D["total"]), _f(D["total_prev"]), D["total_delta"], 100.0, None, None, None, None]})
        T({"title": "Менеджеры (топ-10)", "cols": [("Менеджер", "text", 32), ("Филиал", "text", 24), ("Выручка, ₸", "money", 16), ("Документов", "int", 11)],
           "rows": [[r["m"], r["br"], _f(r["s"]), r["n"]] for r in D["managers"]]})
        T({"title": "Группы товаров", "cols": [("Группа", "text", 36), ("Выручка, ₸", "money", 16)],
           "rows": [[r["g"], _f(r["s"])] for r in D["groups"]]})
        T({"title": "Оплаты по филиалам", "cols": [("Филиал", "text", 28), ("Карта", "money", 14), ("Наличные", "money", 14), ("Безнал", "money", 14), ("Итого", "money", 15)],
           "rows": [[r["br"], _f(r["card"]), _f(r["cash"]), _f(r["bank"]), _f(r["t"])] for r in D["pay_rows"]]})

    elif tab in ("stock", "purchase"):
        rep["sub"] = [f"Остатки 1С на {D['anchor']:%d.%m.%Y}" if D.get("anchor") else "Остатки 1С"] + rep["sub"][-1:]
        rep["kpis"] = [("Позиций в наличии", D["positions"], ""),
                       ("Запасы (оценка по ценам продаж), ₸" if D["by_price"] else "Запасы по себестоимости, ₸", _f(D["value"]), ""),
                       ("Заканчивается (запас < 14 дн.)", D["reorder_n"], "red"),
                       ("Неликвид, позиций", D["ill_n"], ""), ("Заморожено в неликвиде, ₸", _f(D["ill_v"]), "")]
        if tab == "purchase":
            T({"title": "Закупить у поставщика", "cols": [("Номенклатура", "text", 48), ("Склад", "text", 22), ("Ед.", "text", 6),
                                                         ("Остаток", "num", 10), ("Хватит, дн.", "int", 9), ("Нужно", "num", 10),
                                                         ("С других складов", "num", 11), ("Закупить", "num", 11)],
               "rows": [[r["item"], r["warehouse"], r["unit"] or "", _f(r["qty"]), round(r["days"] or 0), _f(r["need"]),
                         _f(r["movable"]), _f(r["buy"])] for r in D["buy_rows"]]})
            T({"title": "Переместить между складами", "cols": [("Номенклатура", "text", 48), ("Откуда", "text", 22), ("Куда", "text", 22),
                                                              ("Ед.", "text", 6), ("Количество", "num", 11)],
               "rows": [[m["item"], m["src"], m["to"], m["unit"] or "", _f(m["qty"])] for m in D["move_rows"]]})
        else:
            T({"title": "Заканчивается", "cols": [("Номенклатура", "text", 48), ("Склад", "text", 22), ("Ед.", "text", 6),
                                                 ("Остаток", "num", 10), ("Хватит, дн.", "int", 9), ("Нужно до 30 дн.", "num", 11),
                                                 ("Где взять", "text", 36)],
               "rows": [[r["item"], r["warehouse"], r["unit"] or "", _f(r["qty"]), round(r["days"] or 0), _f(r["need"]),
                         "; ".join(f"{p['warehouse']} — {p['qty']:.0f}" for p in r["move_plan"]) or "закупка"]
                        for r in D["reorder"]]})
        if D.get("abc_wh"):
            T({"title": "ABC по складам (продажи 90 дн.)", "cols": [("Склад", "text", 28), ("A", "int", 8), ("B", "int", 8), ("C", "int", 8),
                                                            ("Ниже мин.", "int", 10), ("Выше макс.", "int", 10), ("Излишек, ₸", "money", 15)],
               "rows": [[r["w"], r["A"], r["B"], r["C"], r["low"], r["high"], _f(r["high_v"])] for r in D["abc_wh"]]})
            T({"title": "Ниже минимума — заказать до максимума", "cols": [("Номенклатура", "text", 46), ("Склад", "text", 22), ("Класс", "text", 7),
                                                                          ("Ед.", "text", 6), ("Остаток", "num", 10), ("Мин", "num", 10), ("Макс", "num", 10), ("Заказать", "num", 11)],
               "rows": [[r["item"], r["w"], r["abc"], r["unit"] or "", _f(r["qty"]), _f(r["min"]), _f(r["max"]), _f(r["order"])] for r in D["mm_low"]]})
            T({"title": "Выше максимума — излишек", "cols": [("Номенклатура", "text", 46), ("Склад", "text", 22), ("Класс", "text", 7),
                                                             ("Ед.", "text", 6), ("Остаток", "num", 10), ("Макс", "num", 10), ("Излишек", "num", 10), ("Излишек, ₸", "money", 14)],
               "rows": [[r["item"], r["w"], r["abc"], r["unit"] or "", _f(r["qty"]), _f(r["max"]), _f(r["excess"]), _f(r["excess_v"])] for r in D["mm_high"]]})
        if D.get("by_wh") and not D.get("wh"):
            T({"title": "Склады", "cols": [("Склад", "text", 28), ("Позиций", "int", 10), ("Запасы, ₸", "money", 16),
                                           ("Заканчивается", "int", 12), ("Неликвид", "int", 10), ("В неликвиде, ₸", "money", 15)],
               "rows": [[r["w"], r["n"], _f(r["v"]), r["r"], r["i"], _f(r["iv"])] for r in D["by_wh"]]})
        T({"title": "Неликвиды (нет продаж 90 дн.)", "cols": [("Номенклатура", "text", 48), ("Склад", "text", 22), ("Остаток", "num", 10),
                                                              ("Ед.", "text", 6), ("Сумма, ₸", "money", 15), ("Посл. продажа", "text", 12)],
           "rows": [[r["item"], r["warehouse"], _f(r["qty"]), r["unit"] or "", _f(r["cost_sum"]), r["last_sale"] or "не было"]
                    for r in D["illiquid"]]})
        if D["by_price"]:
            rep["notes"].append("В выгрузке 1С нет себестоимости остатков — стоимость оценена по средней цене продаж за 180 дней.")

    elif tab == "money":
        rep["kpis"] = [("Поступления (ДДС), ₸", _f(D["in"]), ""), ("Расходы (ДДС), ₸", _f(D["out"]), "red"),
                       ("Сальдо, ₸", _f(D["net"]), ""), ("Оплаты клиентов, ₸", _f(D["pay_total"]), "")]
        T({"title": "Расходы по статьям", "cols": [("Статья", "text", 40), ("Сумма, ₸", "money", 16), ("Платежей", "int", 10), ("К прошлому", "pct", 11)],
           "rows": [[r["a"], _f(r["s"]), r["n"], r["delta"]] for r in D["out_by"]], "total": ["Итого", _f(D["out"]), D["n_out"], D["out_delta"]]})
        T({"title": "Поступления по статьям", "cols": [("Статья", "text", 40), ("Сумма, ₸", "money", 16), ("Платежей", "int", 10)],
           "rows": [[r["a"], _f(r["s"]), r["n"]] for r in D["in_by"]]})
        T({"title": "Кому платим больше всего", "cols": [("Контрагент", "text", 40), ("Сумма, ₸", "money", 16), ("Платежей", "int", 10)],
           "rows": [[r["k"], _f(r["s"]), r["n"]] for r in D["cps"]]})
        T({"title": "По организациям", "cols": [("Организация", "text", 34), ("Поступления, ₸", "money", 16), ("Расходы, ₸", "money", 16)],
           "rows": [[r["o"], _f(r["i"]), _f(r["o2"])] for r in D["by_org"]]})

    elif tab == "prod" and not D.get("empty"):
        O = D.get("own")
        rep["kpis"] = ([("АВТОКОМП выпуск, м²", _f(O["m2"]), ""), ("АВТОКОМП выпуск, т", round(O["t"], 2), ""),
                        ("АВТОКОМП выпуск, шт/м", _f(O["qty"]), "")] if O else []) + [
                       ("Ламинировано за период", _f(D["qty"]), ""), ("Заказов в работе", D["n_work"], ""),
                       ("Просрочено заказов", D["n_late"], "red"), ("Сырьё у переработчика", _f(D["raw_qty"]), "")]
        if O:
            T({"title": "АВТОКОМП: выпуск по участкам", "cols": [("Участок", "text", 34), ("м²", "num", 12), ("т", "num", 10),
                                                                ("шт / м", "num", 12), ("Документов", "int", 10), ("м² к прошлому", "pct", 12)],
               "rows": [[r["k"], _f(r["m2"]), round(r["t"], 3), _f(r["qty"]), r["docs"], r["d_m2"]] for r in O["depts"]],
               "total": ["Итого", _f(O["m2"]), round(O["t"], 3), _f(O["qty"]), O["docs"], O["d_m2"]]})
            T({"title": "АВТОКОМП: что выпустили", "cols": [("Номенклатура", "text", 50), ("Группа", "text", 16), ("м²", "num", 12),
                                                           ("т", "num", 10), ("Количество", "num", 12), ("Ед.", "text", 6)],
               "rows": [[r["item"], r["group"], _f(r["m2"]), round(r["t"], 3), _f(r["qty"]), r["unit"]] for r in O["items"]]})
        T({"title": "Заказы переработчику в работе", "cols": [("Заказ", "text", 14), ("Дата", "text", 11), ("Срок", "text", 11),
                                                             ("Статус", "text", 16), ("Заказано", "num", 11), ("Получено", "num", 11),
                                                             ("Осталось", "num", 11), ("Просрочка, дн.", "int", 10), ("Что осталось", "text", 50)],
           "rows": [[o["no"], o["date"], o["due"], o["status"], _f(o["qty"]), _f(o["qty_in"]), _f(o["left"]),
                     o["late_days"] or None, "; ".join(o["items"])] for o in D["work"]]})
        T({"title": "Что ламинировали", "cols": [("Профиль", "text", 50), ("Количество", "num", 14), ("Ед.", "text", 6), ("Цветов", "int", 8)],
           "rows": [[r["item"], _f(r["s"]), r["unit"] or "", r["nc"]] for r in D["by_item"]]})
        T({"title": "По цветам", "cols": [("Цвет", "text", 40), ("Количество", "num", 14)],
           "rows": [[r["k"], _f(r["s"])] for r in D["by_color"]]})
        T({"title": "Сырьё у переработчика", "cols": [("Профиль / материал", "text", 50), ("Цвет", "text", 22), ("Количество", "num", 14), ("Ед.", "text", 6)],
           "rows": [[r["item"], r["color"] or "", _f(r["q"]), r["unit"] or ""] for r in D["raw"]]})

    elif tab == "acc":
        rep["kpis"] = [("Нам должны, ₸", _f(D["debt"]), "red"), ("Переплаты, ₸", _f(D["prepay"]), ""),
                       ("Поступило, ₸", _f(D["pay_total"]), ""), ("Расходы, ₸", _f(D["exp"]), "red")]
        T({"title": "Дебиторка по филиалам", "cols": [("Филиал", "text", 28), ("Нам должны, ₸", "money", 16), ("Клиентов", "int", 10),
                                                      ("Просрочено, ₸", "money", 15), ("Переплаты, ₸", "money", 15)],
           "rows": [[r["br"], _f(r["debt"]), r["n"], _f(r["over"]), _f(r["prepay"])] for r in D["by_br"]],
           "total": ["Итого", _f(D["debt"]), D["n_debt"], _f(D["overdue"]), _f(D["prepay"])]})
        T({"title": "Поступления по способам", "cols": [("Филиал", "text", 28), ("Карта", "money", 14), ("Наличные", "money", 14), ("Безнал", "money", 14), ("Итого", "money", 15)],
           "rows": [[r["br"], _f(r["card"]), _f(r["cash"]), _f(r["bank"]), _f(r["total"])] for r in D["pays"]],
           "total": ["Итого"] + [_f(v) for _k, _l, v in D["kinds"]] + [_f(D["pay_total"])]})
        T({"title": "Должники", "cols": [("Клиент", "text", 40), ("Филиал", "text", 22), ("Менеджер", "text", 24), ("Долг, ₸", "money", 16)],
           "rows": [[r["client"], r["br"], r["manager"] or "", _f(r["debt"])] for r in D["debtors"]]})
        T({"title": "Переплаты клиентов", "cols": [("Клиент", "text", 40), ("Филиал", "text", 22), ("Переплата, ₸", "money", 16)],
           "rows": [[r["client"], r["br"], _f(r["prepay"])] for r in D["prepays"]]})
        T({"title": "Расходы по статьям ДДС", "cols": [("Статья", "text", 40), ("Сумма, ₸", "money", 16), ("Платежей", "int", 10)],
           "rows": [[r["a"], _f(r["s"]), r["n"]] for r in D["exp_by"]]})
    return rep


def _tab_ctx(request: Request, tab: str, q: dict):
    """Вызвать вкладку с теми же отборами → (ответ-заглушка | None, контекст)."""
    from . import dashboards as d
    p, org, branch, dd, wh, mg = (q.get(k, "") for k in ("p", "org", "branch", "d", "wh", "mg"))
    p = p or "month"
    call = {
        "company": lambda: d.dash(request, p, org, branch, dd),
        "mgr": lambda: d.dash_mgr(request, p, org, branch, dd, mg),
        "branches": lambda: d.dash_branches(request, p, org, dd),
        "stock": lambda: d.dash_stock(request, org, wh),
        "purchase": lambda: d.dash_purchase(request, org, wh),
        "money": lambda: d.dash_money(request, p, org, dd),
        "acc": lambda: d.dash_acc(request, p, org, branch, dd),
        "prod": lambda: d.dash_prod(request, p, org, dd),
    }.get(tab)
    if not call:
        return HTMLResponse("Нет такого отчёта", status_code=404), None
    resp = call()
    ctx = getattr(resp, "context", None)
    if not ctx or "data" not in ctx or getattr(resp, "template", None) is None or resp.template.name == "noaccess.html":
        return resp, None
    return None, ctx


@router.get("/dash/report")
def dash_report(request: Request, tab: str = "company", fmt: str = "html"):
    from . import b24auth, xlsx_out, main as m
    q = dict(request.query_params)
    if tab == "acc" and fmt != "xlsx":
        import urllib.parse as up
        return RedirectResponse(f"{m._root()}/dash/acc/report?" + up.urlencode({k: v for k, v in q.items() if k not in ("tab", "fmt")}),
                                status_code=303)
    resp, ctx = _tab_ctx(request, tab, q)
    if resp is not None:
        return resp
    rep = build(tab, ctx)
    who = b24auth.me(request)["name"]
    b24auth.log_access(request, "report", b24auth.current_user(request), f"отчёт {tab} {fmt} {q.get('p', '')}")
    if fmt == "xlsx":
        body = xlsx_out.report_book(rep, who)
        from datetime import date
        name = f"otchet_{tab}_{date.today():%Y%m%d}.xlsx"
        return Response(body, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers={"Content-Disposition": f'attachment; filename="{name}"'})
    return m.templates.TemplateResponse("report.html", {
        "request": request, "base": m._root(), "rep": rep, "who": who,
        "now": xlsx_out.now_local().strftime("%d.%m.%Y %H:%M"), "fv": fv, "zip": zip,
    })
