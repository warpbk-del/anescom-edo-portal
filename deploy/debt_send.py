# Еженедельный отчёт по дебиторке в чат Bitrix24 «ANESCOM // DEBT» (задача «ANESCOM debt», пятница 19:00).
# --print — только текст и размер файла, без отправки; --file — сохранить Excel в D:\anescom_edo\data\debitorka.xlsx
import sys
sys.path.insert(0, r"D:\anescom_edo")
sys.stdout.reconfigure(encoding="utf-8")
from app import debtweek
if "--print" in sys.argv:
    r = debtweek.send(dry=True)
    print(r.pop("text")); print(r)
elif "--file" in sys.argv:
    p = r"D:\anescom_edo\data\debitorka.xlsx"
    open(p, "wb").write(debtweek.xlsx(debtweek.build())); print("сохранено", p)
elif "--chats" in sys.argv:
    print(debtweek.find_chat())
else:
    print(debtweek.send())
