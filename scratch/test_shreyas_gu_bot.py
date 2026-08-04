# scratch/test_shreyas_gu_bot.py

import os
import sys
import django

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from conversations.services.core.behavior_router import get_role_strategy
from conversations.services.core.dialogue_engine import STRATEGY_MAP, PREPARE_MAP, FINALIZE_MAP
from shreyas_gu_bot.strategy import shreyas_gu_prepare
from agents.models import VoiceAgent

print("=== Shreyas Gujarati Bot Tests ===")

# 1. Routing Test
print("\n1. Behavior Router test:")
strategy_key = get_role_strategy("Shreyas Sports Advisor Gujarati")
print(f"Role 'Shreyas Sports Advisor Gujarati' maps to: {strategy_key}")
assert strategy_key == "shreyas_gu_strategy", "Strategy mapping failed"
print("OK")

# 2. Registration Test
print("\n2. Dialogue Engine strategy registration test:")
assert "shreyas_gu_strategy" in STRATEGY_MAP, "STRATEGY_MAP registration failed"
assert "shreyas_gu_strategy" in PREPARE_MAP, "PREPARE_MAP registration failed"
assert "shreyas_gu_strategy" in FINALIZE_MAP, "FINALIZE_MAP registration failed"
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
    role_name="Shreyas Sports Advisor Gujarati",
    industry=ind,
    defaults={
        "description": "Shreyas Foundation Sports & Outreach Programs Advisor in Gujarati",
        "system_prompt_template": "Welcome prompt gu",
        "default_tone": "polite",
        "default_voice": "gu-IN-DhwaniNeural"
    }
)
agent, _ = VoiceAgent.objects.get_or_create(
    name="Shreya Gujarati",
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
    session_id="test_shreyas_gu_session_1"
)
session.state = {}
session.save()

# Turn 1
prep1 = shreyas_gu_prepare(agent, "નમસ્તે", session)
print(f"Turn 1 Prepare: {prep1}")
assert prep1["static_reply"] == "[PLAY_AUDIO:shreyas_gu_bot/shreyas_gu_step1_greeting.raw]", "Greeting failed"
print("OK")

# Turn 2: Program selection
session.refresh_from_db()
print("\n4. Prepare Turn 2 (Smart Filler check - Program):")
prep2 = shreyas_gu_prepare(agent, "હું મારા બાળકના સ્કેટિંગ માટે જાણવા માંગું છું", session)
print(f"Turn 2 play_filler: {prep2.get('play_filler')}")
assert prep2.get("play_filler") in [f"shreyas_gu_bot/filler_1_{c}.raw" for c in "abcde"], "Should choose program filler"
print("OK")

# Turn 3: Age
session.refresh_from_db()
print("\n5. Prepare Turn 3 (Smart Filler check - Age):")
prep3 = shreyas_gu_prepare(agent, "તે ૧૦ વર્ષનો છે", session)
print(f"Turn 3 play_filler: {prep3.get('play_filler')}")
assert prep3.get("play_filler") in [f"shreyas_gu_bot/filler_2_{c}.raw" for c in "abcde"], "Should choose age filler"
print("OK")

# Turn 4: Consent
session.refresh_from_db()
print("\n6. Prepare Turn 4 (Smart Filler check - Consent):")
prep4 = shreyas_gu_prepare(agent, "હા મોકલી આપો", session)
print(f"Turn 4 play_filler: {prep4.get('play_filler')}")
assert prep4.get("play_filler") in [f"shreyas_gu_bot/filler_3_{c}.raw" for c in "abcde"], "Should choose consent filler"
print("OK")

# Turn 5: Question
session.refresh_from_db()
print("\n7. Prepare Turn 5 (Smart Filler check - Question):")
prep5 = shreyas_gu_prepare(agent, "અહીંયા ફી કેટલી થાય?", session)
print(f"Turn 5 play_filler: {prep5.get('play_filler')}")
assert prep5.get("play_filler") in [f"shreyas_gu_bot/filler_4_{c}.raw" for c in "abcde"], "Should choose question filler"
print("OK")

# Turn 6: Default/Fallback
session.refresh_from_db()
print("\n8. Prepare Turn 6 (Smart Filler check - Fallback):")
prep6 = shreyas_gu_prepare(agent, "હરિ ઓમ", session)
print(f"Turn 6 play_filler: {prep6.get('play_filler')}")
assert prep6.get("play_filler") in [f"shreyas_gu_bot/filler_5_{c}.raw" for c in "abcde"], "Should choose fallback filler"
print("OK")

# Clean up test session
session.delete()
print("\n=== All Tests Passed Successfully ===")
