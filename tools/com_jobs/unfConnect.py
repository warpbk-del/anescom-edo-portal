# Подключение к УНФ (только чтение). Путь и пользователь/пароль вводит пользователь.
import os as _os
cands = [p for p in (r"D:\Base\1C\UNF", r"D:\Base\1C\УНФ", r"D:\Base\1C\ANESCOM-UNF") if _os.path.exists(p)]
print("найдено:", cands, "| все базы:", [d for d in _os.listdir(r"D:\Base\1C")])
UNFPATH = input("Папка базы УНФ (Enter = первый найденный): ").strip() or (cands[0] if cands else "")
u = input("Пользователь УНФ: ").strip()
pw = ask_pwd("Пароль УНФ (звёздочки), Enter: ")
conn_unf = win32com.client.Dispatch("V83.COMConnector")
ib_unf = conn_unf.Connect(f'File="{UNFPATH}";Usr="{u}";Pwd="{pw}";')
pw = None
print("УНФ ПОДКЛЮЧЕНА:", ib_unf.Метаданные.Имя, ib_unf.Метаданные.Версия)
