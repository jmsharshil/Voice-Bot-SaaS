# scratch/test_shreyas_bot.py

import os
import sys
import django

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from conversations.services.core.behavior_router import get_role_strategy
from conversations.services.core.dialogue_engine import STRATEGY_MAP, PREPARE_MAP, FINALIZE_MAP, get_agent_tts_language
from shreyas_bot.strategy import shreyas_prepare, shreyas_strategy
from agents.models import VoiceAgent

print("=== Shreyas Bot Tests ===")

# 1. Routing Test
print("\n1. Behavior Router test:")
strategy_key = get_role_strategy("Shreyas Sports Advisor")
print(f"Role 'Shreyas Sports Advisor' maps to: {strategy_key}")
assert strategy_key == "shreyas_strategy", "Strategy mapping failed"
print("OK")

# 2. Registration Test
print("\n2. Dialogue Engine strategy registration test:")
assert "shreyas_strategy" in STRATEGY_MAP, "STRATEGY_MAP registration failed"
assert "shreyas_strategy" in PREPARE_MAP, "PREPARE_MAP registration failed"
assert "shreyas_strategy" in FINALIZE_MAP, "FINALIZE_MAP registration failed"
print("All strategy function maps registered successfully!")
print("OK")

# 3. Strategy Prepare Turn 1 (Greeting)
print("\n3. Prepare Turn 1 (Greeting) Test:")
from django.contrib.auth.models import User
from agents.models import Industry, AgentRoleTemplate
from conversations.models import ConversationSession

user = User.objects.first()
if not user:
    user, _ = User.objects.get_or_create(username="test_admin")

ind, _ = Industry.objects.get_or_create(slug="sports-outreach", defaults={"name": "Sports & Outreach"})
tpl, _ = AgentRoleTemplate.objects.get_or_create(
    role_name="Shreyas Sports Advisor",
    industry=ind,
    defaults={
        "description": "Shreyas Foundation Sports & Outreach Programs Advisor",
        "system_prompt_template": "Welcome prompt",
        "default_tone": "polite",
        "default_voice": "en-IN-AartiNeural"
    }
)
agent, _ = VoiceAgent.objects.get_or_create(
    name="Shreya",
    owner=user,
    industry=ind,
    role_template=tpl,
    defaults={
        "company_name": "Shreyas Foundation",
        "is_active": True
    }
)

session, _ = ConversationSession.objects.get_or_create(
    agent=agent,
    session_id="test_shreyas_session_1"
)
session.state = {}
session.save()

# Turn 1
prep1 = shreyas_prepare(agent, "hello", session)
print(f"Turn 1 Prepare: {prep1}")
assert prep1["static_reply"] == "[PLAY_AUDIO:shreyas_bot/shreyas_step1_greeting.raw]", "Greeting failed"
print("OK")

# Turn 2: Program selection
session.refresh_from_db()
print("\n4. Prepare Turn 2 (Smart Filler check - Program):")
prep2 = shreyas_prepare(agent, "Horse riding sounds fun", session)
print(f"Turn 2 play_filler: {prep2.get('play_filler')}")
assert prep2.get("play_filler") in [f"shreyas_bot/filler_1_{c}.raw" for c in "abcde"], "Should choose program filler"
print("OK")

# Turn 3: Age
session.refresh_from_db()
print("\n5. Prepare Turn 3 (Smart Filler check - Age):")
prep3 = shreyas_prepare(agent, "He is 10 years old", session)
print(f"Turn 3 play_filler: {prep3.get('play_filler')}")
assert prep3.get("play_filler") in [f"shreyas_bot/filler_2_{c}.raw" for c in "abcde"], "Should choose age filler"
print("OK")

# Turn 4: Consent
session.refresh_from_db()
print("\n6. Prepare Turn 4 (Smart Filler check - Consent):")
prep4 = shreyas_prepare(agent, "Yes please, send details", session)
print(f"Turn 4 play_filler: {prep4.get('play_filler')}")
assert prep4.get("play_filler") in [f"shreyas_bot/filler_3_{c}.raw" for c in "abcde"], "Should choose consent filler"
print("OK")

# Turn 5: Question
session.refresh_from_db()
print("\n7. Prepare Turn 5 (Smart Filler check - Question):")
prep5 = shreyas_prepare(agent, "What are the fees?", session)
print(f"Turn 5 play_filler: {prep5.get('play_filler')}")
assert prep5.get("play_filler") in [f"shreyas_bot/filler_4_{c}.raw" for c in "abcde"], "Should choose question filler"
print("OK")

# Turn 6: Default/Fallback
session.refresh_from_db()
print("\n8. Prepare Turn 6 (Smart Filler check - Fallback):")
prep6 = shreyas_prepare(agent, "Hello there", session)
print(f"Turn 6 play_filler: {prep6.get('play_filler')}")
assert prep6.get("play_filler") in [f"shreyas_bot/filler_5_{c}.raw" for c in "abcde"], "Should choose fallback filler"
print("OK")

# Clean up test session
session.delete()
print("\n=== All Tests Passed Successfully ===")
