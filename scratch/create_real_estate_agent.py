import os
import sys
import django

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from django.contrib.auth.models import User
from agents.models import Industry, AgentRoleTemplate, VoiceAgent

def create_agent():
    # 1. Fetch User (prefer 'admin', then 'test_admin', then first user)
    owner = User.objects.filter(username="admin").first()
    if not owner:
        owner = User.objects.filter(username="test_admin").first()
    if not owner:
        owner = User.objects.first()
        
    if not owner:
        print("[ERROR] Error: No User found in database. Please create a user first.")
        return

    # 2. Fetch Industry
    industry = Industry.objects.filter(slug="temp-real-estate").first()
    if not industry:
        print("[ERROR] Error: Temp Real Estate Industry not found. Did you run seed_roles?")
        return

    # 3. Fetch Role Template
    role_template = AgentRoleTemplate.objects.filter(
        industry=industry,
        role_name="Naavya JMS Real Estate Advisor"
    ).first()
    
    if not role_template:
        print("[ERROR] Error: Role template 'Naavya JMS Real Estate Advisor' not found. Did you run seed_roles?")
        return

    # 4. Create VoiceAgent
    # Check if already exists
    agent = VoiceAgent.objects.filter(
        owner=owner,
        role_template=role_template
    ).first()

    if agent:
        print(f"[INFO] Voice Agent '{agent.name}' (ID: {agent.id}) already exists for user '{owner.username}'.")
        return agent

    agent = VoiceAgent.objects.create(
        owner=owner,
        industry=industry,
        role_template=role_template,
        name="Naavya Real Estate Advisor",
        company_name="JMS Real Estate",
        summary="Temporary real estate advisor bot for selling flats in Gujarati.",
        is_demo=False,
        is_active=True,
        minutes_quota=5000
    )

    print(f"[OK] Voice Agent '{agent.name}' created successfully!")
    print(f"   ID: {agent.id}")
    print(f"   API Key: {agent.api_key}")
    print(f"   Owner: {agent.owner.username}")
    print(f"   Industry: {agent.industry.name}")
    print(f"   Role: {agent.role_template.role_name}")
    return agent

if __name__ == "__main__":
    create_agent()
