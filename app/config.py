"""Конфигурация портала EDO.ANESCOM.

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
        # utf-8-sig: config.env, сохранённый PowerShell Set-Content -Encoding UTF8, начинается с BOM —
        # иначе первая строка не читается (так 18.10 ссылки уходили с адресом 127.0.0.1)
        load_dotenv(_envf, override=False, encoding="utf-8-sig")
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
BRAND = "EDO.ANESCOM"
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

# --- ChatApp API (уведомления в WhatsApp) — значения только в config.env на сервере ---
CHATAPP_EMAIL = os.environ.get("CHATAPP_EMAIL", "")
CHATAPP_PASSWORD = os.environ.get("CHATAPP_PASSWORD", "")
CHATAPP_APP_ID = os.environ.get("CHATAPP_APP_ID", "app_33469_1")
CHATAPP_LICENSE = os.environ.get("CHATAPP_LICENSE", "40266")
CHATAPP_MESSENGER = os.environ.get("CHATAPP_MESSENGER", "grWhatsApp")

# --- Уведомления об оплате (ПКО / эквайринг) ---
# off — не отправлять; test — только на PAY_TEST_PHONES; live — клиентам
PAY_NOTIFY_MODE = os.environ.get("PAY_NOTIFY_MODE", "test").lower()
PAY_TEST_PHONES = [x for x in os.environ.get("PAY_TEST_PHONES", "").replace(";", ",").split(",") if x.strip()]
# Ссылка на чек ОФД; {i} номер чека, {f} РНК, {s} сумма, {t} дата-время ГГГГММДДTччммсс
PAY_RECEIPT_URL = os.environ.get("PAY_RECEIPT_URL", "https://cabinet.wofd.kz/consumer?i={i}&f={f}&s={s}&t={t}")

# Ключ в ссылке на PDF заказа для робота ChatApp (/b24/order-pdf/<ID>?k=...). Задать в config.env.
ORDER_PDF_KEY = os.environ.get("ORDER_PDF_KEY", "")

# --- Многошаговое подписание (накладная З-2: менеджер → кладовщик/помощник → клиент) ---
# off — ссылки не рассылать (только кабинет); test — только на SIGN_TEST_PHONES; live — всем
SIGN_NOTIFY_MODE = os.environ.get("SIGN_NOTIFY_MODE", "test").lower()
SIGN_TEST_PHONES = [x for x in (os.environ.get("SIGN_TEST_PHONES") or os.environ.get("PAY_TEST_PHONES", ""))
                    .replace(";", ",").split(",") if x.strip()]
# Срок шага по ролям в часах (просрочка и автонапоминания) и сколько раз напоминать
SIGN_SLA_HOURS = os.environ.get("SIGN_SLA_HOURS", "manager=4,storekeeper=8,client=48,other=24")
SIGN_REMIND_MAX = int(os.environ.get("SIGN_REMIND_MAX", "3") or 3)
# Поле сделки Bitrix с номером заказа 1С (напр. UF_CRM_…); пусто — поиск по названию сделки
Z2_DEAL_ORDER_FIELD = os.environ.get("Z2_DEAL_ORDER_FIELD", "")
# Явный список кладовщиков по городам (JSON); пусто — по подразделению «Склад <город>» в Bitrix
try:
    import json as _json
    Z2_STOREKEEPERS = _json.loads(os.environ.get("Z2_STOREKEEPERS", "") or "{}")
except Exception:
    Z2_STOREKEEPERS = {}
# 18.10.2026 23:13 решение пользователя: на основном складе Актобе подписывает только Гульфара
# (Калдымырзин Саламат перешёл на склад АВТОКОМП). Переопределяется Z2_STOREKEEPERS в config.env.
Z2_STOREKEEPERS.setdefault("Актобе", ["Бимагамбетова Гульфара"])
# Сотрудник → «свой склад» на портале, если отдел в Bitrix24 ещё старый (ФИО в нижнем регистре)
try:
    USER_CITY = _json.loads(os.environ.get("USER_CITY", "") or "{}")
except Exception:
    USER_CITY = {}
USER_CITY.setdefault("калдымырзин саламат", "АВТОКОМП")

# «Моя компания» сделки по подразделению менеджера (app/branch.py): город → ID «Моей компании»,
# только если автоматическое сопоставление по названию не подходит. Пример: {"Актобе": 12}
try:
    BRANCH_MAP = _json.loads(os.environ.get("BRANCH_MAP", "") or "{}")
except Exception:
    BRANCH_MAP = {}

# Свои компании среди контрагентов (внутригрупповые долги показываются на дашборде отдельно).
# Через запятую, часть названия без учёта регистра. Решение пользователя 18.10: АВТОКОМП — своё производство.
INTERNAL_CLIENTS = [x.strip().upper() for x in os.environ.get("EDO_INTERNAL_CLIENTS", "АВТОКОМП,ГРИНТЕ,GREENTE").split(",") if x.strip()]

# Вход сотрудников через Bitrix24 (локальное приложение «EDO.ANESCOM»; app/b24auth.py)
B24_DOMAIN = os.environ.get("B24_DOMAIN", "anescom.bitrix24.kz").strip().lower()
B24_CLIENT_ID = os.environ.get("B24_CLIENT_ID", "").strip()
B24_CLIENT_SECRET = os.environ.get("B24_CLIENT_SECRET", "").strip()
B24_ADMIN_IDS = [int(x) for x in os.environ.get("B24_ADMIN_IDS", "").replace(";", ",").split(",") if x.strip().isdigit()]

# Утренняя сводка в Bitrix24 (app/briefing.py): ID пользователей Bitrix24 через запятую. 18.10: сначала Болатұлы (355).
BRIEF_TO = [int(x) for x in os.environ.get("BRIEF_TO", "355").replace(";", ",").split(",") if x.strip().isdigit()]

# 6п (19.10.2026): кадровые документы из 1С (ANESCOM и АВТОКОМП) на подпись.
# Маршрут: кадровик → [сотрудник + лист ознакомления] → начальник подразделения (Bitrix24) → директор.
KADR_HR = os.environ.get("KADR_HR", "Караменова Лаура")
KADR_DIRECTOR_ANESCOM = os.environ.get("KADR_DIRECTOR_ANESCOM", "Кулданов Бекбол")
KADR_DIRECTOR_AVTOKOMP = os.environ.get("KADR_DIRECTOR_AVTOKOMP", "Имангалиева Алия")
