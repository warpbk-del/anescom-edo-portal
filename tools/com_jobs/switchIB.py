# 21-П: переключить сеанс COM на другую файловую базу (TARGET), сохранив прежние соединения.
# После переключения все задания (q, ib, REG, log) работают с TARGET. Пароль вводит пользователь в этом окне.
# TARGET = r"D:\Base\1C\AVTOKOMP_FIX" | r"D:\Base\1C\ANESCOM_FIX" | r"D:\Base\1C\KA2026" (копия)
TARGET = globals().get("TARGET")
_pool = globals().setdefault("IB_POOL", {})
if "cur" not in globals().get("IB_STATE", {}):
    globals()["IB_STATE"] = {"cur": r"D:\Base\1C\KA2026"}
    _pool[r"D:\Base\1C\KA2026"] = (ib, REG)
assert TARGET, "задайте TARGET"
if TARGET in _pool:
    ib, REG = _pool[TARGET]
else:
    u = input(f"Пользователь базы {TARGET} (Enter = Болатұлы Бауыржан): ").strip() or "Болатұлы Бауыржан"
    pw = ask_pwd("Пароль (звёздочки), Enter: ")
    c = win32com.client.Dispatch("V83.COMConnector")
    ib_new = c.Connect(f'File="{TARGET}";Usr="{u}";Pwd="{pw}";'); pw = None
    ib = ib_new; REG = ib.Метаданные.РегистрыБухгалтерии.Получить(0).Имя
    _pool[TARGET] = (ib, REG)
IB_STATE["cur"] = TARGET
LOG = TARGET + "_fix_log.txt"
print("ТЕКУЩАЯ БАЗА:", TARGET, "|", ib.Метаданные.Имя, ib.Метаданные.Версия, "| регистр", REG, "| журнал", LOG)
try:
    print("организации:", [s(r["Н"]) for r in q("ВЫБРАТЬ О.Наименование КАК Н ИЗ Справочник.Организации КАК О")])
except Exception as e: print(str(e)[-100:])
