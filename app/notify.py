"""Отправка ссылки на подпись клиенту в WhatsApp.

Пока реализован безопасный режим по умолчанию: функция формирует текст и
возвращает его со статусом 'manual' (ссылку отправляет оператор или 1С).
Реальная интеграция с исходящим WhatsApp (ChatApp/Bitrix) подключается в
задаче #54 — для этого достаточно заполнить EDO_B24_WEBHOOK / EDO_WA_* и
дописать _send_via_bitrix().
"""
import logging

from . import config

log = logging.getLogger("edo.notify")


def build_message(link: str, code: str, title: str, client_name: str = None) -> str:
    hello = f"Здравствуйте, {client_name}!" if client_name else "Здравствуйте!"
    link = f"{link}{'&' if '?' in link else '?'}k={code}"   # код в ссылке — клиенту вводить не нужно
    return (
        f"{hello}\n\n"
        f"{config.COMPANY} направляет вам документ на подпись: «{title}».\n\n"
        f"Подписать за 1 минуту:\n{link}\n\n"
        f"1) Откройте ссылку и проверьте документ.\n"
        f"2) Поставьте галочку «ознакомлен(а)».\n"
        f"3) Нажмите «Подписать документ».\n\n"
        f"Если на странице попросят код — {code}.\n"
        f"Не согласны — там же кнопка «Отказаться» с причиной.\n\n"
        f"{config.COMPANY} · портал {config.BRAND}"
    )


def _send_via_bitrix(phone: str, text: str) -> dict:
    """Заглушка под реальную отправку исходящего WhatsApp через Bitrix/ChatApp.

    Вернёт {'status': 'sent'} при успехе. Реализация в задаче #54.
    """
    return {"status": "not_configured"}


def send_sign_link(phone, link, code, title, client_name=None) -> dict:
    text = build_message(link, code, title, client_name)
    if not phone:
        log.info("Нет телефона клиента — отправка вручную")
        return {"status": "manual", "reason": "no_phone", "text": text, "link": link}

    if config.B24_WEBHOOK:
        try:
            res = _send_via_bitrix(phone, text)
            if res.get("status") == "sent":
                log.info("Ссылка отправлена в WhatsApp: %s", phone)
                return {"status": "sent", "channel": "bitrix", "link": link}
            log.info("Bitrix-отправка недоступна: %s", res)
        except Exception as e:  # noqa
            log.exception("Ошибка отправки через Bitrix")
            return {"status": "error", "error": str(e), "text": text, "link": link}

    # безопасный дефолт — ручная отправка
    return {"status": "manual", "text": text, "link": link}
