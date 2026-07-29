# scratch/create_carekay_agent.py

import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from django.contrib.auth.models import User
from agents.models import VoiceAgent, AgentRoleTemplate, Industry

def setup_carekay():
    owner = User.objects.first()
    if not owner:
        print("No users found in database. Please register a user first.")
        return

    # Get Industry
    try:
        industry = Industry.objects.get(slug="insurance")
    except Industry.DoesNotExist:
        # Fallback if seed_roles hasn't run
        industry = Industry.objects.create(name="Insurance", slug="insurance")
        print("Industry 'insurance' was not found. Created automatically.")

    # Get the role template we seeded
    try:
        role_template = AgentRoleTemplate.objects.get(
            role_name="Carekay Insurance Advisor",
            industry=industry
        )
    except AgentRoleTemplate.DoesNotExist:
        # Fallback if seed_roles hasn't run
        role_template = AgentRoleTemplate.objects.create(
            role_name="Carekay Insurance Advisor",
            industry=industry,
            description="Carekay Insurance Renewal Reminder and Payment Link Advisor",
            system_prompt_template="Warm female insurance renewal advisor.",
            default_tone="warm",
            default_voice="gu-IN-DhwaniNeural"
        )
        print("Role template 'Carekay Insurance Advisor' was not found. Created automatically.")

    # Create/Get Carekay Agent
    agent, created = VoiceAgent.objects.get_or_create(
        name="Kay",
        owner=owner,
        industry=industry,
        role_template=role_template,
        defaults={
            "company_name": "Carecay Insurance",
            "summary": "Carekay Insurance Renewal reminder bot in Gujarati.",
            "is_active": True
        }
    )
    if not created:
        agent.role_template = role_template
        agent.company_name = "Carecay Insurance"
        agent.summary = "Carekay Insurance Renewal reminder bot in Gujarati."
        agent.save()
        print(f"Carekay agent already exists. Updated details.")
    else:
        print(f"Created new Carekay agent.")

    print("\nCarekay Agent Info:")
    print(f"Agent ID: {agent.id}")
    print(f"Role: {agent.role_template.role_name}")
    print(f"Company: {agent.company_name}")
    print(f"API Key: {agent.api_key}")

if __name__ == "__main__":
    setup_carekay()
