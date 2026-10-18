"""Вход сотрудников через Bitrix24 (этап A, часть 2 портала v4).

Два пути входа, оба дают одну и ту же сессию (cookie edo_user):
  1) Из меню Bitrix24 — локальное приложение «EDO.ANESCOM» (обработчик /b24/app). Bitrix24 открывает
     портал во фрейме и присылает POST с AUTH_ID и DOMAIN; по AUTH_ID спрашиваем user.current.
  2) С сайта — кнопка «Войти через Битрикс24» (/b24/login → OAuth Bitrix24 → /b24/oauth).

Настройки (config.env): B24_DOMAIN, B24_CLIENT_ID, B24_CLIENT_SECRET (из карточки локального
приложения), B24_ADMIN_IDS — ID пользователей Bitrix24 с ролью «Администратор» (через запятую).
Старый вход общим паролем остаётся запасным (кнопка «Войти по паролю»).

Роли: портал предлагает роль по должности и отделу из Bitrix24 (suggest_role); подтверждает и правит
администратор на странице «Роли» (следующий шаг). Каждый вход пишется в журнал access_log.
"""
import hashlib
import hmac
import json
import logging
import secrets
import time
import urllib.parse
from typing import Optional

import httpx
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from . import config, db

log = logging.getLogger("edo.b24auth")
router = APIRouter()

COOKIE = "edo_user"
MAX_AGE = 60 * 60 * 24 * 14  # 14 дней

