# -*- coding: utf-8 -*-
"""Проверка портала: что прислала КОПИЯ 1С ночью 25.10.2026 при перепроведении (аудит 21-14/21-15).
Запуск на сервере:  python D:\\anescom_edo\\tools\\night_check.py [--cancel]
Без --cancel — только список. С --cancel — З-2, созданные с 01:40 25.10 (Алматы), отменяются с причиной.
"""
import sqlite3, sys, json
DB = r"D:\anescom_edo\data\edo.sqlite3"
SINCE = "2026-10-24T20:40"   # UTC = 25.10 01:40 Алматы
c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
docs = c.execute("SELECT id, title, status, created_at, meta FROM documents WHERE created_at >= ? ORDER BY created_at", (SINCE,)).fetchall()
z2 = [d for d in docs if '"kind": "z2"' in (d["meta"] or "")]
print("документов с", SINCE, "UTC:", len(docs), "из них З-2:", len(z2))
for d in z2[:200]:
    print(" ", d["created_at"][:19], d["status"], d["title"][:70])
sent = c.execute("SELECT COUNT(*) FROM events WHERE ts >= ? AND kind IN ('sent','notified','wa_sent')", (SINCE,)).fetchone()[0]
print("событий отправки с", SINCE, ":", sent)
for r in c.execute("SELECT kind, COUNT(*) n FROM events WHERE ts >= ? GROUP BY kind", (SINCE,)):
    print("  событие", r["kind"], r["n"])
try:
    for r in c.execute("SELECT doc_title, status, phone, created_at, detail FROM pay_notifications WHERE created_at >= ?", (SINCE,)):
        print(" оплата:", dict(r))
except Exception as e:
    print("pay_notifications:", e)
if "--cancel" in sys.argv:
    n = 0
    for d in z2:
        if d["status"] in ("in_progress", "created"):
            c.execute("UPDATE signers SET status='cancelled' WHERE document_id=? AND status IN ('waiting','active','viewed')", (d["id"],))
            c.execute("UPDATE documents SET status='cancelled', current_step=NULL WHERE id=?", (d["id"],))
            c.execute("INSERT INTO events(document_id, ts, kind, detail) VALUES(?, datetime('now'), 'cancelled', ?)",
                      (d["id"], "создан копией 1С при ночном аудите 25.10.2026 (перепроведение) — не рабочий документ"))
            n += 1
    c.commit(); print("отменено З-2:", n)
