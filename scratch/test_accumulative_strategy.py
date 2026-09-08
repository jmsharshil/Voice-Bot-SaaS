import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from conversations.models import ConversationSession
from icemake_bot.strategy import icemake_prepare

print("==================================================")
print("  TESTING ACCUMULATIVE MULTI-TURN PHONE & PINCODE ")
print("==================================================")

class DummySession:
    def __init__(self, session_id="test_session_123"):
        self.session_id = session_id
        self.state = {"current_step": 4, "selected_language": "hi", "customer_name": "Taksh Patel"}

session = DummySession()

# Turn 1: Caller speaks first 5 digits
print("\n--- Step 4: Turn 1 ---")
msg1 = "99133"
res1 = icemake_prepare(None, msg1, session, detected_language="hi")
print(f"User Input 1: '{msg1}'")
print(f"Partial Digits Stored in State: '{session.state.get('partial_phone_digits')}'")
print(f"Current Step: {session.state.get('current_step')} | Static Reply: '{res1.get('static_reply')}'")

# Turn 2: Caller speaks remaining digits phonetically: "एट वन 306" (81306)
print("\n--- Step 4: Turn 2 ---")
msg2 = "एट वन 306"
res2 = icemake_prepare(None, msg2, session, detected_language="hi")
print(f"User Input 2: '{msg2}'")
print(f"Registered Mobile Saved in State: '{session.state.get('registered_mobile')}'")
print(f"Current Step: {session.state.get('current_step')}")
print(f"Bot Confirmation Reply: '{res2.get('static_reply')}'")

print("\n==================================================")
print("  ACCUMULATIVE MULTI-TURN TEST FINISHED SUCCESSFULLY ")
print("==================================================")
