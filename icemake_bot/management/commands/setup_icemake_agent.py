from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from agents.models import Industry, AgentRoleTemplate, VoiceAgent

class Command(BaseCommand):
    help = "Creates or verifies the single unified Ice Make Voice Agent in the database."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🚀 Setting up ICEMAKE Voice Agent in database..."))

        # 1. Owner User
        owner = User.objects.first()
        if not owner:
            owner = User.objects.create_superuser("admin", "admin@example.com", "admin123")
            self.stdout.write(self.style.SUCCESS("👤 Created default superuser: admin"))

        # 2. Industry
        industry, created_ind = Industry.objects.get_or_create(
            slug="cold-room-refrigeration",
            defaults={"name": "Cold Room Refrigeration"}
        )

        # 3. Agent Role Template
        role_template, created_rt = AgentRoleTemplate.objects.get_or_create(
            role_name="Ice Make Cold Room Support",
            defaults={
                "industry": industry,
                "description": "24x7 After-Hours Cold Room Support Agent for ICEMAKE Refrigeration LTD.",
                "system_prompt_template": (
                    "You are Aaisha, a 24x7 Cold Room Support Agent for ICEMAKE Refrigeration Ltd.\n"
                    "Help customers register complaints about Chillers, Freezers, and Blast Freezers."
                ),
                "default_tone": "professional",
                "default_voice": "hi-IN-SwaraNeural",
            }
        )

        # 4. Voice Agent
        agent, created_agent = VoiceAgent.objects.get_or_create(
            name="Ice Make Support Agent",
            defaults={
                "owner": owner,
                "industry": industry,
                "role_template": role_template,
                "company_name": "ICEMAKE Refrigeration Ltd.",
                "summary": "24x7 After-Hours Cold Room Support Agent that logs chiller and freezer complaints and registers tickets."
            }
        )
        if not created_agent:
            agent.role_template = role_template
            agent.company_name = "ICEMAKE Refrigeration Ltd."
            agent.save()

        self.stdout.write(self.style.SUCCESS(f"✅ SUCCESS! Ice Make Voice Agent is ready! (ID: {agent.id}, Name: '{agent.name}')"))
