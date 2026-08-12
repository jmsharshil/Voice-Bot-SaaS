# scratch/test_kia_syros_bot.py

import os
import sys
import django

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from conversations.services.core.behavior_router import get_role_strategy
from conversations.services.core.dialogue_engine import STRATEGY_MAP, PREPARE_MAP, FINALIZE_MAP
from conversations.models import ConversationSession
from agents.models import VoiceAgent

def test_router():
    print("\n1. Behavior Router test:")
    strategy = get_role_strategy("Kia Syros EV Advisor")
    print(f"Role 'Kia Syros EV Advisor' maps to: {strategy}")
    assert strategy == "kia_syros_strategy", f"Expected 'kia_syros_strategy', got '{strategy}'"
    print("OK")

def test_strategy_maps():
    print("\n2. Dialogue Engine strategy registration test:")
    assert "kia_syros_strategy" in STRATEGY_MAP, "kia_syros_strategy not in STRATEGY_MAP"
    assert "kia_syros_strategy" in PREPARE_MAP, "kia_syros_strategy not in PREPARE_MAP"
    assert "kia_syros_strategy" in FINALIZE_MAP, "kia_syros_strategy not in FINALIZE_MAP"
    print("All strategy function maps registered successfully!")
    print("OK")

def test_greeting():
    print("\n3. Prepare Turn 1 (Greeting) Test:")
    agent = VoiceAgent.objects.first()
    session = ConversationSession.objects.get_or_create(
        agent=agent, session_id="test_kia_session_123"
    )[0]
    session.state = {}
    session.save()

    from kia_syros_bot.strategy import kia_syros_prepare
    result = kia_syros_prepare(agent, "initial", session, detected_language="hi")
    print(f"Turn 1 Prep result (Greeting): {result}")
    assert "static_reply" in result, "Expected static_reply for greeting"
    assert "क्या मेरी बात" in result["static_reply"], "Greeting text mismatch"
    print("OK")

def test_identity_confirm_mp3():
    print("\n4. Prepare Turn 2 (Identity Confirm → MP3 Pitch) Test:")
    agent = VoiceAgent.objects.first()
    session = ConversationSession.objects.get_or_create(
        agent=agent, session_id="test_kia_session_123"
    )[0]
    session.state = {
        "intro_shown": True,
        "call_phase": "GREETING_REPLY",
        "conversation_history": ["Agent: Hello, क्या मेरी बात आप से हो रही है?"]
    }
    session.save()

    from kia_syros_bot.strategy import kia_syros_prepare
    result = kia_syros_prepare(agent, "Haan main bol raha hoon", session, detected_language="hi")
    print(f"Turn 2 Prep result: {result}")
    
    assert "static_reply" in result, "Expected static_reply (MP3 match) for identity confirmation"
    assert "PLAY_AUDIO" in result["static_reply"], "Expected PLAY_AUDIO tag in response"
    assert "kia_syros_pitch" in result["static_reply"], f"Expected pitch audio file, got: {result['static_reply']}"
    print("OK")

def test_agree_pitch_mp3():
    print("\n5. Prepare Turn 3 (Agree → MP3 Callback Confirm) Test:")
    agent = VoiceAgent.objects.first()
    session = ConversationSession.objects.get_or_create(
        agent=agent, session_id="test_kia_session_123"
    )[0]
    session.state = {
        "intro_shown": True,
        "call_phase": "PITCH_REPLY",
        "conversation_history": [
            "Agent: Hello, क्या मेरी बात आप से हो रही है?",
            "User: Haan main bol raha hoon",
            "Agent: [Pitch]"
        ],
        "exchange_count": 1
    }
    session.save()

    from kia_syros_bot.strategy import kia_syros_prepare
    result = kia_syros_prepare(agent, "Haan interested hoon", session, detected_language="hi")
    print(f"Turn 3 Prep result: {result}")

    assert "static_reply" in result, "Expected static_reply (MP3 match) for agree"
    assert "PLAY_AUDIO" in result["static_reply"], "Expected PLAY_AUDIO tag"
    assert "callback_confirm" in result["static_reply"], f"Expected callback_confirm audio, got: {result['static_reply']}"
    print("OK")

