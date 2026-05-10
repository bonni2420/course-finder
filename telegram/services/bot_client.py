import json
from urllib import error, request

from django.conf import settings

TELEGRAM_API_BASE = "https://api.telegram.org"


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
        request.urlopen(req, timeout=10)
    except error.URLError:
        return
