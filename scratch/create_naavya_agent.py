import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from django.contrib.auth.models import User
from agents.models import VoiceAgent, AgentRoleTemplate, Industry

def setup_naavya():
    try:
        # 1. Retrieve Aisha's details to copy owner and industry
        aisha_id = "92edcbdf-1b70-4c7b-a69e-faf15c829860"
        aisha = VoiceAgent.objects.get(id=aisha_id)
        owner = aisha.owner
        industry = aisha.industry
        default_voice = aisha.role_template.default_voice if aisha.role_template else "aSFxChEgBmCyExpaDqHd"
    except VoiceAgent.DoesNotExist:
        owner = User.objects.first()
        industry = Industry.objects.get(slug="automobile")
        default_voice = "aSFxChEgBmCyExpaDqHd"

    # 2. Get the role template we seeded
    try:
        role_template = AgentRoleTemplate.objects.get(
            role_name="Naavya Automobile Advisor",
            industry=industry
        )
    except AgentRoleTemplate.DoesNotExist:
        print("Role template 'Naavya Automobile Advisor' not found. Please run seed_roles first.")
        return

    # 3. Get or create Naavya agent
    naavya_agent, created = VoiceAgent.objects.get_or_create(
        name="Naavya",
        owner=owner,
        industry=industry,
        defaults={
            "role_template": role_template,
            "company_name": "Premium Car Showroom",
            "summary": "Warm and enthusiastic automobile consultant",
            "is_active": True
        }
    )
    if not created:
        naavya_agent.role_template = role_template
        naavya_agent.save()
        print(f"Naavya agent already exists. Updated her role to Naavya Automobile Advisor.")
    else:
        # If Priya exists, delete her so we don't have duplicates
        VoiceAgent.objects.filter(name="Priya").delete()
        print(f"Created new Naavya agent with role Naavya Automobile Advisor (and deleted any old Priya agents).")

    print("\nNaavya Agent Info:")
    print(f"Agent ID: {naavya_agent.id}")
    print(f"API Key: {naavya_agent.api_key}")
    print(f"Role: {naavya_agent.role_template.role_name}")
    print(f"Company: {naavya_agent.company_name}")

if __name__ == "__main__":
    setup_naavya()
