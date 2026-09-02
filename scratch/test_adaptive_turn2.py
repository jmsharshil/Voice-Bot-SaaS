# scratch/test_adaptive_turn2.py
import os
import sys
import django
import uuid

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from agents.models import VoiceAgent
from conversations.models import ConversationSession
from raahi_iiiem_bot.strategy import raahi_iiiem_prepare

def test_adaptive_turn2():
    agent = VoiceAgent.objects.filter(name__icontains="Raahi").first()
    session_id = f"test_adaptive_{uuid.uuid4().hex[:8]}"
    session, _ = ConversationSession.objects.get_or_create(
        agent=agent,
        session_id=session_id
    )

    # Turn 1: Opening
    t1 = raahi_iiiem_prepare(agent, "", session)
    print("Turn 1 Opening Line:", t1.get("static_reply"))
    assert "Hi, I am Raahi calling from Triple i E M, how can I help you today?" in t1.get("static_reply")

    # Turn 2: User responds with specific business: "mera ek toys business hai mujhe abb usse export krna hai"
    user_input = "Mera ek toys business hai, mujhe ab usse export karna hai."
    t2 = raahi_iiiem_prepare(agent, user_input, session)
    
    print("\nTurn 2 System Prompt Generated Length:", len(t2.get("system_prompt")))
    print("Turn 2 User Message Passed:", t2.get("user_message"))
    assert "ADAPTIVE TURN 2 RESPONSE RULE" in t2.get("system_prompt"), "System prompt must contain ADAPTIVE TURN 2 RULE!"
    assert t2.get("user_message") == user_input, "User message must be passed correctly!"

    print("\n✅ ADAPTIVE BUSINESS TURN 2 TEST PASSED 100%!")

if __name__ == "__main__":
    test_adaptive_turn2()
