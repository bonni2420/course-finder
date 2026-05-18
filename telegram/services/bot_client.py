import json
import logging
from urllib import error, request

from django.conf import settings

TELEGRAM_API_BASE = "https://api.telegram.org"
logger = logging.getLogger(__name__)


def send_message(chat_id: int, text: str) -> None:
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return

    url = f"{TELEGRAM_API_BASE}/bot{token}/sendMessage"
    payload = json.dumps(
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
    ).encode("utf-8")

    req = request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=10) as response:
            response.read()
    except error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        logger.warning("Telegram sendMessage failed: status=%s body=%s", exc.code, response_body)
    except error.URLError as exc:
        logger.warning("Telegram sendMessage connection failed: %s", exc)


def send_photo(chat_id: int, photo_url: str, caption: str = "") -> None:
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return

    url = f"{TELEGRAM_API_BASE}/bot{token}/sendPhoto"
    payload = json.dumps(
        {
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": caption,
            "parse_mode": "HTML",
        }
    ).encode("utf-8")

    req = request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=10) as response:
            response.read()
    except error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        logger.warning("Telegram sendPhoto failed: status=%s body=%s", exc.code, response_body)
    except error.URLError as exc:
        logger.warning("Telegram sendPhoto connection failed: %s", exc)
