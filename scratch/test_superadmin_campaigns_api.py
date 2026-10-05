import os
import sys
import django

sys.path.append("c:\\Users\\AYUSHI PATEL\\Voicebot_saas\\sarvam_manuual\\Voice-Bot-SaaS")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from conversations.views import sarvam_admin_all_campaigns_api

factory = RequestFactory()

def test_superadmin_campaigns():
    print("\n=== TESTING SUPERADMIN GLOBAL CAMPAIGNS API ===")
    
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        print("Superuser not found!")
        return

    req = factory.get('/api/sarvam/admin/campaigns/')
    req.user = admin_user

    res = sarvam_admin_all_campaigns_api(req)
    print(f"Status Code: {res.status_code}")
    print(f"Response Data: {res.data}")

if __name__ == "__main__":
    test_superadmin_campaigns()
