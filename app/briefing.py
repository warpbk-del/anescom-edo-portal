"""Утренняя сводка руководителю в Bitrix24 (этап C портала v4).

Каждое утро (задача планировщика «ANESCOM brief», пн–сб 8:30) портал собирает показатели за вчера
из выгрузки 1С и документов и пишет сообщение в Bitrix24 через вебхук (im.message.add) каждому
из BRIEF_TO (ID пользователей Bitrix24 через запятую; решение 18.10: сначала только Болатұлы, 355).
Предпросмотр: /dash/brief (админ). Ручная отправка: deploy/brief_send.py или кнопка на предпросмотре.
"""
import logging
from datetime import date, datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from . import analytics, config, db, registry

log = logging.getLogger("edo.brief")
router = APIRouter()


def _m(v) -> str:
    v = float(v or 0)
    if abs(v) >= 1e9:
        return f"{v / 1e9:.2f} млрд".replace(".", ",")
    if abs(v) >= 1e6:
        return f"{v / 1e6:.1f} млн".replace(".", ",")
    return f"{v:,.0f}".replace(",", " ")


def _pct(cur, prev):
    if not prev:
        return ""
    d = (cur - prev) / prev * 100
    return f" ({'▲' if d >= 0 else '▼'} {abs(d):.0f}%)"


def build(day: date = None) -> dict:
    tz = timezone(timedelta(hours=config.TZ_OFFSET_HOURS))
    today = datetime.now(tz).date()
    y = day or (today - timedelta(days=1))
    wk = y - timedelta(days=7)
    m1 = y.replace(day=1)
    pm1 = (m1 - timedelta(days=1)).replace(day=1)
    pm_end = pm1 + (y - m1)
    from .dashboards import is_internal
    with analytics.conn() as c:
        def sales(a, b):
            r = c.execute("SELECT COALESCE(SUM(sum),0) s, COUNT(DISTINCT doc_key) n, COUNT(DISTINCT client_key) k "
                          "FROM an_sales WHERE date BETWEEN ? AND ?", (str(a), str(b))).fetchone()
            return dict(r)
        sy, sw = sales(y, y), sales(wk, wk)
        sm, spm = sales(m1, y), sales(pm1, pm_end)
        pays = {r["kind"]: r["s"] for r in c.execute(
            "SELECT kind, SUM(sum) s FROM an_payments WHERE date=? GROUP BY kind", (str(y),))}
        exp = c.execute("SELECT COALESCE(SUM(sum),0) s FROM an_cashflow WHERE direction='out' AND date=?",
                        (str(y),)).fetchone()["s"]
        exp_m = c.execute("SELECT COALESCE(SUM(sum),0) s FROM an_cashflow WHERE direction='out' AND date BETWEEN ? AND ?",
                          (str(m1), str(y))).fetchone()["s"]
        brs = c.execute("SELECT CASE WHEN branch='' THEN '(не указан)' ELSE branch END b, SUM(sum) s FROM an_sales "
                        "WHERE date=? GROUP BY b ORDER BY s DESC LIMIT 3", (str(y),)).fetchall()
        mgrs = c.execute("SELECT manager m, SUM(sum) s FROM an_sales WHERE date=? AND manager<>'' GROUP BY m "
                         "ORDER BY s DESC LIMIT 3", (str(y),)).fetchall()
        debts = [dict(r) for r in c.execute("SELECT client, debt, prepay FROM an_debts")]
        reorder = c.execute("SELECT COUNT(*) n FROM an_stock WHERE sold_30>0 AND qty < sold_30/30.0*14").fetchone()["n"]
        last = c.execute("SELECT MAX(ts) t FROM an_loads").fetchone()["t"]
    ext = [d for d in debts if not is_internal(d["client"])]
    debt = sum(d["debt"] or 0 for d in ext)
    prepay = sum(d["prepay"] or 0 for d in ext)
    top_debtors = sorted([d for d in ext if (d["debt"] or 0) > 0], key=lambda d: -d["debt"])[:3]
    with db.conn() as dc:
        raw = dc.execute("SELECT * FROM documents ORDER BY created_at DESC LIMIT 2000").fetchall()
        docs = registry.decorate(dc, raw)
    k = registry.dashboard(None, [d for d in docs if d["cat"] != "kadr"])["kpi"]
    last_local = ""
    if last:
        try:
            last_local = datetime.fromisoformat(last).astimezone(tz).strftime("%d.%m %H:%M")
        except ValueError:
            last_local = last
    return {"day": y, "sy": sy, "sw": sw, "sm": sm, "spm": spm, "pays": pays, "pay_total": sum(pays.values()),
            "exp": exp, "exp_m": exp_m, "brs": [dict(r) for r in brs], "mgrs": [dict(r) for r in mgrs],
            "debt": debt, "prepay": prepay, "top_debtors": top_debtors, "reorder": reorder, "docs": k,
            "last": last_local}


WD = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]


