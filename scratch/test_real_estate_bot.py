import os
import sys
import django

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from conversations.services.core.behavior_router import get_role_strategy
from conversations.services.core.dialogue_engine import STRATEGY_MAP, PREPARE_MAP, FINALIZE_MAP, get_agent_tts_language
from conversations.consumers import TEMP_REAL_ESTATE_MATCHER

print("1. Behavior Router test:")
strategy_key = get_role_strategy("Naavya JMS Real Estate Advisor")
print(f"Role 'Naavya JMS Real Estate Advisor' maps to: {strategy_key}")
assert strategy_key == "temp_real_estate_strategy", "Strategy mapping failed"

print("\n2. Dialogue Engine strategy registration test:")
assert "temp_real_estate_strategy" in STRATEGY_MAP, "STRATEGY_MAP registration failed"
assert "temp_real_estate_strategy" in PREPARE_MAP, "PREPARE_MAP registration failed"
assert "temp_real_estate_strategy" in FINALIZE_MAP, "FINALIZE_MAP registration failed"
print("All strategy function maps registered successfully!")

print("\n3. Language resolution test:")
from agents.models import VoiceAgent
agent = VoiceAgent.objects.filter(role_template__role_name="Naavya JMS Real Estate Advisor").first()
if agent:
    lang = get_agent_tts_language(agent.id)
    print(f"Agent {agent.name} (TTS Language): {lang}")
    assert lang == "gu", "Language mapping failed"
else:
    # If no agent exists, let's create a dummy one for testing
    from django.contrib.auth.models import User
    from agents.models import Industry, AgentRoleTemplate
    user, _ = User.objects.get_or_create(username="test_admin")
    ind = Industry.objects.get(slug="temp-real-estate")
    tpl = AgentRoleTemplate.objects.get(industry=ind, role_name="Naavya JMS Real Estate Advisor")
    dummy_agent = VoiceAgent.objects.create(
        owner=user,
        industry=ind,
        role_template=tpl,
        name="Naavya Test Agent",
        company_name="JMS Real Estate"
    )
    try:
        lang = get_agent_tts_language(dummy_agent.id)
        print(f"Agent {dummy_agent.name} (TTS Language): {lang}")
        assert lang == "gu", "Language mapping failed"
    finally:
        dummy_agent.delete()

print("\n4. Matcher trigger test:")
assert TEMP_REAL_ESTATE_MATCHER is not None, "TEMP_REAL_ESTATE_MATCHER failed to load"
match1 = TEMP_REAL_ESTATE_MATCHER.find_match("મને ૨બીએચકે ફ્લેટ જોઈએ છે", current_phase="GREETING_REPLY")
print(f"Match 1 (2BHK Flat type in Gujarati): {match1}")
assert match1["match_type"] == "CONTEXTUAL", "Flat type matching failed"
assert match1["mp3"] == "temp_real_estate_bot/real_estate_step2_ask_area.raw", "Incorrect flat type response raw file"

match2 = TEMP_REAL_ESTATE_MATCHER.find_match("બોપલ વિસ્તારમાં", current_phase="ASK_AREA")
print(f"Match 2 (Bopal area in Gujarati): {match2}")
assert match2["match_type"] == "CONTEXTUAL", "Area matching failed"
assert match2["mp3"] == "temp_real_estate_bot/real_estate_step3_ask_budget.raw", "Incorrect area response raw file"

match3 = TEMP_REAL_ESTATE_MATCHER.find_match("૫૦ લાખ સુધી", current_phase="ASK_BUDGET")
print(f"Match 3 (50 Lakh budget in Gujarati): {match3}")
assert match3["match_type"] == "CONTEXTUAL", "Budget matching failed"
assert match3["mp3"] == "temp_real_estate_bot/real_estate_step4_ask_name.raw", "Incorrect budget response raw file"

match4 = TEMP_REAL_ESTATE_MATCHER.find_match("અમિત ભાઈ", current_phase="ASK_NAME")
print(f"Match 4 (Amit name in Gujarati): {match4}")
assert match4["match_type"] == "CONTEXTUAL", "Name matching failed"
assert match4["mp3"] == "temp_real_estate_bot/real_estate_step5_closing.raw", "Incorrect name response raw file"

print("\nAll tests completed successfully!")
