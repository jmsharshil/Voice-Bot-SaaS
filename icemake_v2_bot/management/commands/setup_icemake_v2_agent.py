from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from agents.models import Industry, AgentRoleTemplate, VoiceAgent

class Command(BaseCommand):
    help = "Creates or verifies the Ice Make Voice Agent V2 (11-step script) in the database."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🚀 Setting up ICEMAKE Voice Agent V2 in database..."))

        # 1. Owner User
        owner = User.objects.first()
        if not owner:
            owner = User.objects.create_superuser("admin", "admin@example.com", "admin123")
            self.stdout.write(self.style.SUCCESS("👤 Created default superuser: admin"))

        # 2. Industry
        industry, _ = Industry.objects.get_or_create(
            slug="cold-room-refrigeration",
            defaults={"name": "Cold Room Refrigeration"}
        )

        # 3. Agent Role Template
        role_template, created_rt = AgentRoleTemplate.objects.get_or_create(
            role_name="Ice Make Cold Room Support V2",
            defaults={
                "industry": industry,
                "description": "24x7 Female Breakdown & Serial-Number Verified Support Agent for ICEMAKE Refrigeration Ltd.",
                "system_prompt_template": (
                    "You are a female customer support voice assistant for Ice Make Refrigeration Limited.\n"
                    "Always speak in a polite, professional female voice and use feminine verb forms in Hindi (e.g. सकती हूँ, करूँगी, समझ गई).\n"
                    "Register breakdown complaints with pincode verification and product serial number."
                ),
                "default_tone": "professional",
                "default_voice": "en-IN-NeerjaNeural",
            }
        )
        if not created_rt:
            role_template.description = "24x7 Female Breakdown & Serial-Number Verified Support Agent for ICEMAKE Refrigeration Ltd."
            role_template.system_prompt_template = (
                "You are a female customer support voice assistant for Ice Make Refrigeration Limited.\n"
                "Always speak in a polite, professional female voice and use feminine verb forms in Hindi (e.g. सकती हूँ, करूँगी, समझ गई).\n"
                "Register breakdown complaints with pincode verification and product serial number."
            )
            role_template.default_voice = "en-IN-NeerjaNeural"
            role_template.save()

        # 4. Voice Agent
        agent, created_agent = VoiceAgent.objects.get_or_create(
            name="Ice Make Support Agent V2",
            defaults={
                "owner": owner,
                "industry": industry,
                "role_template": role_template,
                "company_name": "Ice Make Refrigeration Limited",
                "summary": "24x7 Customer Support Voice Agent that registers breakdown complaints with address verification and machine serial number."
            }
        )
        if not created_agent:
            agent.role_template = role_template
            agent.company_name = "Ice Make Refrigeration Limited"
            agent.save()

        self.stdout.write(self.style.SUCCESS(f"✅ SUCCESS! Ice Make Voice Agent V2 is ready! (ID: {agent.id}, Name: '{agent.name}')"))
