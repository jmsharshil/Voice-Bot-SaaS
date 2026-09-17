import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from agents.models import VoiceAgent

agent_id = "92edcbdf-1b70-4c7b-a69e-faf15c829860"
try:
    agent = VoiceAgent.objects.get(id=agent_id)
    role_name = agent.role_template.role_name if agent.role_template else "No Role"
    print(f"Current Agent Name: {agent.name}")
    print(f"Current Agent Role: {role_name}")
except VoiceAgent.DoesNotExist:
    print(f"Agent with ID {agent_id} not found.")
