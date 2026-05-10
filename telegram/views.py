import json

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from telegram.services.bot_client import send_message
from telegram.services.message_handler import build_reply


@csrf_exempt
def telegram_webhook(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    try:
        update = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({"ok": True})

    message = update.get("message") or {}
    command_text = (message.get("text") or "").strip().lower()
    chat = message.get("chat") or {}
    chat_id = chat.get("id")

    if not chat_id:
        return JsonResponse({"ok": True})

    reply = build_reply(command_text)
    send_message(chat_id=chat_id, text=reply)
    return JsonResponse({"ok": True})
