@echo off
REM --- Запуск портала ЭДО АНЕСКОМ ---
cd /d D:\anescom_edo
set EDO_ENV_FILE=D:\anescom_edo\config.env
call .venv\Scripts\activate.bat
python -m uvicorn app.main:app --host 127.0.0.1 --port 8096
