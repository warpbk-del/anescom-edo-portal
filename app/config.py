"""Конфигурация портала ЭДО АНЕСКОМ.

Все секреты и параметры читаются из переменных окружения (файл config.env на
сервере грузится через python-dotenv в start-скрипте или systemd/schtasks).
Значения по умолчанию рассчитаны на локальную разработку.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Загрузка config.env (рядом с приложением или по пути EDO_ENV_FILE), если есть
try:
    from dotenv import load_dotenv
    _envf = os.environ.get("EDO_ENV_FILE", str(BASE_DIR / "config.env"))
    if os.path.exists(_envf):
        load_dotenv(_envf, override=False)
except Exception:
    pass
DATA_DIR = Path(os.environ.get("EDO_DATA_DIR", BASE_DIR / "data"))
DOCS_DIR = DATA_DIR / "docs"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "edo.sqlite3"

# Публичный базовый URL портала (для формирования ссылок клиентам).
# На проде: https://bot.anescom.kz/dogovor
PUBLIC_BASE_URL = os.environ.get("EDO_PUBLIC_BASE_URL", "http://127.0.0.1:8096").rstrip("/")

# Префикс монтирования (должен совпадать с хвостом PUBLIC_BASE_URL и маршрутом caddy).
ROOT_PATH = os.environ.get("EDO_ROOT_PATH", "")  # напр. "/dogovor" на проде

# Токен, которым 1С аутентифицирует запросы к API портала (Bearer).
API_TOKEN = os.environ.get("EDO_API_TOKEN", "dev-api-token-change-me")

# Бренд
BRAND = "ЭДО АНЕСКОМ"
COMPANY = 'ТОО «ANESCOM/АНЕСКОМ»'

# Длина кода подтверждения (ПЭП), отправляемого в WhatsApp
SIGN_CODE_LEN = int(os.environ.get("EDO_SIGN_CODE_LEN", "4"))

# Сколько дней ссылка действительна
LINK_TTL_DAYS = int(os.environ.get("EDO_LINK_TTL_DAYS", "14"))

# Таймзона для отображения (Казахстан, UTC+5)
TZ_OFFSET_HOURS = int(os.environ.get("EDO_TZ_OFFSET_HOURS", "5"))

# Пароль входа в кабинет для сотрудников ANESCOM
STAFF_PASSWORD = os.environ.get("EDO_STAFF_PASSWORD", "anescom")
# Секрет для подписи cookie сессии кабинета
SECRET_KEY = os.environ.get("EDO_SECRET_KEY", "dev-secret-change-me")

# --- WhatsApp / Bitrix (для задачи отправки ссылки) ---
B24_WEBHOOK = os.environ.get("EDO_B24_WEBHOOK", "").rstrip("/")
# Строка исходящего коннектора/линии ChatApp при необходимости
WA_LINE = os.environ.get("EDO_WA_LINE", "")
WA_CONNECTOR = os.environ.get("EDO_WA_CONNECTOR", "")
