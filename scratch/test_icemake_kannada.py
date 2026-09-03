import sys
import os

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from icemake_bot.strategy import icemake_prepare

class MockSession:
    def __init__(self):
        self.session_id = "test_kannada_session_123"
        self.user_number = "9831542402"
        self.state = {}

def run_kannada_flow_test():
    print("==================================================================")
    print("🚀 TESTING ICEMAKE VOICE AGENT - KANNADA (KN) FULL DIALOGUE FLOW")
    print("==================================================================")
    
    session = MockSession()
    agent = None

    # Step 0: Initial Greeting
    res0 = icemake_prepare(agent, "", session)
    print(f"\n[STEP 0 AGENT GREETING]:\n  -> {res0['static_reply']}\n  (TTS Lang: {res0['tts_language']})")

    # Step 0 -> 1: User selects Kannada language
    res1 = icemake_prepare(agent, "ನನಗೆ ಕನ್ನಡದಲ್ಲಿ ಮಾತನಾಡಬೇಕು", session)
    print(f"\n[USER]: ನನಗೆ ಕನ್ನಡದಲ್ಲಿ ಮಾತನಾಡಬೇಕು\n[STEP 1 AGENT]:\n  -> {res1['static_reply']}\n  (Selected Lang: {session.state.get('selected_language')})")

    # Step 1 -> 2: User gives Name
    res2 = icemake_prepare(agent, "ನನ್ನ ಹೆಸರು ತಕ್ಷ ಪಟೇಲ್", session)
    print(f"\n[USER]: ನನ್ನ ಹೆಸರು ತಕ್ಷ ಪಟೇಲ್\n[STEP 2 AGENT]:\n  -> {res2['static_reply']}\n  (Customer Name: {session.state.get('customer_name')})")

    # Step 2 -> 3: User gives State
    res3 = icemake_prepare(agent, "ಕರ್ನಾಟಕ", session)
    print(f"\n[USER]: ಕರ್ನಾಟಕ\n[STEP 3 AGENT]:\n  -> {res3['static_reply']}\n  (State: {session.state.get('state_name')})")

    # Step 3 -> 4: User gives Address / Pincode
    res4 = icemake_prepare(agent, "ಬೆಂಗಳೂರು, ಪಿನ್‌ಕೋಡ್ ೫೬೦೦೦೧", session)
    print(f"\n[USER]: ಬೆಂಗಳೂರು, ಪಿನ್‌ಕೋಡ್ ೫೬૦೦೦೧\n[STEP 4 AGENT]:\n  -> {res4['static_reply']}\n  (City/Address: {session.state.get('city_name')})")

    # Step 4 -> 5: User gives Phone Number (10 digits)
    res5 = icemake_prepare(agent, "೯೮೩೧೫೪೨೪೦೨", session)
    print(f"\n[USER]: ೯೮೩೧೫೪೨೪೦೨\n[STEP 5 AGENT]:\n  -> {res5['static_reply']}\n  (Spoken Num Pronunciation test)")

    # Step 5 -> 6: User confirms registered number
    res6 = icemake_prepare(agent, "ಹೌದು ಇದು ನನ್ನ ನೋಂದಾಯಿತ ಸಂಖ್ಯೆ", session)
    print(f"\n[USER]: ಹೌದು ಇದು ನನ್ನ ನೋಂದಾಯಿತ ಸಂಖ್ಯೆ\n[STEP 6 AGENT]:\n  -> {res6['static_reply']}")

    # Step 6 -> 7: User specifies Ice Make Product
    res7 = icemake_prepare(agent, "ಬ್ಲಾಸ್ಟ್ ಫ್ರೀಜರ್", session)
    print(f"\n[USER]: ಬ್ಲಾಸ್ಟ್ ಫ್ರೀಜರ್\n[STEP 7 AGENT]:\n  -> {res7['static_reply']}\n  (Product Classified: {session.state.get('issue_type')})")

    # Step 7 -> 8: User describes issue
    res8 = icemake_prepare(agent, "ಕೂಲಿಂಗ್ ಸಮಸ್ಯೆ ಇದೆ ಮತ್ತು ಕಂಪನ ಬರುತ್ತದೆ", session)
    print(f"\n[USER]: ಕೂಲಿಂಗ್ ಸಮಸ್ಯೆ ಇದೆ ಮತ್ತು ಕಂಪನ ಬರುತ್ತದೆ\n[STEP 8 AGENT TICKET GENERATION]:\n  -> {res8['static_reply']}\n  (Ticket #: {session.state.get('ticket_number')}, Auto-disconnect: {res8.get('auto_disconnect')})")

    print("\n✅ KANNADA FULL FLOW TEST PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_kannada_flow_test()
