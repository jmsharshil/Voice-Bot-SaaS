# scratch/create_all_remaining_agents.py

import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from django.contrib.auth.models import User
from django.core.management import call_command
from agents.models import Industry, AgentRoleTemplate, VoiceAgent

def main():
    print("--- Seeding Roles ---")
    call_command("seed_roles")

    # 1. Get or Create Owner User
    owner = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if not owner:
        owner = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpassword123"
        )
        print(f"[OK] Created default admin superuser: {owner.username}")

    # Voice Agent configurations
    AGENT_SPECS = [
        {
            "industry_slug": "automobile",
            "role_name": "Automobile Advisor",
            "id": "92edcbdf-1b70-4c7b-a69e-faf15c829860",
            "name": "Aisha Bot",
            "company_name": "Premium Automobile",
            "summary": "Automobile Advisor for customer inquiries",
        },
        {
            "industry_slug": "automobile",
            "role_name": "Naavya Automobile Advisor",
            "name": "Naavya Automobile Advisor",
            "company_name": "Premium Car Showroom",
            "summary": "Warm and enthusiastic automobile consultant",
        },
        {
            "industry_slug": "enogic-commercial-trade",
            "role_name": "Enogic ZED Advisor",
            "name": "Zara",
            "company_name": "ENOGIC COMMERCIAL TRADE PRIVATE LIMITED",
            "summary": "ZED Certification Consultant",
        },
        {
            "industry_slug": "healthcare",
            "role_name": "Hospital Appointment Advisor",
            "name": "Healthcare Advisor",
            "company_name": "City Care Hospital",
            "summary": "Friendly healthcare appointment scheduling assistant",
        },
        {
            "industry_slug": "loans",
            "role_name": "JMS Loan Advisor",
            "name": "JMS Loan Advisor",
            "company_name": "JMS Bank",
            "summary": "Polite and professional loan executive",
        },
        {
            "industry_slug": "reminder-industry",
            "role_name": "JMS Loan Reminder Advisor",
            "name": "JMS Loan Reminder Agent",
            "company_name": "JMS Bank",
            "summary": "તમારી EMI ની તારીખ નજીક છે, તમે ક્યારે ચુકવણી કરશો?",
        },
        {
            "industry_slug": "temp-real-estate",
            "role_name": "Naavya JMS Real Estate Advisor",
            "name": "Naavya Real Estate Advisor",
            "company_name": "JMS Real Estate",
            "summary": "Temporary real estate advisor bot for selling flats in Gujarati.",
        },
        {
            "industry_slug": "samsung-store",
            "role_name": "Naavya Samsung Store Advisor",
            "name": "Naavya Store Bot",
            "company_name": "Vtech Samsung Care",
            "summary": "Friendly customer advisor for Samsung products",
        },
        {
            "industry_slug": "samsung-store",
            "role_name": "Naavya Samsung LLM Advisor",
            "name": "Neel Samsung LLM Bot",
            "company_name": "Vtech Samsung Cafe",
            "summary": "Friendly male customer advisor for Samsung products working on full LLM",
        },
        {
            "industry_slug": "samsung-store",
            "role_name": "Galaxy Z Fold8 Pre-Reserve Advisor",
            "name": "Galaxy Z Fold8 Advisor",
            "company_name": "VTech NxtGen Retails LLP",
            "summary": "Outbound Galaxy Z Fold8 Pre-Reserve campaign advisor",
        },
    ]

    print("\n--- Creating / Updating Voice Agents ---")
    for spec in AGENT_SPECS:
        try:
            industry = Industry.objects.get(slug=spec["industry_slug"])
            role_template = AgentRoleTemplate.objects.get(
                industry=industry,
                role_name=spec["role_name"]
            )
        except (Industry.DoesNotExist, AgentRoleTemplate.DoesNotExist) as e:
            print(f"[ERROR] Skipping {spec['name']}: {e}")
            continue

        agent_id = spec.get("id")
        agent = None

        if agent_id:
            agent = VoiceAgent.objects.filter(id=agent_id).first()

        if not agent:
            agent = VoiceAgent.objects.filter(
                role_template=role_template,
                name=spec["name"]
            ).first()

        if not agent:
            kwargs = {
                "owner": owner,
                "industry": industry,
                "role_template": role_template,
                "name": spec["name"],
                "company_name": spec["company_name"],
                "summary": spec["summary"],
                "is_active": True,
                "is_demo": False,
            }
            if agent_id:
                kwargs["id"] = agent_id
            agent = VoiceAgent.objects.create(**kwargs)
            print(f"[CREATED] {agent.name} | Role: {role_template.role_name} | ID: {agent.id}")
        else:
            agent.owner = owner
            agent.industry = industry
            agent.role_template = role_template
            agent.company_name = spec["company_name"]
            agent.summary = spec["summary"]
            agent.is_active = True
            agent.save()
            print(f"[UPDATED] {agent.name} | Role: {role_template.role_name} | ID: {agent.id}")

    print("\nAll Voice Agents setup completed successfully!")

if __name__ == "__main__":
    main()
