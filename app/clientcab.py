"""Кабинет клиента /my (поставлено 18.10.2026 23:29).

Клиент открывает ссылку из WhatsApp (или ярлык «на экране телефона» — PWA с start_url /my), входит по номеру
мобильного и коду из WhatsApp. Внутри: закупки за год (по месяцам, что купил), сверка (долг / переплата, оплаты),
свои документы (накладные З-2: подписать, PDF, квитанция) и чеки об оплате.

Кто есть кто: клиент = номер телефона. Его названия в 1С берём из документов портала (телефон клиента в накладной),
из уведомлений об оплате и из ручной привязки администратора (таблица client_links, страница /cabinet/clients).
Код входа отправляется только на известные номера (защита от рассылки на чужие номера).
"""
import hashlib
import hmac
import json
import re
import time
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from . import analytics, chatapp, config, db

router = APIRouter()
COOKIE = "edo_client"
MAX_AGE = 60 * 60 * 24 * 120          # 4 месяца
CODE_TTL = 10 * 60
LOCAL_TZ = timezone(timedelta(hours=5))
MONTHS = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS client_codes (phone TEXT, code TEXT, expires REAL, tries INTEGER DEFAULT 0, created REAL);
CREATE TABLE IF NOT EXISTS client_links (phone TEXT, client_name TEXT, added_by TEXT, created_at TEXT,
    PRIMARY KEY (phone, client_name));
