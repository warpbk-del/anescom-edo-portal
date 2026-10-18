"""Портал v4, этап A: приём аналитики из 1С (расширение «ANESCOM: Аналитика», общий модуль ану_Аналитика).

1С раз в 15–30 мин шлёт POST /api/analytics/<вид> (Bearer EDO_API_TOKEN), JSON:
  {"date_from": "2026-10-15", "date_to": "2026-10-18",   # для видов за период
   "replace": true,                                      # для снимков: первая порция заменяет всё
   "rows": [{...}, ...]}

Виды за период (строки с датой; присланный период полностью заменяется — повтор безопасен):
  sales     — продажи: date, doc_key, doc_no, org, branch, warehouse, manager, client, client_key,
              item, item_key, item_group, qty, sum (с НДС), cost (себестоимость)
  payments  — поступления от клиентов: date, doc_key, doc_no, org, branch, manager, client, client_key,
              kind (cash | card | bank), sum
  cashflow  — движение денег (ДДС): date, doc_key, doc_no, org, branch, article, counterparty,
              direction (in | out), sum
Снимки (на момент выгрузки):
  stock     — остатки: org, branch, warehouse, item, item_key, item_group, unit, qty, cost_sum,
              last_sale (дата последней продажи или ""), sold_30, sold_90 (кол-во за 30/90 дней)
  debts     — взаиморасчёты с клиентами: org, branch, manager, client, client_key, debt, prepay,
              overdue, overdue_days
  prod_orders — заказы переработчику за год: order_key, order_no, order_date, partner, org, status, item,
              item_key, item_group, color, qty, qty_in (поступило), due_date
  prod_raw  — сырьё у переработчика: item, item_key, item_group, color, qty
Производство за период:
  prod_in   — поступления от переработчика: date, doc_key, doc_no, org, partner, order_no, warehouse,
              item, item_key, item_group, color, qty
  prod_out  — собственное производство («Производство без заказа», база АВТОКОМП): date, doc_key, doc_no,
              org, dept (участок — алюминий / ПВХ / покраска), warehouse, item, item_key, item_group, color, qty, unit,
              weight, weight_unit, area, area_unit (вес и площадь выпуска из карточки номенклатуры)
Источник (поле "source" в теле): anescom (по умолчанию) или avtokomp — данные второй базы лежат в своих
таблицах an_*_avtokomp, поэтому замена снимков одной базы не трогает другую (решение 18.10.2026).
Служебные:
  meta      — описание метаданных 1С (диагностика при первом запуске), хранится как есть.

Данные лежат в отдельной базе DATA_DIR/analytics.sqlite3 (не смешиваются с документами ЭДО).
"""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from . import config

router = APIRouter()
DB_PATH = config.DATA_DIR / "analytics.sqlite3"

# вид → (таблица, колонки, числовые колонки, есть ли дата)
KINDS = {
    "sales": ("an_sales",
              ["date", "doc_key", "doc_no", "org", "branch", "warehouse", "manager", "client",
               "client_key", "item", "item_key", "item_group", "qty", "sum", "cost"],
              {"qty", "sum", "cost"}, True),
    "payments": ("an_payments",
                 ["date", "doc_key", "doc_no", "org", "branch", "manager", "client", "client_key",
                  "kind", "sum"],
                 {"sum"}, True),
    "cashflow": ("an_cashflow",
                 ["date", "doc_key", "doc_no", "org", "branch", "article", "counterparty",
                  "direction", "sum"],
                 {"sum"}, True),
    "stock": ("an_stock",
              ["org", "branch", "warehouse", "item", "item_key", "item_group", "unit", "qty",
               "cost_sum", "last_sale", "sold_30", "sold_90"],
              {"qty", "cost_sum", "sold_30", "sold_90"}, False),
    "debts": ("an_debts",
              ["org", "branch", "manager", "client", "client_key", "debt", "prepay", "overdue",
               "overdue_days"],
              {"debt", "prepay", "overdue", "overdue_days"}, False),
    # долги/переплаты на 31.12 закрытых лет (6м, 19.10.2026): date = «ГГГГ-12-31», год заменяется целиком;
    # годы до 2025 — из старой БП (legacy/build.py), с 2025 — расширение 1С
    "debts_hist": ("an_debts_hist",
                   ["date", "year", "org", "branch", "manager", "client", "client_key", "debt", "prepay", "overdue",
                    "overdue_days"],
                   {"debt", "prepay", "overdue", "overdue_days"}, True),
    # Производство АВТОКОМП (ламинирование): поступления от переработчика, заказы, сырьё у переработчика
    "prod_in": ("an_prod_in",
                ["date", "doc_key", "doc_no", "org", "partner", "order_no", "warehouse", "item", "item_key",
                 "item_group", "color", "qty"],
                {"qty"}, True),
    "prod_orders": ("an_prod_orders",
                    ["order_key", "order_no", "order_date", "partner", "org", "status", "item", "item_key",
                     "item_group", "color", "qty", "qty_in", "due_date"],
                    {"qty", "qty_in"}, False),
    "prod_raw": ("an_prod_raw",
                 ["item", "item_key", "item_group", "color", "qty"],
                 {"qty"}, False),
    # собственное производство (документ «Производство без заказа», база АВТОКОМП)
    "prod_out": ("an_prod_out",
                 ["date", "doc_key", "doc_no", "org", "dept", "warehouse", "item", "item_key", "item_group",
                  "color", "qty", "unit", "weight", "weight_unit", "area", "area_unit"],
                 {"qty", "weight", "area"}, True),
}

