# -*- coding: utf-8 -*-
# REPL к ANESCOM_FIX без подключения к KA2026: python -i repl_fix.py  (пароль вводит пользователь)
import urllib.request
_src = urllib.request.urlopen("https://raw.githubusercontent.com/warpbk-del/anescom-edo-portal/main/tools/com_repl.py", timeout=30).read().decode("utf-8-sig")
assert "\nconnect()" in _src
exec(compile(_src.replace("\nconnect()", "\n# connect() пропущен"), "com_repl", "exec"), globals())
run("main", "fixConnect")
