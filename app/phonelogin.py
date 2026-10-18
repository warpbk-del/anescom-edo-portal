"""Вход по номеру телефона и паролю (19.10.2026, решение пользователя 00:07).

Сотрудники: «Войти через Битрикс24» или номер + свой пароль. Номер берётся из профиля Битрикс24
(мобильный / рабочий телефон). Первый вход или «забыл пароль» — код в WhatsApp на этот номер → свой пароль.
Клиенты (/my): номер + пароль; первый вход / забыл — код в WhatsApp (clientcab.py) → свой пароль.
Пароли хранятся только как хэш (PBKDF2 с солью) в базе портала на диске D.
"""
import hashlib
import hmac
import os
import re
import time
from typing import Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from . import b24auth, b24people, chatapp, config, db

router = APIRouter()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (kind TEXT NOT NULL, phone TEXT NOT NULL, pw_hash TEXT, salt TEXT, b24_id INTEGER,
    set_at TEXT, fails INTEGER DEFAULT 0, locked_until REAL DEFAULT 0, PRIMARY KEY (kind, phone));
CREATE TABLE IF NOT EXISTS client_codes (phone TEXT, code TEXT, expires REAL, tries INTEGER DEFAULT 0, created REAL);
"""
with db.conn() as _c:
    _c.executescript(_SCHEMA)


def _hash(pw: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), (salt + config.SECRET_KEY).encode(), 150000).hex()


def has_password(kind: str, phone: str) -> bool:
    with db.conn() as c:
        r = c.execute("SELECT pw_hash FROM accounts WHERE kind=? AND phone=?", (kind, phone)).fetchone()
    return bool(r and r["pw_hash"])


def set_password(kind: str, phone: str, pw: str, b24_id: Optional[int] = None):
    salt = os.urandom(12).hex()
    with db.conn() as c:
        c.execute("INSERT INTO accounts(kind, phone, pw_hash, salt, b24_id, set_at, fails, locked_until) VALUES (?,?,?,?,?,?,0,0) "
                  "ON CONFLICT(kind, phone) DO UPDATE SET pw_hash=excluded.pw_hash, salt=excluded.salt, "
                  "b24_id=COALESCE(excluded.b24_id, accounts.b24_id), set_at=excluded.set_at, fails=0, locked_until=0",
                  (kind, phone, _hash(pw, salt), salt, b24_id, db.now_iso()))


def check_password(kind: str, phone: str, pw: str) -> tuple:
    """→ (ok, сообщение, b24_id). 5 ошибок подряд — блок на 15 минут."""
    with db.conn() as c:
        r = c.execute("SELECT * FROM accounts WHERE kind=? AND phone=?", (kind, phone)).fetchone()
        if not r or not r["pw_hash"]:
            return False, "Для этого номера пароль ещё не задан — нажмите «Первый вход или забыли пароль».", None
        if (r["locked_until"] or 0) > time.time():
            return False, "Слишком много попыток. Подождите 15 минут или войдите по коду.", None
        if hmac.compare_digest(_hash(pw or "", r["salt"]), r["pw_hash"]):
            c.execute("UPDATE accounts SET fails=0 WHERE kind=? AND phone=?", (kind, phone))
            return True, "", r["b24_id"]
        fails = (r["fails"] or 0) + 1
        c.execute("UPDATE accounts SET fails=?, locked_until=? WHERE kind=? AND phone=?",
                  (fails, time.time() + 900 if fails >= 5 else 0, kind, phone))
    return False, "Неверный номер или пароль.", None


def pw_ok(pw1: str, pw2: str) -> str:
    if pw1 != pw2:
        return "Пароли не совпадают."
    if len(pw1) < 6:
        return "Пароль — не меньше 6 символов."
    return ""


# ------------------------------------------------------------------ коды в WhatsApp (общие)
def send_code(key: str, phone: str, text_tpl: str) -> str:
    """→ '' если отправлено, иначе текст ошибки. key — 'staff:7701…' или '7701…' (клиент)."""
    now = time.time()
    with db.conn() as c:
        n = c.execute("SELECT COUNT(*) n FROM client_codes WHERE phone=? AND created>?", (key, now - 600)).fetchone()["n"]
        if n >= 3:
            return "Код уже отправлен. Подождите 10 минут."
        code = db.gen_code(4)
        c.execute("INSERT INTO client_codes(phone, code, expires, tries, created) VALUES (?,?,?,?,?)", (key, code, now + 600, 0, now))
    try:
        if not chatapp.is_configured():
            return "Отправка в WhatsApp не настроена."
        chatapp.send_text(phone, text_tpl.format(code=code))
        return ""
    except Exception as e:  # noqa
        return f"Не удалось отправить код в WhatsApp ({str(e)[:80]})."


def check_code(key: str, code: str) -> bool:
    code = re.sub(r"\D", "", code or "")
    with db.conn() as c:
        row = c.execute("SELECT rowid, * FROM client_codes WHERE phone=? ORDER BY created DESC LIMIT 1", (key,)).fetchone()
        ok = bool(row and row["expires"] > time.time() and row["tries"] < 5 and hmac.compare_digest(row["code"], code))
        if row and not ok:
            c.execute("UPDATE client_codes SET tries=tries+1 WHERE rowid=?", (row["rowid"],))
        if ok:
            c.execute("DELETE FROM client_codes WHERE phone=?", (key,))
    return ok


# ------------------------------------------------------------------ сотрудники
_PHONES = {"t": 0, "map": {}}


def staff_by_phone(phone: str) -> Optional[int]:
    """Номер → ID сотрудника Битрикс24 (мобильный/рабочий телефон в профиле). Кэш 10 минут."""
    if time.time() - _PHONES["t"] > 600 or not _PHONES["map"]:
        m = {}
        try:
            start = 0
            while True:
                res = b24people._b24("user.get", {"FILTER": {"ACTIVE": True}, "start": start}) or []
                for u in res:
                    for f in ("PERSONAL_MOBILE", "WORK_PHONE", "PERSONAL_PHONE", "UF_PHONE_INNER"):
                        n = chatapp.normalize_phone(u.get(f) or "")
                        if n and chatapp.is_mobile(n):
                            m.setdefault(n, int(u["ID"]))
                if len(res) < 50 or start > 1000:
                    break
                start += 50
        except Exception:
            pass
        if m:
            _PHONES.update(t=time.time(), map=m)
    uid = _PHONES["map"].get(phone)
    if uid:
        with db.conn() as c:
            r = c.execute("SELECT active FROM users WHERE b24_id=?", (uid,)).fetchone()
        if r is None or not r["active"]:
            return None     # сотрудник ещё не загружен на портал или доступ закрыт
    return uid


def _user(uid):
    with db.conn() as c:
        r = c.execute("SELECT * FROM users WHERE b24_id=?", (uid,)).fetchone()
    return dict(r) if r else {"b24_id": uid}


def _root():
    from . import main as m
    return m._root()


def _login_page(request, **kw):
    from . import main as m
    return m.templates.TemplateResponse("login.html", {"request": request, "brand": config.BRAND, "company": config.COMPANY,
                                                       "base": m._root(), "b24": b24auth.configured(), **kw})


def _session(request, b24_id: int, nxt: str = ""):
    nxt = nxt if (nxt.startswith("/") and not nxt.startswith("//")) else ""
    resp = RedirectResponse(f"{_root()}{nxt or '/cabinet'}", status_code=303)
    b24auth.set_session(resp, b24_id)
    return resp


@router.post("/staff/pw")
def staff_pw(request: Request, phone: str = Form(...), password: str = Form(...), next: str = Form("")):
    ph = chatapp.normalize_phone(phone)
    ok, msg, uid = check_password("staff", ph, password)
    if not ok or not uid:
        b24auth.log_access(request, "denied", None, f"вход по номеру: {msg or 'нет сотрудника'}")
        return _login_page(request, error=msg or "Сотрудник с таким номером не найден.", phone_mode=True, phone=phone)
    b24auth.log_access(request, "login_phone", _user(uid))
    return _session(request, uid, next)


@router.post("/staff/code")
def staff_code(request: Request, phone: str = Form(...)):
    ph = chatapp.normalize_phone(phone)
    uid = staff_by_phone(ph) if chatapp.is_mobile(ph) else None
    if not uid:
        return _login_page(request, phone_mode=True, phone=phone,
                           error="Этот номер не найден в профилях Битрикс24 (мобильный телефон) или у сотрудника нет доступа к порталу.")
    err = send_code("staff:" + ph, ph, "Код для входа в EDO.ANESCOM: {code}\nНикому не сообщайте этот код.")
    if err:
        return _login_page(request, phone_mode=True, phone=phone, error=err)
    return _login_page(request, phone_mode=True, code_step=True, phone=ph)


@router.post("/staff/verify")
def staff_verify(request: Request, phone: str = Form(...), code: str = Form(...), pw1: str = Form(...), pw2: str = Form(...)):
    ph = chatapp.normalize_phone(phone)
    bad = pw_ok(pw1, pw2)
    if bad:
        return _login_page(request, phone_mode=True, code_step=True, phone=ph, error=bad)
    uid = staff_by_phone(ph)
    if not uid or not check_code("staff:" + ph, code):
        return _login_page(request, phone_mode=True, code_step=True, phone=ph, error="Код неверный или устарел.")
    set_password("staff", ph, pw1, uid)
    b24auth.log_access(request, "staff_password_set", _user(uid))
    return _session(request, uid)
