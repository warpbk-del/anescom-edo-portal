"""Отправка сообщений в WhatsApp через API ChatApp (https://api.chatapp.online/docs).

Токен получаем методом v1.tokens по email/паролю кабинета и App ID
(живёт 24 ч, лимит 100 токенов в сутки) и держим в файле до истечения.
Все секреты — только в config.env на сервере (CHATAPP_EMAIL / CHATAPP_PASSWORD).
"""
import json
import logging
import re
import time

import httpx

from . import config

log = logging.getLogger("edo.chatapp")

API = "https://api.chatapp.online/v1"
_TOKEN_FILE = config.DATA_DIR / "chatapp_token.json"


def is_configured() -> bool:
    return bool(config.CHATAPP_EMAIL and config.CHATAPP_PASSWORD
                and config.CHATAPP_APP_ID and config.CHATAPP_LICENSE)


def normalize_phone(phone: str) -> str:
    """Казахстанский номер → 7XXXXXXXXXX (формат chatId для WhatsApp)."""
    d = re.sub(r"\D", "", phone or "")
    if len(d) == 11 and d[0] == "8":
        d = "7" + d[1:]
    elif len(d) == 10:
        d = "7" + d
    return d if len(d) == 11 and d[0] == "7" else ""


_KZ_MOBILE = re.compile(r"^7(70[0-8]|747|75[01]|76[0-4]|771|77[5-8])\d{7}$")


def is_mobile(n: str) -> bool:
    """Мобильный Казахстан (WhatsApp); городские 7 7xxx… отсекаем."""
    return bool(_KZ_MOBILE.match(n or ""))


def first_phone(phones: str) -> str:
    """Из списка телефонов 1С (через ; или ,) — первый мобильный."""
    for part in re.split(r"[;,\n]", phones or ""):
        n = normalize_phone(part)
        if is_mobile(n):
            return n
    return ""


def _token(force: bool = False) -> str:
    if not force and _TOKEN_FILE.exists():
        try:
            t = json.loads(_TOKEN_FILE.read_text(encoding="utf-8"))
            if t.get("accessTokenEndTime", 0) - 600 > time.time():
                return t["accessToken"]
        except Exception:
            pass
    r = httpx.post(f"{API}/tokens", timeout=20, headers={"Lang": "ru"}, json={
        "email": config.CHATAPP_EMAIL,
        "password": config.CHATAPP_PASSWORD,
        "appId": config.CHATAPP_APP_ID,
    })
    r.raise_for_status()
    data = r.json().get("data") or {}
    if not data.get("accessToken"):
        raise RuntimeError(f"ChatApp не выдал токен: {r.text[:300]}")
    _TOKEN_FILE.write_text(json.dumps({
        "accessToken": data["accessToken"],
        "accessTokenEndTime": data.get("accessTokenEndTime", time.time() + 3600),
    }), encoding="utf-8")
    return data["accessToken"]


def _post(path: str, body: dict) -> dict:
    url = (f"{API}/licenses/{config.CHATAPP_LICENSE}/messengers/"
           f"{config.CHATAPP_MESSENGER}/{path}")
    for attempt in (0, 1):
        r = httpx.post(url, timeout=30, json=body, headers={
            "Authorization": _token(force=attempt == 1), "Lang": "ru"})
        if attempt == 0 and (r.status_code == 401 or (r.status_code == 403 and "InvalidToken" in r.text)):
            continue  # токен протух или отозван раньше срока (403 ApiInvalidTokenError) — берём новый
        try:
            js = r.json()
        except Exception:
            js = {"raw": r.text[:300]}
        if r.status_code >= 400 or js.get("success") is False:
            raise RuntimeError(f"ChatApp {r.status_code}: {json.dumps(js, ensure_ascii=False)[:400]}")
        return js
    raise RuntimeError("ChatApp: не удалось авторизоваться")


def send_text(phone: str, text: str) -> dict:
    chat = normalize_phone(phone)
    if not chat:
        raise ValueError(f"Некорректный номер телефона")
    return _post(f"chats/{chat}/messages/text", {"text": text})


def send_file(phone: str, file_url: str, file_name: str, caption: str = "") -> dict:
    chat = normalize_phone(phone)
    if not chat:
        raise ValueError(f"Некорректный номер телефона")
    return _post(f"chats/{chat}/messages/file",
                 {"file": file_url, "fileName": file_name, "caption": caption})
