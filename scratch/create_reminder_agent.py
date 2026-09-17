import os
import sys
import django

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from django.contrib.auth.models import User
from agents.models import Industry, AgentRoleTemplate, VoiceAgent

def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    # 1. Get the admin or first user as owner
    owner = User.objects.filter(is_superuser=True).first()
    if not owner:
        owner = User.objects.first()
    if not owner:
        print("[ERROR] No User found in database. Please register a user first.")
        return

    # 2. Get the Reminder Industry
    try:
        industry = Industry.objects.get(slug="reminder-industry")
    except Industry.DoesNotExist:
        print("[ERROR] Reminder Industry not seeded yet. Please run: python manage.py seed_roles")
        return

    # 3. Get the JMS Loan Reminder Advisor role template
    try:
        role_template = AgentRoleTemplate.objects.get(industry=industry, role_name="JMS Loan Reminder Advisor")
    except AgentRoleTemplate.DoesNotExist:
        print("[ERROR] Role template not found. Please run: python manage.py seed_roles")
        return

    # 4. Create or update the VoiceAgent
    agent, created = VoiceAgent.objects.update_or_create(
        name="JMS Loan Reminder Agent",
        defaults={
            "owner": owner,
            "industry": industry,
            "role_template": role_template,
            "company_name": "JMS Bank",
            "summary": "તમારી EMI ની તારીખ નજીક છે, તમે ક્યારે ચુકવણી કરશો?",
            "is_demo": False,
            "is_active": True,
        }
    )

    if created:
        print(f"[OK] VoiceAgent '{agent.name}' created with ID: {agent.id}")
    else:
        print(f"[OK] VoiceAgent '{agent.name}' updated with ID: {agent.id}")

if __name__ == "__main__":
    main()
