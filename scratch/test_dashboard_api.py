import os
import sys
import django

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from conversations.views import icemake_dashboard_data
from rest_framework.test import APIRequestFactory

factory = APIRequestFactory()
request = factory.get('/api/icemake-dashboard/data/')

response = icemake_dashboard_data(request)
data = response.data

print("STATUS CODE:", response.status_code)
print("TOTAL COUNT:", data.get("total_count"))
print("VOICE COUNT:", data.get("voice_count"))
print("WHATSAPP COUNT:", data.get("whatsapp_count"))

tickets = data.get("tickets", [])
print(f"Loaded {len(tickets)} total combined tickets.")

if tickets:
    print("Sample First Ticket:", tickets[0])
