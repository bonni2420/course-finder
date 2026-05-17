import json

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from resources.services.resource_service import render_latest_resource_messages
from telegram.services.bot_client import send_message, send_photo
from telegram.services.message_handler import build_reply

RESOURCE_COMMANDS = {"/resources", "resources", "/latest", "latest", "/khoahoc", "khoahoc"}


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

    if command_text in RESOURCE_COMMANDS:
        resource_messages = render_latest_resource_messages(request)
        if not resource_messages:
            send_message(chat_id=chat_id, text="Hiện chưa có khóa học nào. Vui lòng thử lại sau.")
            return JsonResponse({"ok": True})

        for resource_message in resource_messages:
            photo_url = resource_message["photo_url"]
            caption = resource_message["caption"]
            if photo_url:
                send_photo(chat_id=chat_id, photo_url=photo_url, caption=caption)
            else:
                send_message(chat_id=chat_id, text=caption)
        return JsonResponse({"ok": True})

    reply = build_reply(command_text)
    send_message(chat_id=chat_id, text=reply)
    return JsonResponse({"ok": True})
