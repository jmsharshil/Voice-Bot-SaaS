# scratch/test_kia_syros_bot.py

import os
import sys
import django

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from conversations.services.core.behavior_router import get_role_strategy
from conversations.services.core.dialogue_engine import STRATEGY_MAP, PREPARE_MAP, FINALIZE_MAP
from kia_syros_bot.strategy import kia_syros_prepare, kia_syros_strategy
from agents.models import VoiceAgent

print("=== Kia Syros Bot Tests ===")

# 1. Routing Test
print("\n1. Behavior Router test:")
strategy_key = get_role_strategy("Kia Syros EV Advisor")
print(f"Role 'Kia Syros EV Advisor' maps to: {strategy_key}")
assert strategy_key == "kia_syros_strategy", "Strategy mapping failed"
print("OK")

# 2. Registration Test
print("\n2. Dialogue Engine strategy registration test:")
assert "kia_syros_strategy" in STRATEGY_MAP, "STRATEGY_MAP registration failed"
assert "kia_syros_strategy" in PREPARE_MAP, "PREPARE_MAP registration failed"
assert "kia_syros_strategy" in FINALIZE_MAP, "FINALIZE_MAP registration failed"
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

ind, _ = Industry.objects.get_or_create(slug="automobile", defaults={"name": "Automobile"})
tpl, _ = AgentRoleTemplate.objects.get_or_create(
    role_name="Kia Syros EV Advisor",
    industry=ind,
    defaults={
        "description": "Kia Syros EV promotion bot",
        "system_prompt_template": "System prompt",
        "default_tone": "warm",
        "default_voice": "hi-IN-SwaraNeural"
    }
)
agent, _ = VoiceAgent.objects.get_or_create(
    name="Kia Syros Bot",
    owner=user,
    industry=ind,
    role_template=tpl,
    defaults={
        "company_name": "Westcoast Kia",
        "summary": "Voice bot for Westcoast Kia",
        "is_active": True
    }
)

session_id = "test_kia_session_123"
ConversationSession.objects.filter(session_id=session_id).delete()
session = ConversationSession.objects.create(agent=agent, session_id=session_id)

prep1 = kia_syros_prepare(agent, "hello", session)
print("Turn 1 Prep result (Greeting):", prep1)
assert "static_reply" in prep1, "First turn must be a greeting text reply"
assert "Hello, क्या मेरी बात" in prep1["static_reply"], "Greeting text must be returned"
print("OK")

# 4. Strategy Prepare Turn 2 (Pitch Confirmation)
print("\n4. Prepare Turn 2 (Pitch Confirmation) Test:")
prep2 = kia_syros_prepare(agent, "Haan main bol raha hoon", session)
print("Turn 2 Prep result (Pitch):", prep2)
assert "system_prompt" in prep2, "Turn 2 must be routed dynamically to LLM"
assert "play_filler" in prep2, "Turn 2 must select a filler"
print("OK")

# 5. Strategy Prepare Turn 3 (Inquiry Redirect / Fillers) Test:
print("\n5. Prepare Turn 3 (Inquiry Redirect / Fillers) Test:")
prep3 = kia_syros_prepare(agent, "Is the test drive free?", session)
print("Turn 3 Prep user message:", prep3.get("user_message"))
print("Turn 3 Prep filler chosen:", prep3.get("play_filler"))
assert "play_filler" in prep3, "Should select a context filler"
assert "filler_3_" in prep3["play_filler"], "Should select redirect/inquiry filler (category 3)"
print("OK")

# 6. Dialogue Filler Match Tests
from kia_syros_bot.strategy import select_kia_syros_filler
print("\n6. Filler Match Tests:")
f_confirm = select_kia_syros_filler("Haan, callback arrange kar do", {})
print(f"User: 'Haan, callback arrange kar do' -> Filler: {f_confirm}")
assert "filler_1_" in f_confirm

f_unsure = select_kia_syros_filler("Main abhi thoda busy hoon baad mein dekhte hain", {})
print(f"User: 'Main abhi thoda busy hoon...' -> Filler: {f_unsure}")
assert "filler_2_" in f_unsure

f_inquiry = select_kia_syros_filler("Syros EV ki charging time kitna hai?", {})
print(f"User: 'Syros EV ki charging time...' -> Filler: {f_inquiry}")
assert "filler_3_" in f_inquiry

print("All strategy logic verified successfully!")
