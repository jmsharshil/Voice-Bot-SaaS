# scratch/create_raahi_iiiem_agent.py

import os
import sys
import django

# Setup Django Environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from django.contrib.auth.models import User
from agents.models import VoiceAgent, AgentRoleTemplate, Industry
from raahi_iiiem_bot.prompts import RAAHI_IIIEM_SYSTEM_PROMPT

def setup_raahi_iiiem_agent():
    print("==================================================")
    print("  CREATING / UPDATING RAAHI iiiEM VOICE AGENT")
    print("==================================================")

    # 1. Get or create Superuser Owner
    owner = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if not owner:
        owner = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpassword123"
        )
        print(f"[OK] Created superuser owner: {owner.username}")
    else:
        print(f"[OK] Found owner user: {owner.username}")

    # 2. Get or create Education / Training Industry
    industry, created = Industry.objects.get_or_create(
        slug="education-training",
        defaults={
            "name": "Education & Training",
        }
    )
    if created:
        print("[OK] Created Industry: Education & Training")
    else:
        print("[OK] Found existing Industry: Education & Training")

    # 3. Create or update Agent Role Template
    role_template = AgentRoleTemplate.objects.filter(role_name__icontains="Raahi").first()
    if not role_template:
        role_template = AgentRoleTemplate.objects.create(
            role_name="Raahi iiiEM Export Advisor",
            industry=industry,
            description="Voice agent Raahi for Triple i E M Export Import Training Institute.",
            system_prompt_template=RAAHI_IIIEM_SYSTEM_PROMPT,
            default_tone="friendly",
            default_voice="hi-IN-AartiNeural"
        )
        print("[OK] Created AgentRoleTemplate: Raahi iiiEM Export Advisor")
    else:
        role_template.industry = industry
        role_template.system_prompt_template = RAAHI_IIIEM_SYSTEM_PROMPT
        role_template.description = "Voice agent Raahi for Triple i E M Export Import Training Institute."
        role_template.default_voice = "hi-IN-AartiNeural"
        role_template.save()
        print("[OK] Updated existing AgentRoleTemplate: Raahi iiiEM Export Advisor")

    # 4. Create or update Voice Agent
    agent = VoiceAgent.objects.filter(name__icontains="Raahi").first()
    if not agent:
        agent = VoiceAgent.objects.create(
            name="Raahi - iiiEM Export Bot",
            owner=owner,
            industry=role_template.industry,
            role_template=role_template,
            company_name="Triple i E M",
            summary="Voice agent Raahi for Triple i E M Export Import Training Institute.",
            is_active=True
        )
        print(f"[OK] Created VoiceAgent: {agent.name}")
    else:
        agent.industry = role_template.industry
        agent.role_template = role_template
        agent.company_name = "Triple i E M"
        agent.summary = "Voice agent Raahi for Triple i E M Export Import Training Institute."
        agent.is_active = True
        agent.save()
        print(f"[OK] Updated existing VoiceAgent: {agent.name}")

    print("\n==================================================")
    print("  RAAHI iiiEM AGENT SETUP COMPLETED SUCCESSFULLY!")
    print("==================================================")
    print(f"Agent Name   : {agent.name}")
    print(f"Agent ID     : {agent.id}")
    print(f"Role Name    : {agent.role_template.role_name}")
    print(f"Company Name : {agent.company_name}")
    print(f"API Key      : {agent.api_key}")
    print(f"WebSocket URL: ws://YOUR_SERVER_IP:8000/ws/voice-bot/service2/?agent_id={agent.id}")
    print("==================================================")

if __name__ == "__main__":
    setup_raahi_iiiem_agent()
