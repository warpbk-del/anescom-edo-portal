"""Реестр v3: разделы (виды документов), подразделения, «Мои задачи» (18.10.2026).

Вид и подразделение вычисляются из meta/названия — без изменения схемы БД.
1С в будущем может прислать meta.category / meta.department явно.
"""
from datetime import datetime, timedelta, timezone
import json
import re

from . import config, db, workflow

CATEGORIES = [
    ("nakl", "Накладные З-2"),
    ("dogovor", "Договоры"),
    ("kadr", "Кадровые"),
    ("akt", "Акты сверки"),
    ("other", "Прочие"),
]
CAT_TITLES = dict(CATEGORIES)
CITIES = ["Актобе", "Уральск", "Атырау", "Актау", "Астана", "Костанай", "Алматы"]
SLA_HOURS = float(getattr(config, "TASK_SLA_HOURS", 4) or 4)
STATUS_TITLES = {
    "created": "Черновик", "sent": "Отправлен", "viewed": "Просмотрен", "signed": "Подписан",
    "expired": "Истёк", "declined": "Отклонён", "in_progress": "На подписании", "cancelled": "Отменён",
}


def _meta(row) -> dict:
    try:
        return json.loads(row["meta"] or "{}")
    except Exception:
        return {}


def category(row) -> str:
    m = _meta(row)
    if m.get("category") in CAT_TITLES:
        return m["category"]
    if m.get("kind") == "z2":
        return "nakl"
    if m.get("kind") == "kadr":
        return "kadr"
    t = (row["title"] or "").lower()
    if "накладн" in t:
        return "nakl"
    if "акт сверки" in t or "сверк" in t:
        return "akt"
    if re.search(r"приказ|трудов|кадров|отпуск|увольн|гпх", t):
        return "kadr"
    if "договор" in t or "соглашен" in t or "оферт" in t:
        return "dogovor"
    return "other"


def department(row) -> str:
    m = _meta(row)
    if m.get("department"):
        return str(m["department"])
    src = " ".join(str(m.get(k) or "") for k in ("warehouse", "branch", "city")) + " " + (row["title"] or "")
    low = src.lower()
    for c in CITIES:
        if c.lower() in low:
            return c
    return ""


def _parse(iso):
    try:
        return datetime.fromisoformat(iso)
    except Exception:
        return None


def _ago(iso) -> str:
    dt = _parse(iso)
    if not dt:
        return ""
    sec = (datetime.now(timezone.utc) - dt).total_seconds()
    if sec < 3600:
        return f"{max(1, int(sec // 60))} мин"
    if sec < 86400:
        return f"{int(sec // 3600)} ч"
    return f"{int(sec // 86400)} дн"


def local_time(iso) -> str:
    dt = _parse(iso)
    if not dt:
        return ""
    dt = dt.astimezone(timezone(timedelta(hours=config.TZ_OFFSET_HOURS)))
    today = datetime.now(dt.tzinfo).date()
    return dt.strftime("%H:%M") if dt.date() == today else dt.strftime("%d.%m %H:%M")


def route(c, row):
    """Мини-маршрут: [{step, title, state: done|now|wait|off}], активные подписанты, просрочка."""
    if not row["workflow"]:
        st = row["status"]
        state = ("done" if st == "signed" else ("now" if st in ("sent", "viewed")
                 else ("declined" if st == "declined" else "wait")))
        sla = workflow.sla_hours("client")
        since = row["sent_at"]
        dt = _parse(since) if since else None
        overdue = bool(st in ("sent", "viewed") and dt and datetime.now(timezone.utc) - dt > timedelta(hours=sla))
        return {"steps": [{"step": 1, "title": "Клиент", "state": state}], "active": [],
                "who": "клиент" if st in ("sent", "viewed") else "", "role": "client" if st in ("sent", "viewed") else "",
                "overdue": overdue, "since": since, "step_text": "", "sla": sla}
    rows = workflow.signers(c, row["id"])
    steps = {}
    for s in rows:
        d = steps.setdefault(s["step"], {"step": s["step"], "title": s["role_title"] or s["role"], "states": [],
                                         "role": s["role"]})
        d["states"].append(s["status"])
    out = []
    for n in sorted(steps):
        sts = steps[n]["states"]
        if "signed" in sts:
            state = "done"
        elif "declined" in sts:
            state = "declined"
        elif any(x in ("active", "viewed") for x in sts):
            state = "now"
        elif "passed" in sts and all(x in ("passed", "cancelled") for x in sts):
            state = "skip"
        elif all(x == "cancelled" for x in sts):
            state = "off"
        else:
            state = "wait"
        out.append({"step": n, "title": steps[n]["title"], "state": state, "role": steps[n]["role"]})
    active = [s for s in rows if s["status"] in ("active", "viewed")]
    since = min((s["activated_at"] for s in active if s["activated_at"]), default=None)
    overdue = False
    sla = workflow.sla_hours(active[0]["role"]) if active else SLA_HOURS
    if since and row["status"] == "in_progress":
        dt = _parse(since)
        overdue = bool(dt and datetime.now(timezone.utc) - dt > timedelta(hours=sla))
    who = ", ".join(workflow.last_name(s["name"]) or (s["role_title"] or "") for s in active[:2])
    if len(active) > 2:
        who += f" +{len(active) - 2}"
    cur = row["current_step"] or (active[0]["step"] if active else None)
    return {"steps": out, "active": active, "who": who,
            "role": active[0]["role"] if active else "",
            "overdue": overdue, "since": since, "sla": sla,
            "step_text": f"шаг {cur} из {len(out)}" if cur else ""}


