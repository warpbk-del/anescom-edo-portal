"""Аудит учёта 1С (проект 21, 24.10.2026).

1С (ану_Аналитика.ВыгрузитьАудит, только чтение) шлёт POST /api/analytics/audit (Bearer EDO_API_TOKEN):
  {"section": "osv" | "osv_acc" | "unposted" | "processor" | "negstock",
   "date_from": "2026-01-01", "date_to": "2026-10-24", "replace": true, "rows": [{...}, ...], "source": "anescom"}
Первая порция раздела (replace=true) заменяет раздел целиком; следующие дописывают.
Строки хранятся как JSON в analytics.sqlite3 (таблица an_audit) — состав полей у разделов разный.

Смотреть (только администратор, вход через Битрикс24):
  GET /audit                      — сводка: сколько строк по разделам, когда пришли, ошибки последнего запуска;
  GET /audit/data?section=osv     — строки раздела JSON (limit/offset);
  GET /audit/findings             — готовые находки: сальдо «не той стороны», счёт 0000, банковские счета на нескольких
                                    счетах учёта, непроведённые/будущие документы, переработка без отчёта, минусы на складах.
"""
import json
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from . import access, analytics

router = APIRouter()
SECTIONS = ("osv", "osv_acc", "unposted", "processor", "negstock")

