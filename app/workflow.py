"""Многошаговое подписание (цепочка подписантов) — накладная З-2 и любые документы.

Шаги идут по очереди; внутри шага может быть несколько кандидатов — подписывает
любой из них (кладовщик ИЛИ помощник кладовщика), остальные помечаются «skipped».
Ссылка и код следующему шагу уходят только после подписи предыдущего.

Таблица signers — по строке на кандидата; у каждого свой токен ссылки и код (ПЭП).
Документ с цепочкой: documents.workflow=1, status: in_progress → signed (или cancelled).

Модуль не зависит от FastAPI: маршруты — в app/z2.py.
"""
import json
import logging

from . import config, db

log = logging.getLogger("edo.workflow")

ROLE_TITLES = {
    "manager": "Менеджер",
    "storekeeper": "Кладовщик / помощник кладовщика",
    "client": "Клиент",
}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS signers (
    id           TEXT PRIMARY KEY,
    document_id  TEXT NOT NULL,
    step         INTEGER NOT NULL,     -- 1, 2, 3 …
    role         TEXT NOT NULL,        -- manager | storekeeper | client | другое
    role_title   TEXT,
    name         TEXT,                 -- ожидаемый подписант (из Bitrix/1С)
    phone        TEXT,
    b24_user_id  TEXT,
    token        TEXT UNIQUE NOT NULL,
    code         TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'waiting',  -- waiting|active|viewed|signed|skipped|cancelled
    activated_at TEXT,
    viewed_at    TEXT,
    signed_at    TEXT,
    signer_name  TEXT,                 -- ФИО, введённое при подписи
    signer_ip    TEXT,
    signer_ua    TEXT,
    wa_status    TEXT,                 -- sent | manual | error | off
    wa_detail    TEXT
);
CREATE INDEX IF NOT EXISTS idx_signers_doc ON signers(document_id);
"""


def init(c):
    c.executescript(_SCHEMA)
    cols = {r[1] for r in c.execute("PRAGMA table_info(documents)").fetchall()}
    if "workflow" not in cols:
        c.execute("ALTER TABLE documents ADD COLUMN workflow INTEGER DEFAULT 0")
    if "current_step" not in cols:
        c.execute("ALTER TABLE documents ADD COLUMN current_step INTEGER")


def signers(c, doc_id):
    return c.execute("SELECT * FROM signers WHERE document_id=? ORDER BY step, rowid",
                     (doc_id,)).fetchall()


def signer_by_token(c, token):
    return c.execute("SELECT * FROM signers WHERE token=?", (token,)).fetchone()


def signer(c, sid):
    return c.execute("SELECT * FROM signers WHERE id=?", (sid,)).fetchone()


def add_signers(c, doc_id, steps):
    """steps: [[{role, name, phone, b24_user_id, role_title}], …] — список шагов из кандидатов."""
    for i, cands in enumerate(steps, start=1):
        for s in cands:
            role = s.get("role") or "other"
            c.execute(
                """INSERT INTO signers(id, document_id, step, role, role_title, name, phone,
                       b24_user_id, token, code, status)
                   VALUES(?,?,?,?,?,?,?,?,?,?, 'waiting')""",
                (db.gen_token(8), doc_id, i, role,
                 s.get("role_title") or ROLE_TITLES.get(role, role),
                 s.get("name"), s.get("phone") or None,
                 str(s["b24_user_id"]) if s.get("b24_user_id") else None,
                 db.gen_token(24), db.gen_code()),
            )
    c.execute("UPDATE documents SET workflow=1, status='in_progress', current_step=NULL WHERE id=?",
              (doc_id,))


def activate_step(c, doc_id, step, ip=None):
    """Делает шаг активным. Возвращает id кандидатов, которым нужно отправить ссылку."""
    rows = c.execute("SELECT id FROM signers WHERE document_id=? AND step=? AND status='waiting'",
                     (doc_id, step)).fetchall()
    now = db.now_iso()
    c.execute("UPDATE signers SET status='active', activated_at=? "
              "WHERE document_id=? AND step=? AND status='waiting'", (now, doc_id, step))
    c.execute("UPDATE documents SET current_step=?, sent_at=COALESCE(sent_at,?) WHERE id=?",
              (step, now, doc_id))
    db.add_event(c, doc_id, "step_started", ip=ip, detail=f"Шаг {step}: {_step_title(c, doc_id, step)}")
    return [r["id"] for r in rows]


def start(c, doc_id, ip=None):
    return activate_step(c, doc_id, 1, ip)


def _step_title(c, doc_id, step):
    r = c.execute("SELECT role_title FROM signers WHERE document_id=? AND step=? LIMIT 1",
                  (doc_id, step)).fetchone()
    return r["role_title"] if r else ""


def mark_viewed(c, s, ip=None, ua=None):
    if s["status"] == "active":
        c.execute("UPDATE signers SET status='viewed', viewed_at=COALESCE(viewed_at,?) WHERE id=?",
                  (db.now_iso(), s["id"]))
        db.add_event(c, s["document_id"], "step_viewed", ip=ip, ua=ua,
                     detail=f"Шаг {s['step']} · {s['role_title']} · {s['name'] or ''}".strip())


def check_code(s, code) -> bool:
    return (code or "").strip() == s["code"]


def sign(c, s, signer_name, ip=None, ua=None):
    """Фиксирует подпись кандидата. Возвращает (completed: bool, next_ids: list)."""
    doc_id, step = s["document_id"], s["step"]
    now = db.now_iso()
    c.execute("UPDATE signers SET status='signed', signed_at=?, signer_name=?, signer_ip=?, "
              "signer_ua=? WHERE id=?", (now, signer_name.strip(), ip, ua, s["id"]))
    c.execute("UPDATE signers SET status='skipped' WHERE document_id=? AND step=? AND id<>? "
              "AND status IN ('active','viewed','waiting')", (doc_id, step, s["id"]))
    doc = db.get_doc(c, doc_id)
    db.add_event(c, doc_id, "step_signed", ip=ip, ua=ua,
                 detail=f"Шаг {step} · {s['role_title']} · ФИО: {signer_name.strip()}; "
                        f"код подтверждён; хэш={doc['doc_hash']}")
    nxt = c.execute("SELECT MIN(step) m FROM signers WHERE document_id=? AND step>? "
                    "AND status='waiting'", (doc_id, step)).fetchone()["m"]
    if nxt:
        return False, activate_step(c, doc_id, nxt, ip)
    # все шаги пройдены
    last = s  # для совместимости старых полей документа — последний подписант (обычно клиент)
    c.execute("UPDATE documents SET status='signed', signed_at=?, signer_name=?, signer_ip=?, "
              "signer_ua=?, current_step=NULL WHERE id=?",
              (now, last_name(signer_name), ip, ua, doc_id))
    db.add_event(c, doc_id, "completed", ip=ip, detail="Документ подписан всеми сторонами")
    return True, []


def last_name(n):
    return (n or "").strip()


def cancel(c, doc_id, reason="", ip=None):
    c.execute("UPDATE signers SET status='cancelled' WHERE document_id=? "
              "AND status IN ('waiting','active','viewed')", (doc_id,))
    c.execute("UPDATE documents SET status='cancelled', current_step=NULL WHERE id=?", (doc_id,))
    db.add_event(c, doc_id, "cancelled", ip=ip, detail=reason or None)


def set_phone(c, sid, phone, ip=None):
    s = signer(c, sid)
    c.execute("UPDATE signers SET phone=? WHERE id=?", (phone, sid))
    db.add_event(c, s["document_id"], "signer_phone", ip=ip,
                 detail=f"Шаг {s['step']} · {s['role_title']}: телефон указан в кабинете")


def summary(rows):
    """Для API: шаги с кандидатами."""
    out = {}
    for r in rows:
        out.setdefault(r["step"], []).append({
            "id": r["id"], "role": r["role"], "role_title": r["role_title"],
            "name": r["name"], "has_phone": bool(r["phone"]), "status": r["status"],
            "signed_at": r["signed_at"], "signer_name": r["signer_name"],
            "wa_status": r["wa_status"],
            "sign_url": f"{config.PUBLIC_BASE_URL}/s/{r['token']}",
        })
    return [{"step": k, "candidates": v} for k, v in sorted(out.items())]


# ------------------------------------------------------------------ сообщения
def build_message(s, doc) -> str:
    link = f"{config.PUBLIC_BASE_URL}/s/{s['token']}"
    hello = f"Здравствуйте, {s['name']}!" if s["name"] else "Здравствуйте!"
    if s["role"] == "client":
        who = f"{config.COMPANY} направляет вам документ на подпись"
    else:
        who = f"Документ ждёт вашей подписи ({s['role_title'].lower()})"
    return (f"{hello}\n\n{who}: «{doc['title']}».\n\n"
            f"Ссылка для ознакомления и подписания:\n{link}\n\n"
            f"Код подтверждения: {s['code']}\n(введите его на странице подписания)\n\n"
            f"Портал {config.BRAND}.")


def build_done_message(doc) -> str:
    link = f"{config.PUBLIC_BASE_URL}/s/{doc['sign_token']}"
    return (f"Документ «{doc['title']}» подписан всеми сторонами.\n"
            f"Проверка и квитанция: {link}\n\nПортал {config.BRAND}.")


def _allowed(phone) -> bool:
    from . import chatapp
    mode = config.SIGN_NOTIFY_MODE
    if mode == "live":
        return True
    if mode == "test":
        n = chatapp.normalize_phone(phone)
        return n in {chatapp.normalize_phone(x) for x in config.SIGN_TEST_PHONES}
    return False


def send_text_safe(phone, text):
    """→ (wa_status, detail). Никогда не бросает исключений."""
    from . import chatapp
    n = chatapp.first_phone(phone or "")
    if not n:
        return "manual", "нет мобильного телефона"
    if not chatapp.is_configured():
        return "manual", "ChatApp не настроен"
    if not _allowed(n):
        return "manual", f"режим {config.SIGN_NOTIFY_MODE}"
    try:
        chatapp.send_text(n, text)
        return "sent", ""
    except Exception as e:  # noqa
        log.exception("Ошибка отправки ссылки на подпись")
        return "error", str(e)[:300]


def notify(signer_ids, ip=None):
    """Отправляет ссылки кандидатам (отдельные короткие транзакции вокруг сети)."""
    res = []
    for sid in signer_ids:
        with db.conn() as c:
            s = signer(c, sid)
            doc = db.get_doc(c, s["document_id"])
        st, det = send_text_safe(s["phone"], build_message(s, doc))
        with db.conn() as c:
            c.execute("UPDATE signers SET wa_status=?, wa_detail=? WHERE id=?", (st, det, sid))
            db.add_event(c, s["document_id"], "step_sent", ip=ip,
                         detail=f"Шаг {s['step']} · {s['role_title']} · {s['name'] or '—'}: "
                                f"{st}{(' — ' + det) if det else ''}")
        res.append({"id": sid, "wa_status": st, "detail": det})
    return res


def notify_done(doc_id, ip=None):
    """Документ подписан всеми — сообщить менеджеру (шаг manager)."""
    with db.conn() as c:
        doc = db.get_doc(c, doc_id)
        mgr = c.execute("SELECT * FROM signers WHERE document_id=? AND role='manager' "
                        "AND status='signed' LIMIT 1", (doc_id,)).fetchone()
    if not mgr:
        return None
    st, det = send_text_safe(mgr["phone"], build_done_message(doc))
    with db.conn() as c:
        db.add_event(c, doc_id, "done_sent", ip=ip, detail=f"менеджеру: {st}{(' — ' + det) if det else ''}")
    return st


def meta(doc) -> dict:
    try:
        return json.loads(doc["meta"] or "{}")
    except Exception:
        return {}
