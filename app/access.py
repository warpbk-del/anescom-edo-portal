"""Видимость данных по ролям (портал v4, этап A ч.2 / B).

Кто вошёл (b24auth) → «область» (Scope): что он видит в кабинете документов и в аналитике.

Документы:
  все          — администратор, директор, РОП, бухгалтер;
  менеджер     — где он подписант или менеджер по документу (meta.manager_name / подписант-менеджер);
  кладовщик    — где он подписант + документы своего города (склад из отдела Bitrix24 «Склад Актобе»);
  остальные    — только где он подписант.
  Кадровые     — только администратор, директор, кадровик (личный доступ сотрудника к своим — позже).
Аналитика:
  полная       — администратор, директор, РОП, бухгалтер;
  менеджер     — только свои продажи, оплаты, долги клиентов (по ФИО менеджера в 1С);
  остальные    — своя вкладка ещё не готова (склад/закупки — следующий шаг этапа B).
Общий пароль — как раньше видит всё (запасной вход; отключить: EDO_PASSWORD_LOGIN=0).
Администратор может «смотреть как» любой сотрудник (cookie edo_as).
"""
import json
import re
from dataclasses import dataclass, field
from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse

from . import config, db, b24auth, registry

router = APIRouter()

AS_COOKIE = "edo_as"
FULL_DOCS = {"admin", "director", "rop", "accountant"}
FULL_DASH = {"admin", "director", "rop", "accountant"}
KADR = {"admin", "director", "hr"}


def norm_name(s: str) -> str:
    """«Фамилия Имя» в нижнем регистре: для сравнения ФИО из Bitrix24 и 1С."""
    w = re.sub(r"[^\w\s-]", " ", (s or "").lower().replace("ё", "е")).split()
    return " ".join(w[:2])


@dataclass
class Scope:
    user: Optional[dict] = None          # строка users (кого смотрим)
    real_admin: bool = False             # вошёл администратор (даже если «смотрит как»)
    viewing_as: bool = False
    role: str = "admin"
    full_docs: bool = True
    full_dash: bool = True
    kadr: bool = True
    password: bool = False
    city: str = ""
    names: set = field(default_factory=set)   # варианты ФИО для сопоставления
    mgr_1c: str = ""                         # ФИО менеджера в выгрузке 1С

    @property
    def b24_id(self):
        return (self.user or {}).get("b24_id")


def _city(dept_names: str) -> str:
    low = (dept_names or "").lower()
    for c in registry.CITIES:
        if c.lower() in low:
            return c
    return ""


def manager_1c_name(user: dict) -> str:
    """ФИО менеджера в выгрузке 1С: ручное (users.c1_name) или по совпадению «Фамилия Имя»."""
    if user.get("c1_name"):
        return user["c1_name"]
    key = norm_name(user.get("name") or "")
    if not key:
        return ""
    try:
        from . import analytics
        with analytics.conn() as c:
            for r in c.execute("SELECT DISTINCT manager FROM an_sales WHERE manager<>''"):
                if norm_name(r["manager"]) == key:
                    return r["manager"]
                # в 1С бывает «Имя Фамилия»
                parts = key.split()
                if len(parts) == 2 and norm_name(r["manager"]) == f"{parts[1]} {parts[0]}":
                    return r["manager"]
    except Exception:
        pass
    return ""


def scope(request: Request) -> Scope:
    u = b24auth.current_user(request)
    if not u:
        # общий пароль — видит всё, как раньше
        return Scope(password=True)
    real_admin = u.get("role") == "admin"
    viewing = False
    if real_admin:
        try:
            as_id = int(request.cookies.get(AS_COOKIE) or 0)
        except ValueError:
            as_id = 0
        if as_id and as_id != u["b24_id"]:
            with db.conn() as c:
                row = c.execute("SELECT * FROM users WHERE b24_id=?", (as_id,)).fetchone()
            if row:
                u, viewing = dict(row), True
    role = u.get("role") or "staff"
    s = Scope(user=u, real_admin=real_admin, viewing_as=viewing, role=role,
              full_docs=role in FULL_DOCS, full_dash=role in FULL_DASH, kadr=role in KADR,
              city=_city(u.get("dept_names") or ""))
    s.names = {norm_name(u.get("name") or "")} - {""}
    if role == "manager":
        s.mgr_1c = manager_1c_name(u)
        if s.mgr_1c:
            s.names.add(norm_name(s.mgr_1c))
    return s


# ------------------------------------------------------------------ документы
def _meta(row) -> dict:
    try:
        return json.loads(row["meta"] or "{}")
    except Exception:
        return {}


def visible_doc_ids(s: Scope, c) -> Optional[set]:
    """None — видит все; иначе множество id документов."""
    if s.full_docs:
        return None
    ids = set()
    uid = str(s.b24_id or "")
    for r in c.execute("SELECT document_id, name, b24_user_id FROM signers"):
        if (uid and str(r["b24_user_id"] or "") == uid) or (r["name"] and norm_name(r["name"]) in s.names):
            ids.add(r["document_id"])
    if s.role in ("manager", "storekeeper"):
        for r in c.execute("SELECT id, title, meta FROM documents"):
            m = _meta(r)
            if s.role == "manager" and m.get("manager_name") and norm_name(m["manager_name"]) in s.names:
                ids.add(r["id"])
            if s.role == "storekeeper" and s.city and registry.department(r) == s.city:
                ids.add(r["id"])
    return ids


def filter_docs(s: Scope, c, docs: list) -> list:
    ids = visible_doc_ids(s, c)
    out = [d for d in docs if ids is None or d["id"] in ids]
    if not s.kadr:
        out = [d for d in out if d.get("cat") != "kadr"]
    return out


def require_doc(request: Request, doc_id: str):
    """403, если документ не в области пользователя."""
    s = scope(request)
    if s.full_docs and s.kadr:
        return
    with db.conn() as c:
        row = c.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        if not row:
            return
        if not s.kadr and registry.category(row) == "kadr":
            raise HTTPException(403, "Кадровые документы вам не доступны")
        ids = visible_doc_ids(s, c)
    if ids is not None and doc_id not in ids:
        raise HTTPException(403, "Этот документ не в вашей зоне доступа")


def doc_of_signer(sid: str) -> Optional[str]:
    with db.conn() as c:
        r = c.execute("SELECT document_id FROM signers WHERE id=?", (sid,)).fetchone()
    return r["document_id"] if r else None


# ------------------------------------------------------------------ «смотреть как»
@router.get("/cabinet/as")
def view_as(request: Request, u: int = 0, back: str = "/cabinet"):
    me = b24auth.current_user(request)
    if not me or me.get("role") != "admin":
        raise HTTPException(403, "Только для администратора")
    from . import main
    nxt = back if back.startswith("/") else "/cabinet"
    resp = RedirectResponse(f"{main._root()}{nxt}", status_code=303)
    if u and u != me["b24_id"]:
        resp.set_cookie(AS_COOKIE, str(u), max_age=60 * 60 * 8, httponly=True, secure=True, samesite="lax")
        b24auth.log_access(request, "view_as", me, f"смотрит как ID {u}")
    else:
        resp.delete_cookie(AS_COOKIE)
    return resp
