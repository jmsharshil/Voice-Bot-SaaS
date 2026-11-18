import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from agents.models import VoiceAgent
from conversations.models import ConversationSession
from icemake_v2_bot.strategy import (
    icemake_v2_strategy,
    is_valid_alphanumeric_serial,
    ICEMAKE_V2_SERIAL_INVALID_ALPHANUMERIC
)

agent = VoiceAgent.objects.get(name="Ice Make Support Agent V2")

print("--- 1. Direct Unit Tests on is_valid_alphanumeric_serial ---")
assert is_valid_alphanumeric_serial("VCB2502116") == True
assert is_valid_alphanumeric_serial("DF25008959") == True
assert is_valid_alphanumeric_serial("CIM305B501-25030653") == True
assert is_valid_alphanumeric_serial("2502116") == False
assert is_valid_alphanumeric_serial("9428512345") == False
assert is_valid_alphanumeric_serial("VCB") == False
assert is_valid_alphanumeric_serial("DF") == False
print("✅ Unit tests passed!")

print("\n--- 2. Testing Pure Numbers (e.g. '2502116') ---")
session, _ = ConversationSession.objects.get_or_create(agent=agent, session_id="test_pure_numbers_session")
session.state = {
    "current_step": 6,
    "customer_name": "Ayushi",
    "conversation_history": []
}
res = icemake_v2_strategy(agent=agent, message="मेरा मशीन नंबर 2502116 है", session=session)
reply = res if isinstance(res, str) else (res.get("reply", "") or res.get("static_reply", ""))
state = session.state
print("Bot Reply:", reply)
print("Pending Serial in state:", state.get("pending_serial_number"))
print("Current Step in state:", state.get("current_step"))
# Must NOT accept pure number and must NOT set pending_serial_number
assert not state.get("pending_serial_number"), "Error: Pure number should NOT be accepted as pending_serial_number"
assert state.get("current_step") == 6, "Error: Current step should stay at 6"
assert "अल्फ़ान्यूमेरिक" in reply or "अक्षर" in reply or "letters" in reply, "Error: Bot must prompt that serial requires both letters and numbers"
print("✅ Pure numbers correctly rejected!")

print("\n--- 3. Testing Pure Letters (e.g. 'VCB') ---")
session.state = {
    "current_step": 6,
    "customer_name": "Ayushi",
    "conversation_history": []
}
res = icemake_v2_strategy(agent=agent, message="मशीन पर VCB लिखा है", session=session)
reply = res if isinstance(res, str) else (res.get("reply", "") or res.get("static_reply", ""))
state = session.state
print("Bot Reply:", reply)
print("Pending Serial in state:", state.get("pending_serial_number"))
print("Current Step in state:", state.get("current_step"))
assert not state.get("pending_serial_number"), "Error: Pure letters should NOT be accepted"
assert state.get("current_step") == 6, "Error: Current step should stay at 6"
print("✅ Pure letters correctly rejected!")

print("\n--- 4. Testing Valid Alphanumeric (e.g. 'VCB2502116') ---")
session.state = {
    "current_step": 6,
    "customer_name": "Ayushi",
    "conversation_history": []
}
res = icemake_v2_strategy(agent=agent, message="मेरा सीरियल नंबर VCB2502116 है", session=session)
reply = res if isinstance(res, str) else (res.get("reply", "") or res.get("static_reply", ""))
state = session.state
print("Bot Reply:", reply)
print("Pending Serial in state:", state.get("pending_serial_number"))
print("Awaiting confirmation:", state.get("serial_needs_confirmation"))
assert state.get("pending_serial_number") == "VCB2502116", "Error: Alphanumeric serial should be stored in pending_serial_number"
assert state.get("serial_needs_confirmation") == True, "Error: Bot must ask for confirmation"
print("✅ Valid alphanumeric serial correctly accepted and read back!")

print("\n--- 5. Testing Confirmation with 'हाँ' ---")
res2 = icemake_v2_strategy(agent=agent, message="हाँ बिल्कुल सही है", session=session)
reply2 = res2 if isinstance(res2, str) else (res2.get("reply", "") or res2.get("static_reply", ""))
state2 = session.state
print("Bot Reply after confirmation:", reply2)
print("Confirmed Serial in state:", state2.get("serial_number"))
print("Next step:", state2.get("current_step"))
assert state2.get("serial_number") == "VCB2502116", "Error: Confirmed serial should be saved"
assert state2.get("current_step") == 7, "Error: Flow should advance to step 7 (issue description)"
print("✅ Step 7 successfully reached after confirmation!")

print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