# источник (база 1С) → суффикс таблиц; anescom — основная база (старые таблицы без суффикса)
SOURCES = {"anescom": "", "avtokomp": "_avtokomp"}


def table_for(kind: str, source: str = "anescom") -> str:
    return KINDS[kind][0] + SOURCES[source]

PAY_KINDS = {"cash", "card", "bank"}
MAX_ROWS = 50000  # в одном запросе; больше — порциями


def _schema() -> str:
    parts = []
    for base, cols, nums, dated in KINDS.values():
        defs = ", ".join(f"{c} {'REAL' if c in nums else 'TEXT'}" for c in cols)
        for suf in SOURCES.values():
            table = base + suf
            parts.append(f"CREATE TABLE IF NOT EXISTS {table} (id INTEGER PRIMARY KEY AUTOINCREMENT, {defs});")
            if dated:
                parts.append(f"CREATE INDEX IF NOT EXISTS idx_{table}_date ON {table}(date);")
    parts.append("""
CREATE TABLE IF NOT EXISTS an_loads (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, kind TEXT NOT NULL,
    date_from TEXT, date_to TEXT, rows INTEGER, replaced INTEGER, ip TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS an_meta (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, body TEXT NOT NULL);
""")
    return "\n".join(parts)


@contextmanager
def conn():
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init():
    with conn() as c:
        c.executescript(_schema())
        # новые колонки в уже созданных таблицах (prod_out: вес и площадь — 18.10.2026)
        for base, cols, nums, dated in KINDS.values():
            for suf in SOURCES.values():
                have = {r[1] for r in c.execute(f"PRAGMA table_info({base + suf})")}
                for col in cols:
                    if col not in have:
                        c.execute(f"ALTER TABLE {base + suf} ADD COLUMN {col} {'REAL' if col in nums else 'TEXT'}")


init()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def require_api(authorization: Optional[str] = Header(None)):
    if authorization != f"Bearer {config.API_TOKEN}":
        raise HTTPException(401, "Неверный токен")


def _date(v) -> str:
    """'2026-10-18', '2026-10-18T13:45:00', '18.10.2026 13:45:00' → '2026-10-18'."""
    s = str(v or "").strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    if len(s) >= 10 and s[2] == "." and s[5] == ".":
        return f"{s[6:10]}-{s[3:5]}-{s[0:2]}"
    raise ValueError(f"дата не распознана: {s!r}")


def _num(v) -> float:
    if v is None or v == "":
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    return float(str(v).replace(" ", "").replace(" ", "").replace(",", "."))


def _row(kind, cols, nums, dated, r: dict) -> list:
    out = []
    for c in cols:
        v = r.get(c)
        if c in nums:
            out.append(_num(v))
        elif c == "date":
            out.append(_date(v))
        elif c in ("last_sale", "order_date", "due_date"):
            out.append(_date(v) if v else "")
        else:
            out.append("" if v is None else str(v).strip())
    if kind == "payments" and out[cols.index("kind")] not in PAY_KINDS:
        raise ValueError(f"kind должен быть cash/card/bank, пришло {out[cols.index('kind')]!r}")
    if kind == "cashflow" and out[cols.index("direction")] not in ("in", "out"):
        raise ValueError("direction должен быть in/out")
    return out


