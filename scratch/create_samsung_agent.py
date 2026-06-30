# scratch/create_samsung_agent.py

import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from django.contrib.auth.models import User
from agents.models import VoiceAgent, AgentRoleTemplate, Industry

def setup_samsung():
    try:
        aisha_id = "92edcbdf-1b70-4c7b-a69e-faf15c829860"
        aisha = VoiceAgent.objects.get(id=aisha_id)
        owner = aisha.owner
    except VoiceAgent.DoesNotExist:
        owner = User.objects.first()

    # Get Industry
    try:
        industry = Industry.objects.get(slug="samsung-store")
    except Industry.DoesNotExist:
        print("Industry 'samsung-store' not found. Please run seed_roles first.")
        return

    # Get the role template we seeded
    try:
        role_template = AgentRoleTemplate.objects.get(
            role_name="Naavya Samsung Store Advisor",
            industry=industry
        )
    except AgentRoleTemplate.DoesNotExist:
        print("Role template 'Naavya Samsung Store Advisor' not found. Please run seed_roles first.")
        return

    # Create/Get Samsung agent by spec    # Create/Get Samsung agent
    samsung_agent, created = VoiceAgent.objects.get_or_create(
        name="Naavya Store Bot",
        owner=owner,
        industry=industry,
        defaults={
            "role_template": role_template,
            "company_name": "Vtech Samsung Care",
            "summary": "Friendly customer advisor for Samsung products",
            "is_active": True
        }
    )
    if not created:
        samsung_agent.role_template = role_template
        samsung_agent.save()
        print(f"Samsung agent already exists. Updated role template.")
    else:
        print(f"Created new Samsung agent.")

    print("\nSamsung Agent Info:")
    print(f"Agent ID: {samsung_agent.id}")
{samsung_agent.role_template.role_name}")
    print(f"Company: {samsung_agent.company_name}")

if __name__ == "__main__":
    setup_samsung()