# Активные (сальдо должно быть по дебету) и пассивные (по кредиту) группы плана счетов РК — по первой цифре/группе.
ACTIVE_PREFIXES = ("10", "11", "12", "13", "14", "15", "16", "17", "18", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29")
PASSIVE_PREFIXES = ("30", "31", "32", "33", "34", "35", "36", "40", "41", "42", "43", "44", "45", "50", "51", "52", "53", "54", "55", "56")
# контрпассивные/контрактивные и регулирующие счета — сальдо по «чужой» стороне нормально
CONTRA = ("1290", "1291", "1292", "2120", "2420", "2421", "2422", "2423", "2424", "2740", "2750", "5520", "5600", "5610", "5700", "5710")


def init():
    with analytics.conn() as c:
        c.executescript("""
CREATE TABLE IF NOT EXISTS an_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT, section TEXT NOT NULL, source TEXT NOT NULL,
    ts TEXT NOT NULL, date_from TEXT, date_to TEXT, row TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_an_audit_section ON an_audit(section, source);
""")


def ingest(body: dict, ip: str) -> dict:
    """Вызывается из analytics.ingest для kind=audit."""
    section = str(body.get("section") or "").strip()
    if section not in SECTIONS:
        raise HTTPException(400, f"Неизвестный раздел аудита: {section!r}")
    source = str(body.get("source") or "anescom").strip().lower()
    rows = body.get("rows") or []
    if not isinstance(rows, list):
        raise HTTPException(400, "rows должен быть списком")
    if len(rows) > analytics.MAX_ROWS:
        raise HTTPException(413, "Слишком много строк — порциями")
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    init()
    with analytics.conn() as c:
        if body.get("replace"):
            c.execute("DELETE FROM an_audit WHERE section=? AND source=?", (section, source))
        c.executemany(
            "INSERT INTO an_audit(section, source, ts, date_from, date_to, row) VALUES(?,?,?,?,?,?)",
            [(section, source, ts, body.get("date_from"), body.get("date_to"), json.dumps(r, ensure_ascii=False))
             for r in rows])
        c.execute("INSERT INTO an_loads(ts, kind, date_from, date_to, rows, replaced, ip, note) VALUES(?,?,?,?,?,?,?,?)",
                  (ts, f"audit:{section}" + ("" if source == "anescom" else f"@{source}"), body.get("date_from"),
                   body.get("date_to"), len(rows), int(bool(body.get("replace"))), ip, None))
    return {"ok": True, "section": section, "rows": len(rows)}


def _admin(request: Request):
    s = access.scope(request)
    if s.password or not s.real_admin:
        raise HTTPException(403, "Только для администратора (вход через Битрикс24)")
    return s


def _rows(section: str, source: str = "anescom") -> list:
    init()
    with analytics.conn() as c:
        return [json.loads(r["row"]) for r in
                c.execute("SELECT row FROM an_audit WHERE section=? AND source=? ORDER BY id", (section, source))]


def _summary(source: str = "anescom") -> dict:
    init()
    with analytics.conn() as c:
        res = {r["section"]: {"rows": r["n"], "ts": r["ts"], "date_from": r["d1"], "date_to": r["d2"]} for r in c.execute(
            "SELECT section, COUNT(*) n, MAX(ts) ts, MIN(date_from) d1, MAX(date_to) d2 FROM an_audit WHERE source=? "
            "GROUP BY section", (source,))}
        last = c.execute("SELECT ts, body FROM an_meta WHERE body LIKE '%audit_run%' ORDER BY id DESC LIMIT 1").fetchone()
    res["_last_run"] = {"ts": last["ts"], "body": json.loads(last["body"])} if last else None
    return res


def _net(r) -> float:
    return float(r.get("end_dt") or 0) - float(r.get("end_kt") or 0)


def findings(source: str = "anescom") -> dict:
    """Находки по данным аудита (без правок в 1С)."""
    out = {}
    acc = _rows("osv_acc", source)
    det = _rows("osv", source)

    # 1. сальдо «не той стороны» по счетам (свёрнуто по организации и подразделению)
    wrong = []
    by_acc = defaultdict(float)
    for r in acc:
        code = r.get("acc", "")
        by_acc[(r.get("org", ""), code)] += _net(r)
    for (org, code), net in sorted(by_acc.items()):
        if abs(net) < 0.5 or code.startswith(CONTRA) or code in CONTRA:
            continue
        if code.startswith(ACTIVE_PREFIXES) and net < 0:
            wrong.append({"org": org, "acc": code, "net": round(net, 2), "side": "Кт на активном"})
        elif code.startswith(PASSIVE_PREFIXES) and net > 0:
            wrong.append({"org": org, "acc": code, "net": round(net, 2), "side": "Дт на пассивном"})
    out["wrong_side"] = wrong

    # 2. вспомогательный счёт 0000 и прочие с сальдо
    out["acc_0000"] = [r for r in acc if str(r.get("acc", "")).startswith("00") and abs(_net(r)) >= 0.5]

    # 3. банковские счета: один и тот же банковский счёт (субконто) на нескольких счетах учёта денег
    banks = defaultdict(lambda: {"accs": defaultdict(float), "turn": 0.0})
    for r in det:
        code = str(r.get("acc", ""))
        if code[:3] in ("102", "103", "104", "105") and r.get("sub1"):
            b = banks[(r.get("org", ""), r["sub1"])]
            b["accs"][code] += _net(r)
            b["turn"] += float(r.get("dt") or 0)
    out["banks"] = [{"org": k[0], "bank_account": k[1], "by_acc": {a: round(v, 2) for a, v in d["accs"].items()},
                     "total": round(sum(d["accs"].values()), 2), "turnover_dt": round(d["turn"], 2),
                     "several_accounts": len(d["accs"]) > 1}
                    for k, d in sorted(banks.items(), key=lambda kv: -kv[1]["turn"])]

    # 4. расчёты: контрагенты с сальдо «не той стороны» и крупнейшие остатки (1210, 1710, 3310, 3510, 1250, 3350)
    cp = defaultdict(float)
    for r in det:
        code = str(r.get("acc", ""))
        if code[:3] in ("121", "171", "331", "351", "125", "335", "128", "338"):
            cp[(r.get("org", ""), code, r.get("sub1", ""))] += _net(r)
    wrong_cp, top = [], defaultdict(list)
    for (org, code, who), net in cp.items():
        if abs(net) < 0.5:
            continue
        active = code[:1] == "1"
        if (active and net < 0) or (not active and net > 0):
            wrong_cp.append({"org": org, "acc": code, "counterparty": who, "net": round(net, 2)})
        top[(org, code)].append({"counterparty": who, "net": round(net, 2)})
    out["counterparty_wrong_side"] = sorted(wrong_cp, key=lambda x: -abs(x["net"]))[:300]
    out["counterparty_top"] = {f"{o} | {a}": sorted(v, key=lambda x: -abs(x["net"]))[:25] for (o, a), v in top.items()}

    # 5. подразделения: счёт, у которого по одним подразделениям плюс, по другим минус (разнесено по разным)
    dep = defaultdict(lambda: defaultdict(float))
    for r in acc:
        dep[(r.get("org", ""), r.get("acc", ""))][r.get("dept", "")] += _net(r)
    split = []
    for (org, code), d in dep.items():
        pos = sum(v for v in d.values() if v > 0.5)
        neg = sum(v for v in d.values() if v < -0.5)
        if pos > 0 and neg < 0 and min(pos, -neg) > 100000:
            split.append({"org": org, "acc": code, "plus": round(pos, 2), "minus": round(neg, 2),
                          "depts": {k or "<не указано>": round(v, 2) for k, v in d.items() if abs(v) >= 0.5}})
    out["dept_split"] = sorted(split, key=lambda x: -min(x["plus"], -x["minus"]))

    # 6. документы, переработка, склады — как пришли
    docs = _rows("unposted", source)
    out["unposted"] = sorted([d for d in docs if d.get("unposted")], key=lambda d: -d["unposted"])
    out["deleted"] = sorted([d for d in docs if d.get("deleted")], key=lambda d: -d["deleted"])
    out["future"] = sorted([d for d in docs if d.get("future")], key=lambda d: -d["future"])
    out["processor"] = _rows("processor", source)
    neg = _rows("negstock", source)
    out["negstock_count"] = len(neg)
    out["negstock"] = sorted(neg, key=lambda r: r.get("qty", 0))[:300]
    return out


@router.get("/audit/data")
def audit_data(request: Request, section: str, source: str = "anescom", limit: int = 5000, offset: int = 0):
    _admin(request)
    if section not in SECTIONS:
        raise HTTPException(404, "Нет такого раздела")
    rows = _rows(section, source)
    return JSONResponse({"section": section, "total": len(rows), "rows": rows[offset:offset + max(1, min(limit, 50000))]})


@router.get("/audit/findings")
def audit_findings(request: Request, source: str = "anescom"):
    _admin(request)
    return JSONResponse({"summary": _summary(source), "findings": findings(source)})


@router.get("/audit", response_class=HTMLResponse)
def audit_page(request: Request, source: str = "anescom"):
    _admin(request)
    s = _summary(source)
    rows = "".join(f"<tr><td>{k}</td><td>{v['rows']}</td><td>{v['ts']}</td><td>{v['date_from']} — {v['date_to']}</td></tr>"
                   for k, v in s.items() if not k.startswith("_"))
    last = s.get("_last_run")
    err = ""
    if last:
        b = last["body"]
        err = f"<p>Последний запуск: {last['ts']}; строки: {json.dumps(b.get('counts'), ensure_ascii=False)}</p>"
        if b.get("errors"):
            err += "<pre>" + "\n".join(map(str, b["errors"]))[:20000] + "</pre>"
    return HTMLResponse(f"""<!doctype html><meta charset="utf-8"><title>Аудит 1С</title>
<style>body{{font:14px system-ui;margin:24px}}td,th{{border:1px solid #ccc;padding:4px 8px}}table{{border-collapse:collapse}}</style>
<h1>Аудит 1С — данные выгрузки</h1>
<table><tr><th>Раздел</th><th>Строк</th><th>Получено</th><th>Период</th></tr>{rows}</table>{err}
<p><a href="/audit/findings?source={source}">Находки (JSON)</a></p>""")
