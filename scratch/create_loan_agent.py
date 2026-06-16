import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from django.contrib.auth.models import User
from agents.models import VoiceAgent, AgentRoleTemplate, Industry

def setup_loan_agent():
    try:
        # Get owner (first user)
        owner = User.objects.first()
        if not owner:
            print("No users found in database to assign as agent owner.")
            return
        
        # Get industry 'loans'
        industry = Industry.objects.get(slug="loans")
    except Industry.DoesNotExist:
        print("Industry 'loans' not found. Please run seed_roles first.")
        return

    # Get the role template we seeded
    try:
        role_template = AgentRoleTemplate.objects.get(
            role_name="JMS Loan Advisor",
            industry=industry
        )
    except AgentRoleTemplate.DoesNotExist:
        print("Role template 'JMS Loan Advisor' not found. Please run seed_roles first.")
        return

    # Get or create JMS Loan Advisor agent
    loan_agent, created = VoiceAgent.objects.get_or_create(
        name="JMS Loan Advisor",
        owner=owner,
        industry=industry,
        defaults={
            "role_template": role_template,
            "company_name": "JMS Bank",
            "summary": "Polite and professional loan executive",
            "is_active": True
        }
    )
    
    if not created:
        loan_agent.role_template = role_template
        loan_agent.company_name = "JMS Bank"
        loan_agent.save()
        print(f"JMS Loan Advisor agent already exists. Updated role and company details.")
    else:
        print(f"Created new JMS Loan Advisor agent.")

    print("\nJMS Loan Advisor Agent Info:")
    print(f"Agent ID: {loan_agent.id}")
    print(f"API Key: {loan_agent.api_key}")
    print(f"Role: {loan_agent.role_template.role_name}")
    print(f"Company: {loan_agent.company_name}")

if __name__ == "__main__":
    setup_loan_agent()
