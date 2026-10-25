# Проект 22: найти базу АВТОКОМП в списках баз сервера и подключиться ТОЛЬКО ДЛЯ ЧТЕНИЯ (ib_av). Логин/пароль вводит пользователь.
import glob, re
found = []
for f in glob.glob(r"C:\Users\*\AppData\Roaming\1C\1CEStart\ibases.v8i"):
    txt = open(f, encoding="utf-8-sig", errors="ignore").read()
    for name, conn in re.findall(r"^\[(.+?)\]\s*\nConnect=(.+?)$", txt, re.M):
        if any(w in name.upper() for w in ("АВТО", "AVTO")) and (name, conn) not in found:
            found.append((name, conn.strip()))
for i, (n, c) in enumerate(found): print(i, "|", n, "|", c)
AV_IDX = globals().get("AV_IDX")
if AV_IDX is None:
    print("Выберите базу: AV_IDX = номер, затем снова run(... 'avConnect')")
else:
    cs = found[AV_IDX][1].rstrip(";")
    u = input("Пользователь базы АВТОКОМП: ").strip()
    pw = ask_pwd("Пароль (звёздочки), Enter: ")
    conn_av = win32com.client.Dispatch("V83.COMConnector")
    ib_av = conn_av.Connect(f'{cs};Usr="{u}";Pwd="{pw}";')
    pw = None
    print("АВТОКОМП ПОДКЛЮЧЕНА:", found[AV_IDX][0], "|", ib_av.Метаданные.Имя, ib_av.Метаданные.Версия, "| ANESCOM:", ib.Метаданные.Версия)