def decorate(c, rows):
    res = []
    for r in rows:
        d = dict(r)
        d["cat"] = category(r)
        d["cat_title"] = CAT_TITLES[d["cat"]]
        d["dept"] = department(r)
        d["route"] = route(c, r)
        d["status_title"] = STATUS_TITLES.get(r["status"], r["status"])
        d["wait_for"] = _ago(d["route"]["since"]) if d["route"]["since"] else ""
        res.append(d)
    return res


def dashboard(c, rows_all, dept=""):
    """Показатели «Мои задачи» по уже отфильтрованному подразделению."""
    docs = [d for d in rows_all if not dept or d["dept"] == dept]
    now = datetime.now(timezone.utc)
    staff_wait = [d for d in docs if d["status"] == "in_progress" and d["route"]["role"] not in ("client", "")]
    client_wait = [d for d in docs if (d["status"] == "in_progress" and d["route"]["role"] == "client")
                   or d["status"] in ("sent", "viewed")]
    week = [d for d in docs if d["status"] == "signed" and d["signed_at"]
            and (_parse(d["signed_at"]) or now) > now - timedelta(days=7)]
    problems = [d for d in docs if d["status"] in ("declined", "expired")]
    overdue = [d for d in staff_wait + client_wait if d["route"]["overdue"]]
    stuck = {}
    for d in staff_wait + client_wait:
        if d["route"]["role"] == "client" or d["status"] in ("sent", "viewed"):
            key = "Клиенты"
        else:
            key = (d["route"]["active"][0]["role_title"] if d["route"]["active"] else "Сотрудники")
            if d["dept"]:
                key += f" · {d['dept']}"
        s = stuck.setdefault(key, {"name": key, "n": 0, "late": 0})
        s["n"] += 1
        s["late"] += 1 if d["route"]["overdue"] else 0
    tasks = sorted(staff_wait + client_wait,
                   key=lambda d: (not d["route"]["overdue"], d["route"]["since"] or d["created_at"]))
    return {
        "tasks": tasks,
        "kpi": {"staff": len(staff_wait), "client": len(client_wait), "week": len(week),
                "problems": len(problems), "overdue": len(overdue)},
        "stuck": sorted(stuck.values(), key=lambda s: -s["n"]),
    }


EVENT_TITLES = {
    "created": "создан", "sent": "отправлен", "viewed": "открыт", "signed": "подписан",
    "step_started": "передан на шаг", "step_sent": "ссылка отправлена", "step_viewed": "открыт подписантом",
    "step_signed": "подписан на шаге", "completed": "подписан всеми", "done_sent": "итог отправлен менеджеру",
    "cancelled": "отменён", "sign_rejected": "отклонён", "code_failed": "неверный код",
    "signer_phone": "указан телефон", "problem": "требует внимания", "step_skipped": "шаг пропущен", "signer_removed": "подписант удалён",
    "declined": "отказ от подписания", "decline_sent": "об отказе сообщено менеджеру",
    "reminded": "напоминание отправлено",
}


def recent_events(c, limit=8, dept=""):
    rows = c.execute(
        """SELECT e.ts, e.kind, e.detail, d.title, d.id doc_id, d.meta, d.client_name
             FROM events e JOIN documents d ON d.id=e.document_id
            ORDER BY e.id DESC LIMIT ?""", (limit * 4,)).fetchall()
    out = []
    for r in rows:
        if dept and department(r) != dept:
            continue
        kind = r["kind"]
        tone = "ok" if kind in ("signed", "completed", "step_signed") else ("warn" if kind in ("cancelled", "sign_rejected", "code_failed", "problem", "declined") else "info")
        detail = (r["detail"] or "").split(";")[0][:90]
        out.append({"time": local_time(r["ts"]), "title": r["title"], "doc_id": r["doc_id"],
                    "what": EVENT_TITLES.get(kind, kind), "detail": detail, "tone": tone})
        if len(out) >= limit:
            break
    return out


_MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
           "сентября", "октября", "ноября", "декабря"]
_DAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]


def today_title() -> str:
    d = datetime.now(timezone(timedelta(hours=config.TZ_OFFSET_HOURS)))
    return f"{_DAYS[d.weekday()]}, {d.day} {_MONTHS[d.month - 1]}"
