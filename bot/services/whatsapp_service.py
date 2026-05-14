import requests
from django.conf import settings

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