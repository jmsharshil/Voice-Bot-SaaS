# scratch/test_raahi_outbound_greeting.py

import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from agents.models import VoiceAgent
from conversations.services.core.behavior_router import get_role_strategy
from bot.views import pre_synthesize_greeting

def test_raahi_outbound_greeting():
    agent = VoiceAgent.objects.filter(name__icontains="Raahi").first()
    assert agent is not None, "Raahi agent must exist!"
    
    role_name = agent.role_template.role_name if agent.role_template else ""
    strategy_key = get_role_strategy(role_name)
    print(f"Agent Name  : {agent.name}")
    print(f"Role Name   : {role_name}")
    print(f"Strategy Key: {strategy_key}")
    assert strategy_key == "raahi_iiiem_strategy", f"Strategy key must be 'raahi_iiiem_strategy', got {strategy_key}"
    
    test_phone = "9998887776"
    pre_synthesize_greeting(str(agent.id), test_phone, name="Ayushi", language="hi")
    
    raw_path = os.path.join("mp3_responses", f"pre_synthesized_{agent.id}_{test_phone}.raw")
    print(f"Checking pre-synthesized audio file: {raw_path}")
    assert os.path.exists(raw_path), "Pre-synthesized raw file should be created!"
    file_size = os.path.getsize(raw_path)
    print(f"Pre-synthesized audio file size: {file_size} bytes")
    assert file_size > 0, "Audio file should not be empty!"
    print("SUCCESS: Raahi outbound pre-synthesized greeting test passed!")

if __name__ == "__main__":
    test_raahi_outbound_greeting()
