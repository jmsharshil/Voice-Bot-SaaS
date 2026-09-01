# scratch/test_raahi_bot.py

import os
import sys
import django
import uuid

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from agents.models import VoiceAgent
from conversations.models import ConversationSession
from raahi_iiiem_bot.strategy import raahi_iiiem_strategy, raahi_iiiem_prepare, raahi_iiiem_finalize

def test_raahi_clean_llm():
    agent = VoiceAgent.objects.filter(name__icontains="Raahi").first()
    if not agent:
        print("Creating mock Raahi agent for test...")
        agent = VoiceAgent.objects.create(name="Raahi - Triple i E M", company_name="Triple i E M")

    session_id = f"test_raahi_clean_{uuid.uuid4().hex[:8]}"
    session, _ = ConversationSession.objects.get_or_create(
        agent=agent,
        session_id=session_id
    )
    session.state = {"intro_shown": True, "stage": "STAGE_1_GREET", "customer_name": "Ayushi"}
    session.save()

    # Test raw prepare execution
    msg = "ETP plan ka price aur details kya hai?"
    prep = raahi_iiiem_prepare(agent, msg, session)
    print("System Prompt Length:", len(prep["system_prompt"]))
    print("User Message Passed:", prep["user_message"])
    assert "CUSTOMER NAME RULE – DO NOT REPEAT NAME" in prep["system_prompt"], "System prompt must contain DO NOT REPEAT NAME rule!"
    assert "PLAN INFO FIRST vs PRICE SECOND RULE" in prep["system_prompt"], "System prompt must contain PLAN INFO FIRST rule!"
    assert "NO WHATSAPP OFFER RULE" in prep["system_prompt"], "System prompt must contain NO WHATSAPP OFFER rule!"
    assert "SINGLE AGENT INTRODUCTION RULE" in prep["system_prompt"], "System prompt must contain SINGLE AGENT INTRODUCTION rule!"
    print("✅ Clean Raahi Master Prompt v3.1 & RAG Strategy Execution Test Passed!")

if __name__ == "__main__":
    test_raahi_clean_llm()
