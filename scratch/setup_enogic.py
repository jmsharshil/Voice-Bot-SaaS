import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from django.contrib.auth.models import User
from agents.models import VoiceAgent, AgentRoleTemplate, Industry

def setup_enogic():
    try:
        # Get first user as owner
        owner = User.objects.filter(is_superuser=True).first() or User.objects.first()
        if not owner:
            print("[ERROR] No users found in database. Please register a user first.")
            return
            
        # Get the enogic industry
        try:
            industry = Industry.objects.get(slug="enogic-commercial-trade")
        except Industry.DoesNotExist:
            print("[ERROR] Industry 'enogic-commercial-trade' not found. Please run seed_roles first.")
            return

        # Get the role template we seeded
        try:
            role_template = AgentRoleTemplate.objects.get(
                role_name="Enogic ZED Advisor",
                industry=industry
            )
        except AgentRoleTemplate.DoesNotExist:
            print("[ERROR] Role template 'Enogic ZED Advisor' not found. Please run seed_roles first.")
            return

        # Get or create Zara agent
        zara_agent, created = VoiceAgent.objects.get_or_create(
            name="Zara",
            owner=owner,
            industry=industry,
            defaults={
                "role_template": role_template,
                "company_name": "ENOGIC COMMERCIAL TRADE PRIVATE LIMITED",
                "summary": "ZED Certification Consultant",
                "is_active": True
            }
        )
        
        if not created:
            zara_agent.role_template = role_template
            zara_agent.company_name = "ENOGIC COMMERCIAL TRADE PRIVATE LIMITED"
            zara_agent.summary = "ZED Certification Consultant"
            zara_agent.save()
            print(f"Zara agent already exists. Updated her role to Enogic ZED Advisor.")
        else:
            print(f"Created new Zara agent with role Enogic ZED Advisor.")

        print("\nZara Agent Info:")
        print(f"Agent ID: {zara_agent.id}")
        print(f"API Key: {zara_agent.api_key}")
        print(f"Role: {zara_agent.role_template.role_name}")
        print(f"Company: {zara_agent.company_name}")

    except Exception as e:
        print(f"[ERROR] Exception during setup: {e}")

if __name__ == "__main__":
    setup_enogic()
