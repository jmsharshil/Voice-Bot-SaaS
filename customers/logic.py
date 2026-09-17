import requests

from customers.models import Customer, ChatMessage
from bot.services.whatsapp_service import send_whatsapp_message

# import your helpers if needed
from customers.services.expiry_service import *
from customers.services.renewal_service import *
from django.conf import settings 


def save_msg(customer, message, sender):
    ChatMessage.objects.create(customer=customer, message=message, sender=sender)


def handle_whatsapp_logic(phone, raw_text):

    text = raw_text.lower().strip()

    customer = Customer.objects.filter(phone=phone).first()

    if not customer:
        customer = Customer.objects.create(
            phone=phone,
            name="User",
            source="inbound",
            conversation_state="inactive",
        )

    save_msg(customer, text, "user")

    # 🔥 SIMPLE VERSION (you can expand later)
    if customer.conversation_state == "inactive":

        reply = (
            "Hello! 👋 Welcome to Vehicle customers\n\n"
            "1️⃣ New customers\n"
            "2️⃣ Renewal"
        )
        customer.conversation_state = "ask_service_type"

    elif customer.conversation_state == "ask_service_type":

        if text == "1":
            reply = "You selected New customers 🚗"
        elif text == "2":
            reply = "You selected Renewal 🔁"
        else:
            reply = "Please reply with 1 or 2"

    else:
        reply = "Say Hi to start again 😊"

    customer.save()
    save_msg(customer, reply, "bot")

    return reply

def send_whatsapp_message(phone, message):

    url = f"{settings.WA_SENDER_BASE_URL}/send-message"

    headers = {
        "Authorization": f"Bearer {settings.WA_SENDER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "to": phone,   # ✅ NO @c.us
        "text": message
    }

    print("FINAL PHONE:", phone)
    print("URL:", url)

    response = requests.post(url, json=payload, headers=headers)

    print("STATUS:", response.status_code)
    print("RESPONSE:", response.text)

    try:
        return response.json()
    except:
        return response.text