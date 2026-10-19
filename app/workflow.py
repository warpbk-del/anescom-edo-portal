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
    "hr": "Кадровик",
    "employee": "Сотрудник",
    "acquaint": "Ознакомление",
    "head": "Руководитель подразделения",
    "director": "Директор",
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
    # ч.2 подписания (18.10.2026): напоминания и отклонение
    for col, typ in (("remind_count", "INTEGER DEFAULT 0"), ("reminded_at", "TEXT")):
        if col not in cols:
            c.execute(f"ALTER TABLE documents ADD COLUMN {col} {typ}")
    scols = {r[1] for r in c.execute("PRAGMA table_info(signers)").fetchall()}
    for col, typ in (("remind_count", "INTEGER DEFAULT 0"), ("reminded_at", "TEXT"),
                     ("decline_reason", "TEXT"), ("sign_method", "TEXT"),
                     ("all_of", "INTEGER DEFAULT 0")):   # 6п: шаг подписывают все кандидаты, а не любой
        if col not in scols:
            c.execute(f"ALTER TABLE signers ADD COLUMN {col} {typ}")


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
                       b24_user_id, token, code, status, all_of)
                   VALUES(?,?,?,?,?,?,?,?,?,?, 'waiting', ?)""",
                (db.gen_token(8), doc_id, i, role,
                 s.get("role_title") or ROLE_TITLES.get(role, role),
                 s.get("name"), s.get("phone") or None,
                 str(s["b24_user_id"]) if s.get("b24_user_id") else None,
                 db.gen_token(24), db.gen_code(), 1 if s.get("all_of") else 0),
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


def sign(c, s, signer_name, ip=None, ua=None, method="code"):
    """Фиксирует подпись кандидата. Возвращает (completed: bool, next_ids: list).
    method: code — код из сообщения; b24 — в кабинете после входа через Bitrix24 (массовая подпись)."""
    doc_id, step = s["document_id"], s["step"]
    now = db.now_iso()
    c.execute("UPDATE signers SET status='signed', signed_at=?, signer_name=?, signer_ip=?, "
              "signer_ua=?, sign_method=? WHERE id=?", (now, signer_name.strip(), ip, ua, method, s["id"]))
    try:
        all_of = bool(s["all_of"])
    except (IndexError, KeyError):
        all_of = False
    if not all_of:
        c.execute("UPDATE signers SET status='skipped' WHERE document_id=? AND step=? AND id<>? "
                  "AND status IN ('active','viewed','waiting')", (doc_id, step, s["id"]))
    doc = db.get_doc(c, doc_id)
    how = ("код подтверждён" if method == "code"
           else f"подписано в кабинете после входа через Bitrix24 (пользователь {s['b24_user_id'] or '—'})")
    db.add_event(c, doc_id, "step_signed", ip=ip, ua=ua,
                 detail=f"Шаг {step} · {s['role_title']} · ФИО: {signer_name.strip()}; "
                        f"{how}; хэш={doc['doc_hash']}")
    if all_of and c.execute("SELECT 1 FROM signers WHERE document_id=? AND step=? "
                            "AND status IN ('active','viewed','waiting')", (doc_id, step)).fetchone():
        return False, []      # шаг «все»: ждём остальных
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


def can_skip(c, doc) -> bool:
    """Пропустить можно текущий шаг, если он не последний (клиента пропускать нельзя)."""
    if not doc or not doc["workflow"] or doc["status"] != "in_progress" or not doc["current_step"]:
        return False
    nxt = c.execute("SELECT MIN(step) m FROM signers WHERE document_id=? AND step>? AND status='waiting'",
                    (doc["id"], doc["current_step"])).fetchone()["m"]
    return bool(nxt)


def skip_step(c, doc_id, reason, ip=None):
    """Пропуск текущего шага сотрудником в кабинете (с обязательной причиной).
    Кандидаты шага → 'passed', документ уходит на следующий шаг. → id для рассылки."""
    doc = db.get_doc(c, doc_id)
    if not can_skip(c, doc):
        return []
    step = doc["current_step"]
    title = _step_title(c, doc_id, step)
    c.execute("UPDATE signers SET status='passed' WHERE document_id=? AND step=? "
              "AND status IN ('waiting','active','viewed')", (doc_id, step))
    db.add_event(c, doc_id, "step_skipped", ip=ip,
                 detail=f"Шаг {step} · {title} пропущен в кабинете. Причина: {reason.strip()}")
    nxt = c.execute("SELECT MIN(step) m FROM signers WHERE document_id=? AND step>? AND status='waiting'",
                    (doc_id, step)).fetchone()["m"]
    return activate_step(c, doc_id, nxt, ip)


def cancel(c, doc_id, reason="", ip=None):
    c.execute("UPDATE signers SET status='cancelled' WHERE document_id=? "
              "AND status IN ('waiting','active','viewed')", (doc_id,))
    c.execute("UPDATE documents SET status='cancelled', current_step=NULL WHERE id=?", (doc_id,))
    db.add_event(c, doc_id, "cancelled", ip=ip, detail=reason or None)


# ------------------------------------------------------------------ сроки по ролям
_SLA_DEFAULT = {"manager": 4.0, "storekeeper": 8.0, "client": 48.0, "other": 24.0}


def sla_table() -> dict:
    """Сроки шага в часах по ролям. config.env: SIGN_SLA_HOURS=manager=4,storekeeper=8,client=48,other=24"""
    t = dict(_SLA_DEFAULT)
    for part in (getattr(config, "SIGN_SLA_HOURS", "") or "").split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            try:
                t[k.strip()] = float(v)
            except ValueError:
                pass
    return t


def sla_hours(role) -> float:
    t = sla_table()
    return t.get(role or "other", t["other"])


# ------------------------------------------------------------------ отклонение
def decline(c, doc, s, reason, name="", ip=None, ua=None):
    """Подписант отказался подписывать (с обязательной причиной). Документ → declined, цепочка остановлена."""
    reason = (reason or "").strip()[:1000]
    who = (name or "").strip() or (s["name"] if s is not None else doc["client_name"]) or ""
    now = db.now_iso()
    if s is not None:
        c.execute("UPDATE signers SET status='declined', decline_reason=?, signer_name=?, signer_ip=?, "
                  "signer_ua=?, signed_at=NULL WHERE id=?", (reason, who, ip, ua, s["id"]))
        c.execute("UPDATE signers SET status='cancelled' WHERE document_id=? AND id<>? "
                  "AND status IN ('waiting','active','viewed')", (doc["id"], s["id"]))
        detail = f"Шаг {s['step']} · {s['role_title']} · {who}: {reason}"
    else:
        detail = f"{who}: {reason}" if who else reason
    c.execute("UPDATE documents SET status='declined', decline_reason=?, current_step=NULL WHERE id=?",
              (reason, doc["id"]))
    db.add_event(c, doc["id"], "declined", ip=ip, ua=ua, detail=detail)
    return now


def notify_declined(doc_id, ip=None):
    """Сообщить менеджеру документа об отказе (если у менеджера есть телефон)."""
    with db.conn() as c:
        doc = db.get_doc(c, doc_id)
        mgr = c.execute("SELECT * FROM signers WHERE document_id=? AND role='manager' AND phone IS NOT NULL "
                        "ORDER BY step LIMIT 1", (doc_id,)).fetchone()
        dec = c.execute("SELECT * FROM signers WHERE document_id=? AND status='declined' LIMIT 1",
                        (doc_id,)).fetchone()
    if not mgr or (dec is not None and dec["id"] == mgr["id"]):
        return None
    who = (dec["signer_name"] or dec["name"] or dec["role_title"]) if dec is not None else (doc["client_name"] or "клиент")
    text = (f"Документ «{doc['title']}» не подписан: {who} отказался(ась).\n"
            f"Причина: {doc['decline_reason'] or '—'}\n\n"
            f"Карточка: {config.PUBLIC_BASE_URL}/cabinet/doc/{doc_id}\n\nПортал {config.BRAND}.")
    st, det = send_text_safe(mgr["phone"], text)
    with db.conn() as c:
        db.add_event(c, doc_id, "decline_sent", ip=ip, detail=f"менеджеру: {st}{(' — ' + det) if det else ''}")
    return st


# ------------------------------------------------------------------ автонапоминания
REMIND_MAX = int(getattr(config, "SIGN_REMIND_MAX", 3) or 3)


def _hours_since(*isos):
    from datetime import datetime, timezone
    best = None
    for x in isos:
        try:
            dt = datetime.fromisoformat(x) if x else None
        except Exception:
            dt = None
        if dt and (best is None or dt > best):
            best = dt
    if best is None:
        return None
    return (datetime.now(timezone.utc) - best).total_seconds() / 3600


def work_time(now=None) -> bool:
    """Напоминания — только пн–сб 9:00–19:00 по Алматы."""
    from datetime import datetime, timedelta, timezone
    now = now or datetime.now(timezone(timedelta(hours=config.TZ_OFFSET_HOURS)))
    return now.weekday() < 6 and 9 <= now.hour < 19


def due_reminders(c):
    """→ [('signer', id) | ('doc', id)] — кому пора напомнить: срок шага по роли прошёл
    с момента отправки ссылки или прошлого напоминания, напоминаний меньше REMIND_MAX."""
    out = []
    for s in c.execute("""SELECT s.* FROM signers s JOIN documents d ON d.id=s.document_id
                          WHERE d.status='in_progress' AND s.status IN ('active','viewed')
                            AND s.phone IS NOT NULL AND s.phone<>''
                            AND COALESCE(s.remind_count,0) < ?""", (REMIND_MAX,)).fetchall():
        h = _hours_since(s["activated_at"], s["reminded_at"])
        if h is not None and h >= sla_hours(s["role"]):
            out.append(("signer", s["id"]))
    for d in c.execute("""SELECT * FROM documents WHERE COALESCE(workflow,0)=0 AND status IN ('sent','viewed')
                            AND client_phone IS NOT NULL AND client_phone<>''
                            AND COALESCE(remind_count,0) < ?""", (REMIND_MAX,)).fetchall():
        h = _hours_since(d["sent_at"], d["reminded_at"])
        if h is not None and h >= sla_hours("client"):
            out.append(("doc", d["id"]))
    return out


def send_reminders(force=False, ip="scheduler"):
    """Разослать напоминания (вызывается задачей «ANESCOM sign remind» раз в час)."""
    if not force and not work_time():
        return {"sent": 0, "skipped": "нерабочее время"}
    with db.conn() as c:
        due = due_reminders(c)
    res = []
    for kind, oid in due:
        with db.conn() as c:
            if kind == "signer":
                s = signer(c, oid)
                doc = db.get_doc(c, s["document_id"])
                phone, text = s["phone"], "Напоминание. " + build_message(s, doc)
                doc_id, n = doc["id"], (s["remind_count"] or 0) + 1
                label = f"Шаг {s['step']} · {s['role_title']} · {s['name'] or '—'}"
            else:
                doc = db.get_doc(c, oid)
                from . import notify as _n
                link = f"{config.PUBLIC_BASE_URL}/s/{doc['sign_token']}"
                phone = doc["client_phone"]
                text = "Напоминание. " + _n.build_message(link, doc["sign_code"], doc["title"], doc["client_name"])
                doc_id, n = doc["id"], (doc["remind_count"] or 0) + 1
                label = f"клиент · {doc['client_name'] or '—'}"
        st, det = send_text_safe(phone, text)
        with db.conn() as c:
            tbl = "signers" if kind == "signer" else "documents"
            c.execute(f"UPDATE {tbl} SET remind_count=?, reminded_at=? WHERE id=?", (n, db.now_iso(), oid))
            db.add_event(c, doc_id, "reminded", ip=ip,
                         detail=f"{label}: напоминание {n} из {REMIND_MAX} — {st}{(' — ' + det) if det else ''}")
        res.append({"kind": kind, "id": oid, "status": st})
    return {"sent": sum(1 for r in res if r["status"] == "sent"), "total": len(res), "items": res}


# ------------------------------------------------------------------ массовая подпись в кабинете
def my_tasks(c, b24_id):
    """Шаги, где сотрудник (вошёл через Bitrix24) — текущий подписант."""
    if not b24_id:
        return []
    return c.execute("""SELECT s.*, d.title, d.client_name, d.external_id, d.meta, d.created_at doc_created
                          FROM signers s JOIN documents d ON d.id=s.document_id
                         WHERE d.status='in_progress' AND s.status IN ('active','viewed')
                           AND s.b24_user_id=? ORDER BY s.activated_at""", (str(b24_id),)).fetchall()


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
    # 18.10.2026: проще для клиента — код уже в ссылке, на странице: галочка и «Подписать»
    link = f"{config.PUBLIC_BASE_URL}/s/{s['token']}?k={s['code']}"
    hello = f"Здравствуйте, {s['name']}!" if s["name"] else "Здравствуйте!"
    if s["role"] == "client":
        who = f"{config.COMPANY} направляет вам документ на подпись"
    else:
        who = f"Документ ждёт вашей подписи ({s['role_title'].lower()})"
    return (f"{hello}\n\n{who}: «{doc['title']}».\n\n"
            f"Подписать за 1 минуту:\n{link}\n\n"
            f"1) Откройте ссылку и проверьте документ.\n"
            f"2) Поставьте галочку «ознакомлен(а)».\n"
            f"3) Нажмите «Подписать документ».\n\n"
            f"Если на странице попросят код — {s['code']}.\n"
            f"Не согласны — там же кнопка «Отказаться» с причиной.\n\n"
            f"{config.COMPANY} · портал {config.BRAND}")


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