def text(b: dict) -> str:
    y = b["day"]
    L = [f"[B]Утренняя сводка ANESCOM — {y.strftime('%d.%m.%Y')}, {WD[y.weekday()]}[/B]", ""]
    L.append(f"💰 Выручка: [B]{_m(b['sy']['s'])} ₸[/B]{_pct(b['sy']['s'], b['sw']['s'])} к тому же дню прошлой недели")
    L.append(f"   документов {b['sy']['n']}, клиентов {b['sy']['k']}")
    L.append(f"📅 С начала месяца: {_m(b['sm']['s'])} ₸{_pct(b['sm']['s'], b['spm']['s'])} к тем же дням прошлого месяца")
    if b["brs"]:
        L.append("🏢 Филиалы: " + "; ".join(f"{r['b']} — {_m(r['s'])}" for r in b["brs"]))
    if b["mgrs"]:
        L.append("👤 Лучшие менеджеры: " + "; ".join(f"{' '.join(r['m'].split()[:2])} — {_m(r['s'])}" for r in b["mgrs"]))
    L.append("")
    p = b["pays"]
    L.append(f"💳 Поступило: [B]{_m(b['pay_total'])} ₸[/B] (карта {_m(p.get('card'))}, наличные {_m(p.get('cash'))}, безнал {_m(p.get('bank'))})")
    L.append(f"📤 Расходы (ДДС): {_m(b['exp'])} ₸ · с начала месяца {_m(b['exp_m'])} ₸")
    L.append(f"📌 Нам должны: [B]{_m(b['debt'])} ₸[/B] · переплаты клиентов {_m(b['prepay'])} ₸")
    if b["top_debtors"]:
        L.append("   крупные: " + "; ".join(f"{d['client']} — {_m(d['debt'])}" for d in b["top_debtors"]))
    L.append(f"📦 Дозаказать: {b['reorder']} позиций (запас < 14 дн.)")
    k = b["docs"]
    L.append(f"📝 Документы: ждут сотрудников {k['staff']}, клиентов {k['client']}"
             + (f", просрочено {k['overdue']}" if k["overdue"] else ""))
    L.append("")
    L.append(f"Подробно: {config.PUBLIC_BASE_URL}/dash · данные 1С на {b['last']}")
    return "\n".join(L)


def _hook(method: str, params: dict):
    if not config.B24_WEBHOOK:
        raise RuntimeError("Не настроен вебхук Bitrix24 (EDO_B24_WEBHOOK)")
    r = httpx.post(f"{config.B24_WEBHOOK}/{method}.json", json=params, timeout=20)
    js = r.json()
    if "error" in js:
        raise RuntimeError(f"{method}: {js.get('error_description') or js['error']}")
    return js.get("result")


def send(to=None) -> list:
    """Собрать сводку и отправить каждому получателю. → [(id, 'ok'|'ошибка …')]."""
    msg = text(build())
    out = []
    for uid in (to or config.BRIEF_TO):
        try:
            try:
                _hook("im.message.add", {"DIALOG_ID": str(uid), "MESSAGE": msg, "SYSTEM": "N"})
            except RuntimeError as e:
                # нет права im у вебхука — пробуем уведомлением
                _hook("im.notify.personal.add", {"USER_ID": int(uid), "MESSAGE": msg})
                log.warning("brief: im.message.add не прошло (%s), отправлено уведомлением", e)
            out.append((uid, "ok"))
        except Exception as e:
            log.exception("brief send %s", uid)
            out.append((uid, f"ошибка: {e}"))
    with db.conn() as c:
        c.execute("INSERT INTO access_log (ts, b24_id, name, action, ip, ua, detail) VALUES (?,?,?,?,?,?,?)",
                  (db.now_iso(), None, "сводка", "brief_sent", "server", "", str(out)[:500]))
    return out


@router.get("/dash/brief", response_class=HTMLResponse)
def brief_preview(request: Request, sent: str = ""):
    from . import b24auth, main
    if not b24auth.is_admin(request):
        raise HTTPException(403, "Только для администратора")
    t = text(build())
    import html as _h
    body = _h.escape(t).replace("[B]", "<b>").replace("[/B]", "</b>").replace("\n", "<br>")
    note = f"<p style='color:#0f5132'>Отправлено: {_h.escape(sent)}</p>" if sent else ""
    return HTMLResponse(f"""<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Утренняя сводка — предпросмотр</title><body style="font:15px/1.5 Roboto,Arial;background:#eef1f5;margin:0">
<div style="max-width:640px;margin:24px auto;background:#fff;padding:24px;border-radius:12px">
<p style="color:#6b7c90;margin-top:0">Так сводка придёт в Битрикс24 (получатели: {', '.join(map(str, config.BRIEF_TO)) or 'не заданы'}).</p>
{note}<div>{body}</div>
<form method=post action="{main._root()}/dash/brief/send" style="margin-top:18px"><button style="background:#cc2b28;color:#fff;border:0;border-radius:999px;padding:10px 18px;font:500 14px Roboto">Отправить сейчас</button></form>
</div></body>""")


@router.post("/dash/brief/send")
def brief_send_now(request: Request):
    from . import b24auth, main
    if not b24auth.is_admin(request):
        raise HTTPException(403, "Только для администратора")
    res = send()
    import urllib.parse
    return RedirectResponse(f"{main._root()}/dash/brief?sent=" + urllib.parse.quote(str(res)), status_code=303)
