from rest_framework.decorators import api_view
from rest_framework.response import Response

from conversations.services.core.dialogue_engine import process_message
from .service import send_whatsapp_message


@api_view(["POST"])
def whatsapp_webhook(request):
    data = request.data

    phone = data.get("from")
    text = data.get("message")

    if not phone or not text:
        return Response({"status": "invalid"})

    reply, _ = process_message(
        agent="insurance_bot",
        message=text,
        session_id=phone,
        channel="whatsapp"
    )

    send_whatsapp_message(phone, reply)

    return Response({"status": "ok"})