def test_details_redirect_mp3():
    print("\n6. Prepare (Ask Details → MP3 Redirect) Test:")
    agent = VoiceAgent.objects.first()
    session = ConversationSession.objects.get_or_create(
        agent=agent, session_id="test_kia_session_123"
    )[0]
    session.state = {
        "intro_shown": True,
        "call_phase": "PITCH_REPLY",
        "conversation_history": [],
        "exchange_count": 1
    }
    session.save()

    from kia_syros_bot.strategy import kia_syros_prepare
    result = kia_syros_prepare(agent, "price kya hai Syros ki?", session, detected_language="hi")
    print(f"Details redirect result: {result}")

    assert "static_reply" in result, "Expected static_reply for details inquiry"
    assert "redirect" in result["static_reply"], f"Expected redirect audio, got: {result['static_reply']}"
    print("OK")

def test_rejection_mp3():
    print("\n7. Prepare (Rejection → MP3 Close) Test:")
    agent = VoiceAgent.objects.first()
    session = ConversationSession.objects.get_or_create(
        agent=agent, session_id="test_kia_session_123"
    )[0]
    session.state = {
        "intro_shown": True,
        "call_phase": "PITCH_REPLY",
        "conversation_history": [],
        "exchange_count": 1
    }
    session.save()

    from kia_syros_bot.strategy import kia_syros_prepare
    result = kia_syros_prepare(agent, "nahi chahiye mujhe", session, detected_language="hi")
    print(f"Rejection result: {result}")

    assert "static_reply" in result, "Expected static_reply for rejection"
    assert "rejection" in result["static_reply"], f"Expected rejection audio, got: {result['static_reply']}"
    assert "END_CALL" in result["static_reply"], "Expected END_CALL tag"
    assert result.get("auto_disconnect") == True, "Expected auto_disconnect for closing"
    print("OK")

def test_llm_fallback():
    print("\n8. Prepare (Unrecognized → LLM Fallback) Test:")
    agent = VoiceAgent.objects.first()
    session = ConversationSession.objects.get_or_create(
        agent=agent, session_id="test_kia_session_123"
    )[0]
    session.state = {
        "intro_shown": True,
        "call_phase": "PITCH_REPLY",
        "conversation_history": [],
        "exchange_count": 1
    }
    session.save()

    from kia_syros_bot.strategy import kia_syros_prepare
    result = kia_syros_prepare(agent, "meri gaadi ka insurance kab khatam ho raha hai?", session, detected_language="hi")
    print(f"LLM fallback result keys: {list(result.keys())}")

    assert "system_prompt" in result, "Expected system_prompt for LLM fallback"
    assert "user_message" in result, "Expected user_message for LLM fallback"
    assert "static_reply" not in result, "Should NOT have static_reply for LLM fallback"
    print("OK")

def test_intent_matcher():
    print("\n9. Intent Matcher Direct Tests:")
    from kia_syros_bot.strategy import get_kia_syros_matcher
    matcher = get_kia_syros_matcher()
    assert matcher is not None, "Matcher should load"

    # Test GREETING_REPLY → confirm identity
    result = matcher.find_match("haan ji bol raha hoon", current_phase="GREETING_REPLY", threshold=0.70)
    print(f"  'haan ji bol raha hoon' (GREETING_REPLY) -> {result.get('match_type')}: {result.get('mp3', 'N/A')}")
    assert result["match_type"] != "NONE", "Should match confirm_identity"

    # Test PITCH_REPLY → interested
    result = matcher.find_match("haan interested hoon", current_phase="PITCH_REPLY", threshold=0.70)
    print(f"  'haan interested hoon' (PITCH_REPLY) -> {result.get('match_type')}: {result.get('mp3', 'N/A')}")
    assert result["match_type"] != "NONE", "Should match agree_interested"

    # Test PITCH_REPLY → price inquiry
    result = matcher.find_match("price kya hai", current_phase="PITCH_REPLY", threshold=0.70)
    print(f"  'price kya hai' (PITCH_REPLY) -> {result.get('match_type')}: {result.get('mp3', 'N/A')}")
    assert result["match_type"] != "NONE", "Should match ask_details"

    # Test CALLBACK_REPLY → confirm same number
    result = matcher.find_match("haan isi number par call karo", current_phase="CALLBACK_REPLY", threshold=0.70)
    print(f"  'haan isi number par' (CALLBACK_REPLY) -> {result.get('match_type')}: {result.get('mp3', 'N/A')}")
    assert result["match_type"] != "NONE", "Should match confirm_same_number"

    print("OK")


if __name__ == "__main__":
    print("=== Kia Syros Bot Tests (MP3-First) ===")
    test_router()
    test_strategy_maps()
    test_greeting()
    test_identity_confirm_mp3()
    test_agree_pitch_mp3()
    test_details_redirect_mp3()
    test_rejection_mp3()
    test_llm_fallback()
    test_intent_matcher()
    print("\n✅ All Kia Syros MP3-First strategy tests passed!")
