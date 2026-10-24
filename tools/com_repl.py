# -*- coding: utf-8 -*-
"""Интерактивная сессия COM к КОПИИ базы 1С (D:\\Base\\1C\\KA2026) для исправлений аудита (проект 21).
Запуск на сервере:  D:\\anescom_edo\\com_venv\\Scripts\\python.exe -i com_repl.py
Пароль вводит пользователь (getpass, на экран не выводится).
Дальше: run("<sha>", "<имя_задания>") — скачивает tools/com_jobs/<имя>.py из GitHub на этом коммите и выполняет
с глобальными ib (соединение), q() (запрос), log() (журнал исправлений D:\\anescom_edo\\data\\reports\\com_fix_log.txt).
"""
import datetime
import getpass
import io
import sys
import traceback
import urllib.request

import pythoncom
import win32com.client

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
BASE = "https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/{sha}/tools/com_jobs/{name}.py"
LOG = r"D:\anescom_edo\data\reports\com_fix_log.txt"

user = input("Пользователь 1С (Enter = Болатұлы Бауыржан): ").strip() or "Болатұлы Бауыржан"
pwd = getpass.getpass("Пароль копии: ")
conn = win32com.client.Dispatch("V83.COMConnector")
ib = conn.Connect(f'File="D:\\Base\\1C\\KA2026";Usr="{user}";Pwd="{pwd}";')
del pwd
print("ПОДКЛЮЧЕНО:", ib.Метаданные.Имя, ib.Метаданные.Версия)
REG = ib.Метаданные.РегистрыБухгалтерии.Получить(0).Имя
print("Регистр БУ:", REG)


def q(text, **params):
    """Выполнить запрос 1С, вернуть список dict (ключи — колонки)."""
    z = ib.NewObject("Запрос")
    z.Текст = text.replace("{REG}", REG)
    for k, v in params.items():
        z.УстановитьПараметр(k, v)
    res = z.Выполнить()
    cols = [res.Колонки.Получить(i).Имя for i in range(res.Колонки.Количество())]
    out, sel = [], res.Выбрать()
    while sel.Следующий():
        out.append({c: getattr(sel, c) for c in cols})
    return out


def s(v):
    """Строковое представление значения 1С."""
    try:
        return ib.String(v)
    except Exception:
        return str(v)


def log(msg):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run(sha, name):
    src = urllib.request.urlopen(BASE.format(sha=sha, name=name), timeout=30).read().decode("utf-8-sig")
    print(f"--- задание {name} @ {sha[:7]}")
    try:
        exec(compile(src, name, "exec"), globals())
    except Exception:
        traceback.print_exc()
    print(f"--- конец {name}")
