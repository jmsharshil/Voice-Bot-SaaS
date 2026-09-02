import os
import sys
import django

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from django.contrib.auth.models import User
from accounts.models import Role, UserProfile
from agents.models import VoiceAgent

def create_icemake_user():
    print("🚀 Seeding / Creating Ice Make User & Role...")

    # 1. Get or Create "Ice Make User" Role
    role, _ = Role.objects.get_or_create(
        name="Ice Make User",
        defaults={
            "description": "Exclusive dashboard access for ICEMAKE Refrigeration Ltd. tickets & call recordings.",
            "permissions": {"can_view_icemake_dashboard": True}
        }
    )
    print(f"📋 Role: {role.name}")

    # 2. Get Ice Make Voice Agent
    agent = VoiceAgent.objects.filter(role_template__role_name__icontains="Ice Make").first()
    if not agent:
        print("❌ Ice Make Voice Agent not found in DB! Please run seed_icemake script first.")
        return

    print(f"🤖 Found Voice Agent: {agent.name} ({agent.id})")

    # 3. Create or Update User 'icemake'
    user, created = User.objects.get_or_create(
        username="icemake",
        defaults={
            "email": "support@icemakeindia.com",
            "first_name": "Ice Make",
            "last_name": "Support Team",
            "is_staff": True
        }
    )
    user.set_password("icemake123")
    user.save()

    # 4. Attach UserProfile
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.role = role
    profile.assigned_agent = agent
    profile.save()

    print("\n✅ ICE MAKE USER CREATED SUCCESSFULLY!")
    print("---------------------------------------")
    print(f"Username : icemake")
    print(f"Password : icemake123")
    print(f"Role     : {role.name}")
    print(f"Agent    : {agent.name}")
    print(f"Dashboard: http://localhost:8000/icemake-dashboard/")
    print("---------------------------------------")

if __name__ == "__main__":
    create_icemake_user()
