# scratch/create_shreyas_agent.py

import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from django.contrib.auth.models import User
from agents.models import VoiceAgent, AgentRoleTemplate, Industry
from shreyas_bot.prompts import SHREYAS_SYSTEM_PROMPT

def setup_shreyas():
    # Get or create default admin/superuser
    owner = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if not owner:
        owner = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpassword123"
        )
        print(f"[OK] Created default admin superuser: {owner.username}")

    # 1. Create or get Sports & Outreach Industry
    industry, created = Industry.objects.get_or_create(
        slug="sports-outreach",
        defaults={
            "name": "Sports & Outreach",
        }
    )
    if created:
        print("Created new Industry: Sports & Outreach")
    else:
        print("Industry 'sports-outreach' already exists.")

    # 2. Create or get Role Template
    role_template, created = AgentRoleTemplate.objects.get_or_create(
        role_name="Shreyas Sports Advisor",
        industry=industry,
        defaults={
            "description": "Shreyas Foundation Sports & Outreach Programs Advisor",
            "system_prompt_template": SHREYAS_SYSTEM_PROMPT,
            "default_tone": "polite",
            "default_voice": "en-IN-AartiNeural"
        }
    )
    if created:
        print("Created new AgentRoleTemplate: Shreyas Sports Advisor")
    else:
        # Update template prompt just in case it changed
        role_template.system_prompt_template = SHREYAS_SYSTEM_PROMPT
        role_template.description = "Shreyas Foundation Sports & Outreach Programs Advisor"
        role_template.save()
        print("Updated existing AgentRoleTemplate: Shreyas Sports Advisor")

    # 3. Create or get Shreyas Agent
    agent, created = VoiceAgent.objects.get_or_create(
        name="Shreya",
        owner=owner,
        industry=industry,
        role_template=role_template,
        defaults={
            "company_name": "Shreyas Foundation",
            "summary": "Voice bot for Shreyas Foundation Sports & Outreach Programs.",
            "is_active": True
        }
    )
    if created:
        print(f"Created new VoiceAgent: {agent.name} (ID: {agent.id})")
    else:
        agent.role_template = role_template
        agent.company_name = "Shreyas Foundation"
        agent.summary = "Voice bot for Shreyas Foundation Sports & Outreach Programs."
        agent.save()
        print(f"Updated existing VoiceAgent: {agent.name} (ID: {agent.id})")

    print("\n--- Shreyas Agent Setup Completed ---")
    print(f"Agent ID: {agent.id}")
    print(f"Agent Name: {agent.name}")
    print(f"Role: {agent.role_template.role_name}")
    print(f"Company: {agent.company_name}")
    print(f"API Key: {agent.api_key}")

if __name__ == "__main__":
    setup_shreyas()
