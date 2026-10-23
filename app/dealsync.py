"""Закрытие сделок Bitrix24 по закрытым заказам 1С (23.10.2026, проект 14 п. 3).

Почему: коннектор «Битрикс24: Коннектор к 1С для УТ» 4.4.0.3 меняет стадию сделки только при записи
самого заказа. Когда заказ в КА закрывается оплатой / реализацией / обработкой закрытия, заказ не
перезаписывается — сделка остаётся «На согласовании». Коннектор не правим (обновления сотрут) —
досылаем стадию сами.

1С (расширение «ANESCOM: Аналитика», ану_Аналитика.ЗакрытьСделкиБ24, каждые 15 минут) шлёт
POST /api/analytics/deals_close (Bearer EDO_API_TOKEN):
  {"source": "anescom", "orders": [{"guid": "<УникальныйИдентификатор заказа>", "no": "00НФ-8219",
                                     "reason": "status_closed" | "ready_to_close"}, ...]}
Сделку ищем по ORIGIN_ID = guid (так её создаёт коннектор). Открытую сделку переводим в «Завершена
успешно» своей воронки (WON или C<воронка>:WON). Уже закрытые запоминаем, чтобы не спрашивать
Bitrix каждый раз.

Режим DEAL_SYNC_MODE в config.env: test (по умолчанию) — ничего не меняет, только отвечает, что сделал
бы; live — меняет стадии. Поле "dry_run": true в теле (Диагностика, копия базы) — всегда как test. Ответ и журнал — GET /api/analytics/deals_close/last.
"""
import json
import logging
import os
import re
import threading
from datetime import datetime, timezone

from . import config
from .analytics import conn
from .b24people import _b24

log = logging.getLogger("edo.dealsync")

MODE = os.environ.get("DEAL_SYNC_MODE", "test").lower()
CHUNK = 50
GUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
COMMENT = "Закрыта автоматически: заказ {no} закрыт в 1С (ANESCOM, {reason})"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _init():
    with conn() as c:
        c.executescript("""
CREATE TABLE IF NOT EXISTS b24_deal_closed (
  guid TEXT PRIMARY KEY, deal_id TEXT, order_no TEXT, how TEXT, ts TEXT);
CREATE TABLE IF NOT EXISTS b24_deal_sync_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, mode TEXT, body TEXT);
""")


_init()


def won_stage(category_id) -> str:
    cat = str(category_id or "0")
    return "WON" if cat == "0" else f"C{cat}:WON"


_LOCK = threading.Lock()  # два прогона одновременно не запускаем — иначе одну сделку закроем дважды


def handle(body: dict) -> dict:
    if not _LOCK.acquire(blocking=False):
        return {"mode": MODE, "busy": True, "received": len(body.get("orders") or []),
                "note": "предыдущий прогон ещё идёт — заказы придут в следующий раз"}
    try:
        return _handle(body)
    finally:
        _LOCK.release()


def _handle(body: dict) -> dict:
    mode ="test" if body.get("dry_run") else MODE  # dry_run — из Диагностики / копии базы: ничего не меняем
    orders = body.get("orders") or []
    if not isinstance(orders, list):
        raise ValueError("orders должен быть списком")
    want = {}
    bad = 0
    for o in orders:
        g = str((o or {}).get("guid") or "").strip().lower()
        if not GUID_RE.match(g):
            bad += 1
            continue
        want[g] = {"no": str(o.get("no") or "").strip(), "reason": str(o.get("reason") or "").strip()}

    with conn() as c:
        known = {r[0] for r in c.execute("SELECT guid FROM b24_deal_closed")}
    todo = [g for g in want if g not in known]

    res = {"mode": mode, "received": len(orders), "bad_guid": bad, "already_known": len(want) - len(todo),
           "checked": 0, "not_found": [], "already_closed": 0, "closed": [], "would_close": [], "errors": []}
    remember = []
    for i in range(0, len(todo), CHUNK):
        part = todo[i:i + CHUNK]
        try:
            deals = _b24("crm.deal.list", {"filter": {"ORIGIN_ID": part},
                                           "select": ["ID", "TITLE", "ORIGIN_ID", "CATEGORY_ID", "STAGE_ID", "CLOSED"]}) or []
        except Exception as e:  # noqa: BLE001
            res["errors"].append(f"crm.deal.list: {e}")
            continue
        res["checked"] += len(part)
        by_guid = {}
        for d in deals:
            by_guid.setdefault(str(d.get("ORIGIN_ID") or "").lower(), []).append(d)
        for g in part:
            info = want[g]
            found = by_guid.get(g) or []
            if not found:
                res["not_found"].append(info["no"] or g)
                continue
            for d in found:
                item = {"deal": d["ID"], "order": info["no"], "stage": d.get("STAGE_ID"), "reason": info["reason"]}
                if d.get("CLOSED") == "Y":
                    res["already_closed"] += 1
                    remember.append((g, d["ID"], info["no"], "already"))
                    continue
                if mode != "live":
                    res["would_close"].append(item)
                    continue
                try:
                    _b24("crm.deal.update", {"id": d["ID"], "fields": {"STAGE_ID": won_stage(d.get("CATEGORY_ID"))}})
                    try:
                        _b24("crm.timeline.comment.add", {"fields": {
                            "ENTITY_ID": d["ID"], "ENTITY_TYPE": "deal",
                            "COMMENT": COMMENT.format(no=info["no"], reason=info["reason"] or "закрыт")}})
                    except Exception as e:  # noqa: BLE001 — комментарий не обязателен
                        log.warning("комментарий к сделке %s: %s", d["ID"], e)
                    res["closed"].append(item)
                    remember.append((g, d["ID"], info["no"], "closed"))
                    log.info("Сделка %s (%s) → WON", d["ID"], info["no"])
                except Exception as e:  # noqa: BLE001
                    res["errors"].append(f"сделка {d['ID']}: {e}")

    with conn() as c:
        c.executemany("INSERT OR REPLACE INTO b24_deal_closed(guid, deal_id, order_no, how, ts) VALUES(?,?,?,?,?)",
                      [(g, did, no, how, _now()) for g, did, no, how in remember])
        short = dict(res)
        short["not_found"] = res["not_found"][:50]
        c.execute("INSERT INTO b24_deal_sync_log(ts, mode, body) VALUES(?,?,?)",
                  (_now(), mode, json.dumps(short, ensure_ascii=False)))
        c.execute("DELETE FROM b24_deal_sync_log WHERE id <= (SELECT MAX(id) - 500 FROM b24_deal_sync_log)")
    res["not_found_count"] = len(res["not_found"])
    res["not_found"] = res["not_found"][:20]
    return res


def last(n: int = 5) -> list:
    with conn() as c:
        rows = c.execute("SELECT ts, mode, body FROM b24_deal_sync_log ORDER BY id DESC LIMIT ?",
                         (max(1, min(n, 50)),)).fetchall()
    return [{"ts": r["ts"], "mode": r["mode"], **json.loads(r["body"])} for r in rows]
