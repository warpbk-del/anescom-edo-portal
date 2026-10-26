# Новый сеанс REPL сразу к ANESCOM_FIX (после остановки bs2 26.10 14:26). Пароль вводит пользователь.
import win32com.client
_c = win32com.client.Dispatch("V83.COMConnector")
for _i in range(3):
    _pw = ask_pwd("Пароль ANESCOM_FIX (Болатұлы Бауыржан), Enter: ")
    if not _pw:
        continue
    try:
        ib = _c.Connect('File="D:\\Base\\1C\\ANESCOM_FIX";Usr="Болатұлы Бауыржан";Pwd="' + _pw + '";'); break
    except Exception as _e:
        print("НЕ ПОДКЛЮЧИЛОСЬ:", str(_e)[-90:])
    finally:
        _pw = None
REG = ib.Метаданные.РегистрыБухгалтерии.Получить(0).Имя
LOG = r"D:\Base\1C\ANESCOM_FIX_fix_log.txt"
print("ПОДКЛЮЧЕНО ANESCOM_FIX:", ib.Метаданные.Имя, ib.Метаданные.Версия, "| журнал", LOG)
