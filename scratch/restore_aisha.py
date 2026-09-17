import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from agents.models import VoiceAgent, AgentRoleTemplate

aisha_id = "92edcbdf-1b70-4c7b-a69e-faf15c829860"
try:
    aisha = VoiceAgent.objects.get(id=aisha_id)
    if aisha.role_template:
        aisha.role_template.role_name = "Automobile Advisor"
        aisha.role_template.save()
        print(f"Restored Aisha's role to: {aisha.role_template.role_name}")
except Exception as e:
    print(f"Error: {e}")
