# scratch/create_fold8_agent.py

import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from django.contrib.auth.models import User
from agents.models import VoiceAgent, AgentRoleTemplate, Industry

def setup_fold8():
    try:
        aisha_id = "92edcbdf-1b70-4c7b-a69e-faf15c829860"
        aisha = VoiceAgent.objects.get(id=aisha_id)
        owner = aisha.owner
    except VoiceAgent.DoesNotExist:
        owner = User.objects.first()
        if not owner:
            print("No users found in database. Cannot create agent.")
            return

    # Get Industry
    try:
        industry = Industry.objects.get(slug="samsung-store")
    except Industry.DoesNotExist:
        print("Industry 'samsung-store' not found. Please run seed_roles first.")
        return

    # Get the role template we seeded
    try:
        role_template = AgentRoleTemplate.objects.get(
            role_name="Galaxy Z Fold8 Pre-Reserve Advisor",
            industry=industry
        )
    except AgentRoleTemplate.DoesNotExist:
        print("Role template 'Galaxy Z Fold8 Pre-Reserve Advisor' not found. Please run seed_roles first.")
        return

    # Create/Get Samsung Fold8 agent
    fold8_agent, created = VoiceAgent.objects.get_or_create(
        name="Naavya",
        owner=owner,
        industry=industry,
        role_template=role_template,
        defaults={
            "company_name": "VTech NxtGen Retails LLP",
            "summary": "Outbound Galaxy Z Fold8 Pre-Reserve campaign advisor",
            "is_active": True
        }
    )
    if not created:
        fold8_agent.role_template = role_template
        fold8_agent.company_name = "VTech NxtGen Retails LLP"
        fold8_agent.summary = "Outbound Galaxy Z Fold8 Pre-Reserve campaign advisor"
        fold8_agent.save()
        print(f"Galaxy Z Fold8 agent already exists. Updated details.")
    else:
        print(f"Created new Galaxy Z Fold8 agent.")

    print("\nGalaxy Z Fold8 Agent Info:")
    print(f"Agent ID: {fold8_agent.id}")
    print(f"Role: {fold8_agent.role_template.role_name}")
    print(f"Company: {fold8_agent.company_name}")

if __name__ == "__main__":
    setup_fold8()