@router.post("/api/analytics/{kind}")
async def ingest(kind: str, request: Request, _=Depends(require_api)):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Ожидается JSON")
    ip = request.client.host if request.client else ""

    if kind == "meta":
        with conn() as c:
            c.execute("INSERT INTO an_meta(ts, body) VALUES(?,?)", (_now(), json.dumps(body, ensure_ascii=False)))
            c.execute("DELETE FROM an_meta WHERE id <= (SELECT MAX(id) - 500 FROM an_meta)")
            c.execute("INSERT INTO an_loads(ts, kind, rows, replaced, ip) VALUES(?,?,?,?,?)",
                      (_now(), "meta", 1, 0, ip))
        return {"ok": True}

    if kind not in KINDS:
        raise HTTPException(404, f"Неизвестный вид: {kind}")
    source = str(body.get("source") or "anescom").strip().lower()
    if source not in SOURCES:
        raise HTTPException(400, f"Неизвестный источник: {source}")
    _t, cols, nums, dated = KINDS[kind]
    table = table_for(kind, source)
    load_kind = kind if source == "anescom" else f"{kind}@{source}"
    rows = body.get("rows") or []
    if not isinstance(rows, list):
        raise HTTPException(400, "rows должен быть списком")
    if len(rows) > MAX_ROWS:
        raise HTTPException(413, f"Больше {MAX_ROWS} строк — присылайте порциями")

    try:
        data = [_row(kind, cols, nums, dated, r) for r in rows]
        d_from = _date(body["date_from"]) if dated else None
        d_to = _date(body["date_to"]) if dated else None
    except KeyError as e:
        raise HTTPException(400, f"Нет поля {e}")
    except (ValueError, TypeError) as e:
        raise HTTPException(400, f"Ошибка в данных: {e}")

    if dated:
        if d_from > d_to:
            raise HTTPException(400, "date_from позже date_to")
        out = [r for r in data if not (d_from <= r[0] <= d_to)]
        if out:
            raise HTTPException(400, f"{len(out)} строк вне периода {d_from}…{d_to}")
    # Для периода: по умолчанию заменяем весь период (append=true — порции одного периода после первой).
    # Для снимка: replace=true — первая порция заменяет всё.
    replace = (not body.get("append")) if dated else bool(body.get("replace"))
    org = (body.get("org") or "").strip()  # если задана — заменяем только строки этой организации

    with conn() as c:
        if replace:
            where, args = [], []
            if dated:
                where.append("date BETWEEN ? AND ?")
                args += [d_from, d_to]
            if org:
                where.append("org = ?")
                args.append(org)
            c.execute(f"DELETE FROM {table}" + (" WHERE " + " AND ".join(where) if where else ""), args)
        ph = ",".join("?" * len(cols))
        c.executemany(f"INSERT INTO {table}({','.join(cols)}) VALUES({ph})", data)
        c.execute("INSERT INTO an_loads(ts, kind, date_from, date_to, rows, replaced, ip, note) VALUES(?,?,?,?,?,?,?,?)",
                  (_now(), load_kind, d_from, d_to, len(data), int(replace), ip, org or None))
    return {"ok": True, "kind": kind, "source": source, "rows": len(data), "replaced": replace}


@router.get("/api/analytics/status")
def status(_=Depends(require_api)):
    """Проверка выгрузки: сколько строк, период, последняя загрузка по каждому виду."""
    res = {}
    with conn() as c:
        for kind, (table, cols, nums, dated) in KINDS.items():
            q = f"SELECT COUNT(*) n" + (", MIN(date) d1, MAX(date) d2" if dated else "") + f" FROM {table}"
            r = dict(c.execute(q).fetchone())
            last = c.execute("SELECT ts, rows, date_from, date_to FROM an_loads WHERE kind=? ORDER BY id DESC LIMIT 1",
                             (kind,)).fetchone()
            r["last_load"] = dict(last) if last else None
            res[kind] = r
        m = c.execute("SELECT ts FROM an_meta ORDER BY id DESC LIMIT 1").fetchone()
        res["meta"] = {"last": m["ts"] if m else None}
    return res


@router.get("/api/analytics/meta")
def meta(last: int = 5, _=Depends(require_api)):
    """Последние сообщения 1С: итоги запусков (kind=run: строки, ошибки) и диагностика (kind=diagnostics)."""
    with conn() as c:
        rows = c.execute("SELECT ts, body FROM an_meta ORDER BY id DESC LIMIT ?", (max(1, min(last, 50)),)).fetchall()
        diag = c.execute("SELECT ts, body FROM an_meta WHERE body LIKE '%\"diagnostics\"%' ORDER BY id DESC LIMIT 1").fetchone()
    return {"last": [{"ts": r["ts"], "body": json.loads(r["body"])} for r in rows],
            "diagnostics": {"ts": diag["ts"], "body": json.loads(diag["body"])} if diag else None}
