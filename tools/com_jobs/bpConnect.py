# Подключение к старой БП (D:\Base\1C\BUH) только для чтения. Пользователь и пароль вводит пользователь в этом окне.
u = input("Пользователь старой БП (BUH): ").strip()
pw = ask_pwd("Пароль БП (символы — звёздочки), Enter: ")
conn_bp = win32com.client.Dispatch("V83.COMConnector")
ib_bp = conn_bp.Connect(f'File="D:\\Base\\1C\\BUH";Usr="{u}";Pwd="{pw}";')
pw = None
print("БП ПОДКЛЮЧЕНА:", ib_bp.Метаданные.Имя, ib_bp.Метаданные.Версия)
