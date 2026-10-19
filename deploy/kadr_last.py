"""6п: последние кадровые документы на портале (без телефонов). Запуск из D:\\anescom_edo: .venv\\Scripts\\python.exe kadr_last.py"""
import json, sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8")
c = sqlite3.connect(r"D:\anescom_edo\data\edo.sqlite3"); c.row_factory = sqlite3.Row
for d in c.execute("SELECT id, title, status, created_at, meta FROM documents WHERE meta LIKE '%\"kind\": \"kadr\"%' ORDER BY created_at DESC LIMIT 5"):
    m = json.loads(d["meta"] or "{}")
    print(d["created_at"][:19], d["status"], d["title"], "| проблемы:", m.get("problems"))
    for s in c.execute("SELECT step, role_title, name, status, phone IS NOT NULL AND phone<>'' ph FROM signers WHERE document_id=? ORDER BY step", (d["id"],)):
        print("   шаг", s["step"], s["role_title"], s["name"], s["status"], "тел" if s["ph"] else "нет тел")
    if "-v" in sys.argv:
        for e in c.execute("SELECT kind, detail FROM events WHERE document_id=? ORDER BY rowid", (d["id"],)):
            print("   событие", e["kind"], (e["detail"] or "")[:150])

# отмена тестовых: python kadr_last.py --cancel "<часть названия>"
if "--cancel" in sys.argv:
    sys.path.insert(0, ".")
    from app import db, workflow
    part = sys.argv[sys.argv.index("--cancel") + 1]
    with db.conn() as cc:
        for d in cc.execute("SELECT id, title FROM documents WHERE meta LIKE '%\"kind\": \"kadr\"%' AND status<>'cancelled' "
                            "AND title LIKE ?", (f"%{part}%",)).fetchall():
            workflow.cancel(cc, d["id"], "тест 6п в копии базы", "kadr_last")
            print("отменён:", d["title"])
