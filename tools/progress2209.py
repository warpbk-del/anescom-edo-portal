# -*- coding: utf-8 -*-
"""21-31: сколько ссылок на помеченный дубль счёта 2209 ещё осталось в ANESCOM_FIX (только чтение).
Отдельное (второе) подключение; пароль вводит пользователь. До замены было 34 974 (ЗаказКлиента 14 512, Реализация 11 149, ...).
Запуск: D:\\anescom_edo\\com_venv\\Scripts\\python.exe progress2209.py
"""
import collections, io, sys, time, msvcrt
import win32com.client
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

def ask_pwd(prompt):
    time.sleep(0.5)
    while msvcrt.kbhit(): msvcrt.getwch()   # выбросить лишние нажатия (Enter после вставки команды)
    print(prompt, end="", flush=True); buf = []
    while True:
        ch = msvcrt.getwch()
        if ch in ("\r", "\n"): print(); return "".join(buf)
        if ch == "\x08":
            if buf: buf.pop(); print("\b \b", end="", flush=True)
            continue
        buf.append(ch); print("*", end="", flush=True)

c = win32com.client.Dispatch("V83.COMConnector")
ib = None
for _ in range(3):
    pw = ask_pwd("Пароль ANESCOM_FIX (Болатұлы Бауыржан), Enter: ")
    if not pw:
        continue
    try:
        ib = c.Connect('File="D:\\Base\\1C\\ANESCOM_FIX";Usr="Болатұлы Бауыржан";Pwd="' + pw + '";'); break
    except Exception as e:
        print("НЕ ПОДКЛЮЧИЛОСЬ (раскладка EN/RU?):", str(e)[-90:])
    finally:
        pw = None
if ib is None: sys.exit("нет подключения")
z = ib.NewObject("Запрос")
z.Текст = 'ВЫБРАТЬ Т.Ссылка КАК С, Т.Наименование КАК Н, Т.ПометкаУдаления КАК П ИЗ Справочник.БанковскиеСчетаОрганизаций КАК Т ГДЕ Т.ПометкаУдаления И Т.НомерСчета ПОДОБНО "%2209"'
sel = z.Выполнить().Выбрать(); olds = []
while sel.Следующий(): olds.append((sel.С, sel.Н))
print("Помеченных счетов …2209:", len(olds), [n for _, n in olds])
if not olds:
    print("Дубль уже удалён — замена закончилась (смотрите итог в консоли bs2)."); sys.exit()
t0 = time.time()
a = ib.NewObject("Массив")
for r, _ in olds: a.Добавить(r)
t = ib.НайтиПоСсылкам(a)
cnt = collections.Counter()
for i in range(t.Количество()):
    cnt[t.Получить(i).Метаданные.ПолноеИмя()] += 1
total = sum(cnt.values())
print(f"Осталось ссылок: {total} из 34 974 (сделано {34974 - total}, {100*(34974-total)/34974:.0f}%), поиск {int(time.time()-t0)} с, {time.strftime('%H:%M')}")
for k, v in cnt.most_common(12): print(f"  {v:6d}  {k}")
