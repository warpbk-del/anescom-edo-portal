# Автонапоминания подписантам (задача «ANESCOM sign remind», каждый час; рассылка только пн–сб 9–19 по Алматы).
# --print — показать, кому пора напомнить, без отправки; --force — отправить и в нерабочее время.
import sys
sys.path.insert(0, r"D:\anescom_edo")
sys.stdout.reconfigure(encoding="utf-8")
from app import db, workflow
with db.conn() as c:
    workflow.init(c)
    due = workflow.due_reminders(c)
if "--print" in sys.argv:
    print("пора напомнить:", due, "| рабочее время:", workflow.work_time())
else:
    print(workflow.send_reminders(force="--force" in sys.argv))
