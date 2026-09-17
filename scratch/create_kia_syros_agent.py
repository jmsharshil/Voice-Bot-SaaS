# scratch/create_kia_syros_agent.py

import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from django.contrib.auth.models import User
from agents.models import VoiceAgent, AgentRoleTemplate, Industry
from kia_syros_bot.prompts import KIA_SYROS_SYSTEM_PROMPT

def setup_kia_syros():
    # Get or create default admin/superuser
    owner = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if not owner:
        owner = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpassword123"
        )
        print(f"[OK] Created default admin superuser: {owner.username}")

    # 1. Create or get Automobile Industry
    industry, created = Industry.objects.get_or_create(
        slug="automobile",
        defaults={
            "name": "Automobile",
        }
    )
    if created:
        print("Created new Industry: Automobile")
    else:
        print("Industry 'automobile' already exists.")

    # 2. Create or get Role Template
    role_template, created = AgentRoleTemplate.objects.get_or_create(
        role_name="Kia Syros EV Advisor",
        industry=industry,
        defaults={
            "description": "Westcoast Kia Sales Advisor for the all-new Kia Syros EV in Hinglish/Hindi",
            "system_prompt_template": KIA_SYROS_SYSTEM_PROMPT,
            "default_tone": "warm",
            "default_voice": "hi-IN-SwaraNeural"
        }
    )
    if created:
        print("Created new AgentRoleTemplate: Kia Syros EV Advisor")
    else:
        # Update template prompt just in case it changed
        role_template.system_prompt_template = KIA_SYROS_SYSTEM_PROMPT
        role_template.description = "Westcoast Kia Sales Advisor for the all-new Kia Syros EV in Hinglish/Hindi"
        role_template.save()
        print("Updated existing AgentRoleTemplate: Kia Syros EV Advisor")

    # 3. Create or get Kia Agent
    agent, created = VoiceAgent.objects.get_or_create(
        name="Kia Syros Bot",
        owner=owner,
        industry=industry,
        role_template=role_template,
        defaults={
            "company_name": "Westcoast Kia",
            "summary": "Voice bot for Westcoast Kia promoting the all-new Kia Syros EV.",
            "is_active": True
        }
    )
    if created:
        print(f"Created new VoiceAgent: {agent.name} (ID: {agent.id})")
    else:
        agent.role_template = role_template
        agent.company_name = "Westcoast Kia"
        agent.summary = "Voice bot for Westcoast Kia promoting the all-new Kia Syros EV."
        agent.save()
        print(f"Updated existing VoiceAgent: {agent.name} (ID: {agent.id})")

    print("\n--- Kia Syros Agent Setup Completed ---")
    print(f"Agent ID: {agent.id}")
    print(f"Agent Name: {agent.name}")
    print(f"Role: {agent.role_template.role_name}")
    print(f"Company: {agent.company_name}")
    print(f"API Key: {agent.api_key}")

if __name__ == "__main__":
    setup_kia_syros()