ROLES = {
    "admin": "Администратор",
    "director": "Директор",
    "rop": "Руководитель отдела продаж",
    "manager": "Менеджер",
    "accountant": "Бухгалтер",
    "storekeeper": "Кладовщик",
    "purchaser": "Закупщик",
    "hr": "Кадровик",
    "staff": "Сотрудник",
}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    b24_id        INTEGER PRIMARY KEY,
    name          TEXT,
    position      TEXT,
    email         TEXT,
    dept_ids      TEXT,              -- JSON [id, …] из Bitrix24
    dept_names    TEXT,              -- через «; »
    role          TEXT,              -- действующая роль (после подтверждения админом)
    role_suggest  TEXT,              -- предложенная порталом
    role_confirmed INTEGER DEFAULT 0,
    active        INTEGER DEFAULT 1,
    created_at    TEXT,
    last_login    TEXT
);
CREATE TABLE IF NOT EXISTS access_log (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ts      TEXT NOT NULL,
    b24_id  INTEGER,
    name    TEXT,
    action  TEXT NOT NULL,           -- login_b24app | login_oauth | login_password | logout | denied
    ip      TEXT,
    ua      TEXT,
    detail  TEXT
);
"""


def init():
    with db.conn() as c:
        c.executescript(_SCHEMA)
        cols = {r[1] for r in c.execute("PRAGMA table_info(users)")}
        if "c1_name" not in cols:   # ФИО менеджера в 1С (если не совпадает с Bitrix24)
            c.execute("ALTER TABLE users ADD COLUMN c1_name TEXT")


def configured() -> bool:
    return bool(config.B24_DOMAIN and config.B24_CLIENT_ID and config.B24_CLIENT_SECRET)


# ------------------------------------------------------------------ сессия
def _sign(payload: str) -> str:
    return hmac.new(config.SECRET_KEY.encode(), ("u|" + payload).encode(), hashlib.sha256).hexdigest()[:32]


def make_session(b24_id: int) -> str:
    p = f"{int(b24_id)}.{int(time.time())}"
    return f"{p}.{_sign(p)}"


def _session_uid(value: Optional[str]) -> Optional[int]:
    try:
        uid, ts, sig = (value or "").split(".")
        p = f"{uid}.{ts}"
        if not hmac.compare_digest(sig, _sign(p)):
            return None
        if time.time() - int(ts) > MAX_AGE:
            return None
        return int(uid)
    except Exception:
        return None


def current_user(request: Request) -> Optional[dict]:
    uid = _session_uid(request.cookies.get(COOKIE))
    if not uid:
        return None
    with db.conn() as c:
        row = c.execute("SELECT * FROM users WHERE b24_id=? AND active=1", (uid,)).fetchone()
    return dict(row) if row else None


def set_session(resp, b24_id: int, in_frame: bool = False):
    # во фрейме Bitrix24 cookie должна быть SameSite=None; Secure
    resp.set_cookie(COOKIE, make_session(b24_id), max_age=MAX_AGE, httponly=True,
                    secure=True, samesite="none" if in_frame else "lax")


def clear_session(resp):
    resp.delete_cookie(COOKIE)


# ------------------------------------------------------------------ роли
def suggest_role(b24_id: int, position: str, dept_names: str) -> str:
    if b24_id in config.B24_ADMIN_IDS:
        return "admin"
    p = (position or "").lower()
    d = (dept_names or "").lower()
    if "кадр" in p or "hr" in p:
        return "hr"
    if "руководитель отдела продаж" in p or ("руководител" in p and "продаж" in (p + d)):
        return "rop"
    if "директор" in p:
        return "director"
    if "бухгалт" in p or "бухгалт" in d:
        return "accountant"
    if "закуп" in p or "снабж" in p:
        return "purchaser"
    if "кладов" in p:
        return "storekeeper"
    if "менеджер" in p or "продаж" in d:
        return "manager"
    return "staff"


# ------------------------------------------------------------------ Bitrix24 REST
def _rest(method: str, auth: str, params: Optional[dict] = None):
    r = httpx.post(f"https://{config.B24_DOMAIN}/rest/{method}.json",
                   data={**(params or {}), "auth": auth}, timeout=20)
    js = r.json()
    if r.status_code >= 400 or "error" in js:
        raise RuntimeError(f"{method}: {js.get('error_description') or js.get('error') or r.status_code}")
    return js.get("result")


def _dept_names(ids: list, auth: str) -> str:
    names = []
    for i in ids[:10]:
        try:
            res = _rest("department.get", auth, {"ID": i})
            if res:
                names.append(res[0].get("NAME", ""))
        except Exception:
            # у приложения может не быть права department — тогда пробуем вебхуком портала
            try:
                from . import b24people
                res = b24people._b24("department.get", {"ID": i})
                if res:
                    names.append(res[0].get("NAME", ""))
            except Exception:
                pass
    return "; ".join(n for n in names if n)


def _upsert_user(auth: str) -> dict:
    u = _rest("user.current", auth)
    uid = int(u["ID"])
    name = " ".join(x for x in (u.get("LAST_NAME"), u.get("NAME")) if x).strip() or u.get("EMAIL") or f"ID {uid}"
    position = u.get("WORK_POSITION") or ""
    dept_ids = [int(x) for x in (u.get("UF_DEPARTMENT") or []) if str(x).isdigit()]
    dept_names = _dept_names(dept_ids, auth)
    sug = suggest_role(uid, position, dept_names)
    now = db.now_iso()
    with db.conn() as c:
        row = c.execute("SELECT * FROM users WHERE b24_id=?", (uid,)).fetchone()
        if row:
            role = row["role"] if row["role_confirmed"] else sug
            if uid in config.B24_ADMIN_IDS:
                role = "admin"
            c.execute("""UPDATE users SET name=?, position=?, email=?, dept_ids=?, dept_names=?,
                         role_suggest=?, role=?, last_login=? WHERE b24_id=?""",
                      (name, position, u.get("EMAIL"), json.dumps(dept_ids), dept_names, sug, role, now, uid))
        else:
            c.execute("""INSERT INTO users (b24_id, name, position, email, dept_ids, dept_names, role,
                         role_suggest, role_confirmed, active, created_at, last_login)
                         VALUES (?,?,?,?,?,?,?,?,?,1,?,?)""",
                      (uid, name, position, u.get("EMAIL"), json.dumps(dept_ids), dept_names, sug, sug,
                       1 if uid in config.B24_ADMIN_IDS else 0, now, now))
        row = c.execute("SELECT * FROM users WHERE b24_id=?", (uid,)).fetchone()
    return dict(row)


def log_access(request: Request, action: str, user: Optional[dict] = None, detail: str = ""):
    xff = request.headers.get("x-forwarded-for")
    ip = xff.split(",")[0].strip() if xff else (request.client.host if request.client else "?")
    with db.conn() as c:
        c.execute("INSERT INTO access_log (ts, b24_id, name, action, ip, ua, detail) VALUES (?,?,?,?,?,?,?)",
                  (db.now_iso(), (user or {}).get("b24_id"), (user or {}).get("name"), action, ip,
                   (request.headers.get("user-agent") or "")[:300], detail[:500]))


# ------------------------------------------------------------------ маршруты
def _root() -> str:
    from . import main
    return main._root()


def _frame_redirect(url: str) -> HTMLResponse:
    # внутри фрейма Bitrix24 обычный 303 после POST иногда теряет cookie — переходим скриптом
    u = json.dumps(url)
    return HTMLResponse(f"<!doctype html><meta charset=utf-8><script>location.replace({u});</script>"
                        f"<a href={u}>Открыть EDO.ANESCOM</a>")


@router.api_route("/b24/app", methods=["GET", "POST"])
async def b24_app(request: Request):
    """Обработчик локального приложения Bitrix24 (пункт меню «EDO.ANESCOM»)."""
    form = {}
    if request.method == "POST":
        try:
            form = dict(await request.form())
        except Exception:
            form = {}
    auth = form.get("AUTH_ID") or request.query_params.get("AUTH_ID")
    domain = (form.get("DOMAIN") or request.query_params.get("DOMAIN") or "").lower()
    qp = request.query_params
    if not auth and qp.get("code") and qp.get("state"):
        # Bitrix24 возвращает OAuth-ответ на адрес обработчика приложения, а не на redirect_uri
        return b24_oauth(request, qp.get("code"), qp.get("state"), qp.get("server_domain", ""))
    if not auth:
        # открыли не из Bitrix24 — обычный вход
        return RedirectResponse(f"{_root()}/b24/login", status_code=303)
    if config.B24_DOMAIN and domain and domain != config.B24_DOMAIN.lower():
        log_access(request, "denied", None, f"чужой портал {domain}")
        raise HTTPException(403, "Приложение открыто не из портала ANESCOM")
    try:
        user = _upsert_user(auth)
    except Exception as e:
        log.exception("b24 app auth")
        log_access(request, "denied", None, f"user.current: {e}")
        raise HTTPException(401, "Bitrix24 не подтвердил пользователя")
    log_access(request, "login_b24app", user)
    resp = _frame_redirect(f"{_root()}/cabinet")
    set_session(resp, user["b24_id"], in_frame=True)
    return resp


@router.api_route("/b24/install", methods=["GET", "POST"])
async def b24_install():
    """Обработчик установки локального приложения — просто завершаем установку."""
    return HTMLResponse("<!doctype html><meta charset=utf-8>"
                        "<script src='//api.bitrix24.com/api/v1/'></script>"
                        "<script>BX24.init(function(){BX24.installFinish();});</script>"
                        "Установка EDO.ANESCOM завершена.")


def _state(next_url: str) -> str:
    nonce = secrets.token_urlsafe(8)
    p = f"{nonce}|{next_url}"
    return urllib.parse.quote(p + "|" + _sign(p), safe="")


def _check_state(state: str) -> Optional[str]:
    try:
        nonce, nxt, sig = urllib.parse.unquote(state).split("|")
        if hmac.compare_digest(sig, _sign(f"{nonce}|{nxt}")) and nxt.startswith("/"):
            return nxt
    except Exception:
        pass
    return None


def _redirect_uri() -> str:
    return f"{config.PUBLIC_BASE_URL}/b24/oauth"


@router.get("/b24/login")
def b24_login(next: str = "/cabinet"):
    if not configured():
        return RedirectResponse(f"{_root()}/cabinet", status_code=303)
    q = urllib.parse.urlencode({"client_id": config.B24_CLIENT_ID, "response_type": "code",
                                "redirect_uri": _redirect_uri()})
    return RedirectResponse(f"https://{config.B24_DOMAIN}/oauth/authorize/?{q}&state={_state(next)}",
                            status_code=303)


_OAUTH_SERVERS = ("oauth.bitrix.info", "oauth.bitrix24.tech")


@router.get("/b24/oauth")
def b24_oauth(request: Request, code: str = "", state: str = "", server_domain: str = ""):
    nxt = _check_state(state)
    if not code or not nxt:
        log_access(request, "denied", None, "oauth: нет code или неверный state")
        raise HTTPException(400, "Неверный ответ Bitrix24 — попробуйте войти ещё раз")
    try:
        srv = server_domain if server_domain in _OAUTH_SERVERS else "oauth.bitrix.info"
        r = httpx.get(f"https://{srv}/oauth/token/", timeout=20, params={
            "grant_type": "authorization_code", "client_id": config.B24_CLIENT_ID,
            "client_secret": config.B24_CLIENT_SECRET, "code": code})
        tok = r.json()
        if "access_token" not in tok:
            raise RuntimeError(tok.get("error_description") or tok.get("error") or r.status_code)
        # адрес портала — в client_endpoint (https://<портал>/rest/); domain — это OAuth-сервер Bitrix24
        portal = urllib.parse.urlparse(tok.get("client_endpoint") or "").hostname or ""
        if config.B24_DOMAIN and portal and portal.lower() != config.B24_DOMAIN.lower():
            raise RuntimeError(f"чужой портал {portal}")
        user = _upsert_user(tok["access_token"])
    except Exception as e:
        log.exception("b24 oauth")
        log_access(request, "denied", None, f"oauth: {e}")
        raise HTTPException(401, "Не удалось войти через Bitrix24")
    log_access(request, "login_oauth", user)
    resp = RedirectResponse(f"{_root()}{nxt}", status_code=303)
    set_session(resp, user["b24_id"])
    return resp


# ------------------------------------------------------------------ для шаблонов
def me(request: Request) -> dict:
    """Кто вошёл — для боковой панели: имя, роль, инициал, админ ли."""
    u = current_user(request)
    if u:
        from . import access
        s = access.scope(request)
        if s.viewing_as:
            v = s.user
            name = v.get("name") or "Сотрудник"
            return {"name": name, "role": "смотрите как: " + ROLES.get(v.get("role") or "staff", "Сотрудник"),
                    "initial": name[:1].upper(), "admin": False, "b24": True, "as_banner": True}
        name = u.get("name") or "Сотрудник"
        return {"name": name, "role": ROLES.get(u.get("role") or "staff", "Сотрудник"),
                "initial": name[:1].upper(), "admin": u.get("role") == "admin", "b24": True, "as_banner": False}
    return {"name": config.COMPANY, "role": "общий вход (пароль)", "initial": "A", "admin": False, "b24": False,
            "as_banner": False}


def is_admin(request: Request) -> bool:
    u = current_user(request)
    return bool(u and u.get("role") == "admin")


# ------------------------------------------------------------------ загрузка сотрудников из Bitrix24 (вебхук)
def _hook_all(method: str, params: dict) -> list:
    if not config.B24_WEBHOOK:
        raise RuntimeError("Не настроен вебхук Bitrix24 (EDO_B24_WEBHOOK)")
    out, start = [], 0
    for _ in range(60):  # до 3000 записей
        r = httpx.post(f"{config.B24_WEBHOOK}/{method}.json", json={**params, "start": start}, timeout=30)
        js = r.json()
        if "error" in js:
            raise RuntimeError(f"{method}: {js.get('error_description') or js['error']}")
        out += js.get("result") or []
        if "next" not in js:
            break
        start = js["next"]
    return out


def sync_users() -> dict:
    """Все активные сотрудники Bitrix24 → таблица users. Подтверждённые админом роли не меняются."""
    depts = {int(d["ID"]): d.get("NAME", "") for d in _hook_all("department.get", {})}
    users = _hook_all("user.get", {"FILTER": {"ACTIVE": True, "USER_TYPE": "employee"}})
    now = db.now_iso()
    added = updated = 0
    with db.conn() as c:
        for u in users:
            uid = int(u["ID"])
            name = " ".join(x for x in (u.get("LAST_NAME"), u.get("NAME")) if x).strip() or u.get("EMAIL") or f"ID {uid}"
            position = u.get("WORK_POSITION") or ""
            ids = [int(x) for x in (u.get("UF_DEPARTMENT") or []) if str(x).isdigit()]
            names = "; ".join(depts.get(i, "") for i in ids if depts.get(i))
            sug = suggest_role(uid, position, names)
            row = c.execute("SELECT role, role_confirmed FROM users WHERE b24_id=?", (uid,)).fetchone()
            if row:
                role = row["role"] if row["role_confirmed"] else sug
                c.execute("""UPDATE users SET name=?, position=?, email=?, dept_ids=?, dept_names=?,
                             role_suggest=?, role=? WHERE b24_id=?""",
                          (name, position, u.get("EMAIL"), json.dumps(ids), names, sug, role, uid))
                updated += 1
            else:
                c.execute("""INSERT INTO users (b24_id, name, position, email, dept_ids, dept_names, role,
                             role_suggest, role_confirmed, active, created_at) VALUES (?,?,?,?,?,?,?,?,?,1,?)""",
                          (uid, name, position, u.get("EMAIL"), json.dumps(ids), names, sug, sug,
                           1 if uid in config.B24_ADMIN_IDS else 0, now))
                added += 1
    return {"total": len(users), "added": added, "updated": updated}


# ------------------------------------------------------------------ страница «Роли и доступ»
def _templates():
    from . import main
    return main.templates


@router.get("/cabinet/roles", response_class=HTMLResponse)
def roles_page(request: Request, q: str = "", role: str = "", msg: str = ""):
    if not is_admin(request):
        if current_user(request) is None:
            return RedirectResponse(f"{_root()}/b24/login?next=/cabinet/roles", status_code=303)
        raise HTTPException(403, "Страница «Роли и доступ» — только для администратора")
    with db.conn() as c:
        rows = [dict(r) for r in c.execute("SELECT * FROM users ORDER BY active DESC, name")]
        log_rows = [dict(r) for r in c.execute("SELECT * FROM access_log ORDER BY id DESC LIMIT 100")]
    counts = {}
    for r in rows:
        counts[r["role"] or "staff"] = counts.get(r["role"] or "staff", 0) + 1
    if q:
        ql = q.lower()
        rows = [r for r in rows if ql in " ".join(str(r.get(k) or "") for k in ("name", "position", "dept_names")).lower()]
    if role:
        rows = [r for r in rows if (r["role"] or "staff") == role]
    from . import registry, access
    for r in rows:
        r["mgr_1c"] = access.manager_1c_name(r) if r.get("role") == "manager" else ""
    return _templates().TemplateResponse("roles.html", {
        "request": request, "brand": config.BRAND, "base": _root(), "rows": rows, "log": log_rows,
        "roles": ROLES, "counts": counts, "q": q, "role": role, "msg": msg,
        "unconfirmed": sum(1 for r in rows if not r["role_confirmed"] and r["active"]),
        "local_time": registry.local_time, "webhook": bool(config.B24_WEBHOOK),
    })


@router.post("/cabinet/roles/save")
def roles_save(request: Request, b24_id: int = Form(...), role: str = Form(...), active: str = Form(""),
               c1_name: str = Form("")):
    if not is_admin(request):
        raise HTTPException(403, "Только для администратора")
    if role not in ROLES:
        raise HTTPException(400, "Неизвестная роль")
    me_ = current_user(request)
    if b24_id == me_["b24_id"] and (role != "admin" or not active):
        return RedirectResponse(f"{_root()}/cabinet/roles?msg=self", status_code=303)
    with db.conn() as c:
        c.execute("UPDATE users SET role=?, role_confirmed=1, active=?, c1_name=? WHERE b24_id=?",
                  (role, 1 if active else 0, c1_name.strip() or None, b24_id))
    log_access(request, "role_set", me_, f"ID {b24_id} → {role}{'' if active else ', доступ закрыт'}")
    return RedirectResponse(f"{_root()}/cabinet/roles?msg=saved#u{b24_id}", status_code=303)


@router.post("/cabinet/roles/confirm-all")
def roles_confirm_all(request: Request):
    if not is_admin(request):
        raise HTTPException(403, "Только для администратора")
    with db.conn() as c:
        n = c.execute("UPDATE users SET role_confirmed=1 WHERE role_confirmed=0 AND active=1").rowcount
    log_access(request, "role_confirm_all", current_user(request), f"подтверждено {n}")
    return RedirectResponse(f"{_root()}/cabinet/roles?msg=confirmed", status_code=303)


@router.post("/cabinet/roles/sync")
def roles_sync(request: Request):
    if not is_admin(request):
        raise HTTPException(403, "Только для администратора")
    try:
        res = sync_users()
    except Exception as e:
        log.exception("sync users")
        return RedirectResponse(f"{_root()}/cabinet/roles?msg=" + urllib.parse.quote(f"err:{e}"[:200]), status_code=303)
    log_access(request, "users_sync", current_user(request), json.dumps(res, ensure_ascii=False))
    return RedirectResponse(f"{_root()}/cabinet/roles?msg=sync:{res['total']}:{res['added']}", status_code=303)
