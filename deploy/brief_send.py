# Отправка утренней сводки в Bitrix24 (запускает задача планировщика «ANESCOM brief», пн–сб 8:30).
import sys
sys.path.insert(0, r"D:\anescom_edo")
sys.stdout.reconfigure(encoding="utf-8")
from app import briefing
if "--print" in sys.argv:
    print(briefing.text(briefing.build()))
else:
    print(briefing.send())