CREATE TABLE IF NOT EXISTS client_log (ts TEXT, phone TEXT, kind TEXT, detail TEXT, ip TEXT);
"""


def _init():
    with db.conn() as c:
        c.executescript(_SCHEMA)


_init()


# ------------------------------------------------------------------ сессия
def _sig(phone: str) -> str:
    return hmac.new(config.SECRET_KEY.encode(), f"client:{phone}".encode(), hashlib.sha256).hexdigest()[:32]


def current_phone(request: Request) -> Optional[str]:
    v = request.cookies.get(COOKIE) or ""
    if "." not in v:
        return None
    ph, sig = v.split(".", 1)
    return ph if hmac.compare_digest(sig, _sig(ph)) else None


def _log(phone, kind, detail="", ip=""):
    with db.conn() as c:
        c.execute("INSERT INTO client_log VALUES (?,?,?,?,?)", (db.now_iso(), phone, kind, detail[:300], ip))


def _ip(request):
    return request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "")


# ------------------------------------------------------------------ кто этот клиент
def norm(s: str) -> str:
    s = (s or "").lower().replace("ё", "е")
    s = re.sub(r"[«»\"'`.,()]", " ", s)
    s = re.sub(r"\b(тоо|ип|ао|оао|зао|ооо|кх|пк)\b", " ", s)
    return " ".join(s.split())


def client_names(phone: str) -> set:
    """Названия клиента в 1С, связанные с номером."""
    names = set()
    with db.conn() as c:
        for r in c.execute("SELECT client_name, client_phone FROM documents WHERE client_phone IS NOT NULL"):
            if chatapp.normalize_phone(r["client_phone"]) == phone and r["client_name"]:
                names.add(r["client_name"])
        try:
            for r in c.execute("SELECT DISTINCT d.client_name FROM signers s JOIN documents d ON d.id=s.document_id "
                               "WHERE s.role='client' AND s.phone=?", (phone,)):
                if r["client_name"]:
                    names.add(r["client_name"])
        except Exception:
            pass
        try:
            for r in c.execute("SELECT DISTINCT client_name, phone FROM pay_notifications"):
                if chatapp.normalize_phone(r["phone"]) == phone and r["client_name"]:
                    names.add(r["client_name"])
        except Exception:
            pass
        for r in c.execute("SELECT client_name FROM client_links WHERE phone=?", (phone,)):
            names.add(r["client_name"])
    return {n for n in names if n and "розниц" not in n.lower()}


def _sales_names(c, names: set) -> list:
    """Сопоставить названия с написанием клиента в выгрузке 1С (an_sales)."""
    want = {norm(n) for n in names}
    return [r["client"] for r in c.execute("SELECT DISTINCT client FROM an_sales WHERE client<>''") if norm(r["client"]) in want]


# ------------------------------------------------------------------ вход
def _page(request, tpl, **kw):
    from . import main as m
    return m.templates.TemplateResponse(tpl, {"request": request, "brand": config.BRAND, "company": config.COMPANY,
                                              "base": m._root(), **kw})


@router.get("/my/manifest.webmanifest")
def my_manifest():
    from . import main as m
    r = m._root()
    return JSONResponse({
        "name": "ANESCOM Клиент — кабинет клиента", "short_name": "ANESCOM Клиент", "id": f"{r}/my", "start_url": f"{r}/my", "scope": f"{r}/my",
        "display": "standalone", "background_color": "#ffffff", "theme_color": "#cc2b28",
        "icons": [{"src": f"{r}/static/icon-client-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": f"{r}/static/icon-client-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"}],
    }, media_type="application/manifest+json")


@router.get("/my/sw.js")
def my_sw():
    """Минимальный service worker — нужен телефону, чтобы предложить «Установить» кабинет как приложение."""
    from fastapi.responses import Response
    js = ("self.addEventListener('install', e => self.skipWaiting());\n"
          "self.addEventListener('activate', e => self.clients.claim());\n"
          "self.addEventListener('fetch', e => {});\n")
    return Response(js, media_type="application/javascript", headers={"Service-Worker-Allowed": "/"})


@router.post("/my/login")
def my_login(request: Request, phone: str = Form(...)):
    ph = chatapp.normalize_phone(phone)
    if not chatapp.is_mobile(ph):
        return _page(request, "my_login.html", step="phone", err="Введите мобильный номер: +7 7__ ___ __ __", phone=phone)
    if not client_names(ph):
        _log(ph, "unknown", ip=_ip(request))
        return _page(request, "my_login.html", step="phone", phone=phone,
                     err="Этот номер пока не привязан к клиенту ANESCOM. Попросите менеджера указать его в 1С или в накладной.")
    now = time.time()
    with db.conn() as c:
        recent = c.execute("SELECT COUNT(*) n FROM client_codes WHERE phone=? AND created>?", (ph, now - 600)).fetchone()["n"]
        if recent >= 3:
            return _page(request, "my_login.html", step="code", phone=ph, err="Код уже отправлен. Подождите 10 минут.")
        code = db.gen_code(4)
        c.execute("INSERT INTO client_codes(phone, code, expires, tries, created) VALUES (?,?,?,?,?)",
                  (ph, code, now + CODE_TTL, 0, now))
    sent = ""
    try:
        if chatapp.is_configured():
            chatapp.send_text(ph, f"Код для входа в кабинет клиента {config.COMPANY}: {code}\nНикому не сообщайте этот код.")
            sent = "sent"
    except Exception as e:  # noqa
        sent = f"error: {e}"
    _log(ph, "code", sent, _ip(request))
    if sent != "sent":
        return _page(request, "my_login.html", step="phone", phone=phone,
                     err="Не удалось отправить код в WhatsApp. Попробуйте позже или напишите менеджеру.")
    return _page(request, "my_login.html", step="code", phone=ph)


@router.post("/my/verify")
def my_verify(request: Request, phone: str = Form(...), code: str = Form(...), pw1: str = Form(""), pw2: str = Form("")):
    """Код из WhatsApp + новый пароль (первый вход или «забыли пароль»)."""
    from . import phonelogin as pl
    ph = chatapp.normalize_phone(phone)
    bad = pl.pw_ok(pw1, pw2)
    if bad:
        return _page(request, "my_login.html", step="code", phone=ph, err=bad)
    if not pl.check_code(ph, code):
        return _page(request, "my_login.html", step="code", phone=ph, err="Код неверный или устарел. Проверьте или запросите новый.")
    pl.set_password("client", ph, pw1)
    _log(ph, "password_set", ip=_ip(request))
    return _client_session(ph)


def _client_session(ph):
    from . import main as m
    resp = RedirectResponse(f"{m._root()}/my", status_code=303)
    resp.set_cookie(COOKIE, f"{ph}.{_sig(ph)}", max_age=MAX_AGE, httponly=True, secure=True, samesite="lax")
    return resp


@router.post("/my/pw")
def my_pw(request: Request, phone: str = Form(...), password: str = Form(...)):
    from . import phonelogin as pl
    ph = chatapp.normalize_phone(phone)
    ok, msg, _ = pl.check_password("client", ph, password)
    if not ok:
        _log(ph, "denied", msg, _ip(request))
        return _page(request, "my_login.html", step="phone", phone=phone, err=msg)
    _log(ph, "login", ip=_ip(request))
    return _client_session(ph)


@router.get("/my/logout")
def my_logout():
    from . import main as m
    resp = RedirectResponse(f"{m._root()}/my", status_code=303)
    resp.delete_cookie(COOKIE)
    return resp


# ------------------------------------------------------------------ кабинет
def _docs(phone: str) -> list:
    out = []
    with db.conn() as c:
        rows = c.execute("SELECT * FROM documents WHERE status<>'cancelled' ORDER BY created_at DESC LIMIT 3000").fetchall()
        for d in rows:
            mine = chatapp.normalize_phone(d["client_phone"] or "") == phone
            sig = None
            try:
                sig = c.execute("SELECT * FROM signers WHERE document_id=? AND role='client' AND phone=? ORDER BY step LIMIT 1",
                                (d["id"], phone)).fetchone()
            except Exception:
                pass
            if not (mine or sig):
                continue
            try:
                meta = json.loads(d["meta"] or "{}")
            except Exception:
                meta = {}
            token, code = (sig["token"], sig["code"]) if sig else (d["sign_token"], d["sign_code"])
            my_turn = bool(sig and sig["status"] in ("active", "viewed") and d["status"] == "in_progress") or \
                (not sig and d["status"] in ("created", "sent", "viewed"))
            out.append({"id": d["id"], "title": d["title"], "created": (d["created_at"] or "")[:10], "status": d["status"],
                        "kind": meta.get("kind") or "", "order": meta.get("order_no") or "", "my_turn": my_turn,
                        "signed_me": bool(sig and sig["status"] == "signed") or d["status"] == "signed",
                        "link": f"/s/{token}?k={code}", "pdf": f"/s/{token}/view", "cert": f"/s/{d['sign_token']}/certificate"})
            if len(out) >= 60:
                break
    return out


def _receipts(phone: str) -> list:
    out = []
    try:
        with db.conn() as c:
            for r in c.execute("SELECT * FROM pay_notifications ORDER BY created_at DESC LIMIT 5000"):
                if chatapp.normalize_phone(r["phone"] or "") == phone:
                    out.append({"date": (r["created_at"] or "")[:10], "sum": r["amount"] or 0, "kind": r["pay_kind"] or "",
                                "url": r["receipt_url"] or "", "title": r["doc_title"] or "", "order": r["order_no"] or ""})
                    if len(out) >= 40:
                        break
    except Exception:
        pass
    return out


def _staff_viewer(request: Request) -> bool:
    """Сотрудник-руководитель может открыть кабинет любого клиента («смотреть как клиент»)."""
    from . import access, main as m
    if not m.is_staff(request):
        return False
    s = access.scope(request)
    return bool(s.password or s.role in ("admin", "director", "rop", "manager", "accountant"))


@router.get("/my", response_class=HTMLResponse)
def my_home(request: Request, y: str = "", as_phone: str = "", as_name: str = ""):
    viewing = ""
    if (as_phone or as_name) and _staff_viewer(request):
        phone = chatapp.normalize_phone(as_phone) if as_phone else ""
        names = client_names(phone) if phone else set()
        if as_name.strip():
            names.add(as_name.strip())
        viewing = as_name.strip() or (f"+{phone[:4]} ••• {phone[-2:]}" if phone else "")
        phone = phone or "0"
    else:
        phone = current_phone(request)
        if not phone:
            return _page(request, "my_login.html", step="phone", phone="")
        names = client_names(phone)
    today = datetime.now(LOCAL_TZ).date()
    try:
        yy = int(y) if y else today.year
    except ValueError:
        yy = today.year
    with analytics.conn() as c:
        sn = _sales_names(c, names)
        ph = ",".join("?" * len(sn)) or "''"
        years = [r["y"] for r in c.execute(f"SELECT DISTINCT substr(date,1,4) y FROM an_sales WHERE client IN ({ph}) ORDER BY y DESC", sn)]
        if str(yy) not in years and years:
            yy = int(years[0])
        a, b = f"{yy}-01-01", f"{yy}-12-31"
        by_m = {r["m"]: r for r in c.execute(
            f"SELECT substr(date,1,7) m, SUM(sum) s, COUNT(DISTINCT doc_key) n FROM an_sales WHERE client IN ({ph}) "
            "AND date BETWEEN ? AND ? GROUP BY m", sn + [a, b])}
        pay_m = {r["m"]: r["s"] for r in c.execute(
            f"SELECT substr(date,1,7) m, SUM(sum) s FROM an_payments WHERE client IN ({ph}) AND date BETWEEN ? AND ? GROUP BY m",
            sn + [a, b])}
        months = []
        for i in range(12):
            k = f"{yy}-{i + 1:02d}"
            months.append({"k": k, "label": MONTHS[i], "buy": (by_m.get(k) or {"s": 0})["s"] or 0,
                           "docs": (by_m.get(k) or {"n": 0})["n"] or 0, "paid": pay_m.get(k, 0) or 0})
        items = [dict(r) for r in c.execute(
            f"SELECT item, MAX(item_group) g, SUM(qty) q, SUM(sum) s FROM an_sales WHERE client IN ({ph}) AND date BETWEEN ? AND ? "
            "GROUP BY item_key ORDER BY s DESC LIMIT 15", sn + [a, b])]
        last = [dict(r) for r in c.execute(
            f"SELECT date, doc_no, SUM(sum) s, COUNT(*) n FROM an_sales WHERE client IN ({ph}) GROUP BY doc_key "
            "ORDER BY date DESC LIMIT 15", sn)]
        debt = c.execute(f"SELECT COALESCE(SUM(debt),0) d, COALESCE(SUM(prepay),0) p FROM an_debts WHERE client IN ({ph})", sn).fetchone()
        payments = [dict(r) for r in c.execute(
            f"SELECT date, doc_no, kind, sum FROM an_payments WHERE client IN ({ph}) ORDER BY date DESC LIMIT 15", sn)]
        loaded = c.execute("SELECT MAX(ts) t FROM an_loads WHERE kind IN ('sales','debts')").fetchone()["t"]
    total = sum(m["buy"] for m in months)
    paid = sum(m["paid"] for m in months)
    mx = max([m["buy"] for m in months] + [1])
    docs = _docs(phone)
    return _page(request, "my.html", phone=phone, names=sorted(names), y=yy, years=years or [str(yy)], months=months,
                 total=total, paid=paid, mx=mx, items=items, last=last, debt=debt["d"] or 0, prepay=abs(debt["p"] or 0),
                 payments=payments, docs=docs, to_sign=[d for d in docs if d["my_turn"]], receipts=_receipts(phone),
                 today=today, loaded=(loaded or "")[:16].replace("T", " "), matched=bool(sn), viewing=viewing,
                 qs=("&as_phone=" + as_phone if as_phone else "") + ("&as_name=" + as_name if as_name else ""))


# ------------------------------------------------------------------ привязка номеров (администратор)
@router.get("/cabinet/clients", response_class=HTMLResponse)
def clients_admin(request: Request, msg: str = ""):
    from . import access, b24auth, main as m
    if not m.is_staff(request):
        return _page(request, "login.html", b24=b24auth.configured())
    s = access.scope(request)
    if not (s.password or s.role in ("admin", "director", "rop", "manager", "accountant")):
        return _page(request, "noaccess.html", title="Нет доступа", text="Привязка номеров клиентов — для менеджеров и руководителей.")
    with db.conn() as c:
        links = [dict(r) for r in c.execute("SELECT * FROM client_links ORDER BY created_at DESC LIMIT 300")]
        logins = [dict(r) for r in c.execute("SELECT * FROM client_log ORDER BY ts DESC LIMIT 50")]
    with analytics.conn() as c:
        clients = [r["client"] for r in c.execute(
            "SELECT client, SUM(sum) s FROM an_sales WHERE client<>'' AND date>=? GROUP BY client ORDER BY s DESC LIMIT 800",
            (str(date.today() - timedelta(days=730)),))]
    return _page(request, "my_admin.html", links=links, logins=logins, msg=msg, clients=clients)


@router.post("/cabinet/clients")
def clients_add(request: Request, phone: str = Form(...), client_name: str = Form(...), delete: str = Form("")):
    from . import access, b24auth, main as m
    if not m.is_staff(request):
        return RedirectResponse(f"{m._root()}/cabinet", status_code=303)
    ph = chatapp.normalize_phone(phone)
    if not ph:
        return RedirectResponse(f"{m._root()}/cabinet/clients?msg=Неверный+номер", status_code=303)
    who = (b24auth.current_user(request) or {}).get("name") or "общий вход"
    with db.conn() as c:
        if delete:
            c.execute("DELETE FROM client_links WHERE phone=? AND client_name=?", (ph, client_name.strip()))
        else:
            c.execute("INSERT OR REPLACE INTO client_links VALUES (?,?,?,?)", (ph, client_name.strip(), who, db.now_iso()))
    return RedirectResponse(f"{m._root()}/cabinet/clients?msg=Сохранено", status_code=303)
