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
from agents.models import Industry, AgentRoleTemplate, VoiceAgent

def create_priya_naavya_voice_agent():
    print("🚀 Creating/Seeding PRIYA NAAVYA Voice Agent in database...")

    # 1. Owner User
    owner = User.objects.first()
    if not owner:
        owner = User.objects.create_superuser("admin", "admin@example.com", "admin123")
        print("👤 Created default superuser: admin")

    # 2. Industry
    industry, created_ind = Industry.objects.get_or_create(
        slug="real-estate",
        defaults={"name": "Real Estate"}
    )
    if created_ind:
        print(f"🏭 Created Industry: {industry.name}")
    else:
        print(f"🏭 Industry '{industry.name}' already exists.")

    # 3. Agent Role Template
    role_template, created_rt = AgentRoleTemplate.objects.get_or_create(
        role_name="Priya Naavya AI Advisor",
        defaults={
            "industry": industry,
            "description": "Outbound Property Lead Sales & Qualification Agent for Naavya.ai",
            "system_prompt_template": (
                "You are Priya from Naavya.ai, speaking to property lead buyers/investors.\n"
                "Qualify leads for real estate requirements and MSME property services."
            ),
            "default_tone": "persuasive",
            "default_voice": "hi-IN-SwaraNeural",
        }
    )
    if created_rt:
        print(f"📋 Created Role Template: {role_template.role_name}")
    else:
        print(f"📋 Role Template '{role_template.role_name}' already exists.")

    # 4. Voice Agent
    agent, created_agent = VoiceAgent.objects.get_or_create(
        name="Priya Naavya AI Sales Agent",
        defaults={
            "owner": owner,
            "industry": industry,
            "role_template": role_template,
            "company_name": "Naavya.ai",
            "summary": "Outbound property lead qualification assistant calling clients to qualify property requirements."
        }
    )
    if created_agent:
        print(f"🎉 SUCCESS! Created Voice Agent '{agent.name}' (ID: {agent.id})")
    else:
        agent.role_template = role_template
        agent.company_name = "Naavya.ai"
        agent.save()
        print(f"✅ SUCCESS! Verified/Updated Voice Agent '{agent.name}' (ID: {agent.id})")

    return agent

if __name__ == "__main__":
    create_priya_naavya_voice_agent()
