import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from django.contrib.auth.models import User
from django.core.management import call_command
from agents.models import Industry, AgentRoleTemplate, VoiceAgent

def setup_carekay_agent():
    print("--- Seeding Roles & Industries ---")
    call_command("seed_roles")

    print("\n--- Creating / Updating Carekay Insurance Agent ---")
    try:
        industry = Industry.objects.get(slug="carekay-insurance")
    except Industry.DoesNotExist:
        industry = Industry.objects.create(name="Carekay Insurance", slug="carekay-insurance")

    role_template, _ = AgentRoleTemplate.objects.get_or_create(
        industry=industry,
        role_name="Carekay Gujarati Insurance Renewal Advisor",
        defaults={
            "description": "Outbound Motor Insurance Renewal campaign advisor in Gujarati",
            "system_prompt_template": "Carekay System Prompt",
            "default_voice": "gu-IN-DhwaniNeural"
        }
    )

    users = User.objects.all()
    if not users:
        print("[ERROR] No user found in database.")
        return

    for user in users:
        agent, created = VoiceAgent.objects.get_or_create(
            name="Kay Carekay Insurance",
            owner=user,
            industry=industry,
            defaults={
                "role_template": role_template,
                "company_name": "Carekay Insurance",
                "summary": "Outbound Motor Insurance Renewal campaign advisor in Gujarati",
                "is_active": True
            }
        )

        agent.role_template = role_template
        agent.company_name = "Carekay Insurance"
        agent.summary = "Outbound Motor Insurance Renewal campaign advisor in Gujarati"
        agent.is_active = True
        agent.save()
        print(f"✅ Carekay Agent Synced for '{user.username}': ID={agent.id}, Name='{agent.name}'")

if __name__ == "__main__":
    setup_carekay_agent()
