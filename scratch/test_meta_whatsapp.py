import os
import sys
import requests
import django

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from icemake_bot.strategy import _send_meta_whatsapp_template

def test_meta_whatsapp():
    phone_id = os.getenv("ICEMAKE_PHONE_NUMBER_ID") or "1272077585997381"
    token = os.getenv("META_ACCESS_TOKEN")

    print(f"🔍 Testing Meta WhatsApp Cloud API...")
    print(f"Phone ID: {phone_id}")

    customer_phone = "919913381306"
    engineer_phone = "919104142402"

    print(f"\n1️⃣ Sending Customer Template 'icemake_customer' to {customer_phone}...")
    res1 = _send_meta_whatsapp_template(
        to_phone=customer_phone,
        template_name="icemake_customer",
        parameters=["C020926367"]
    )
    print(f"Customer Response: {res1}")

    print(f"\n2️⃣ Sending Engineer Template 'icemake_serviceengineer' to {engineer_phone}...")
    res2 = _send_meta_whatsapp_template(
        to_phone=engineer_phone,
        template_name="icemake_serviceengineer",
        parameters=[
            "C020926367",
            "Harshal Patel",
            "919913381306",
            "Ahmedabad, Gujarat",
            "Blast Freezer",
            "No Cooling / Insufficient Cooling",
            "Mr Rutvik"
        ]
    )
    print(f"Engineer Response: {res2}")

if __name__ == "__main__":
    test_meta_whatsapp()
