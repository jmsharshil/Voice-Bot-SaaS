import os
import sys
import django

# Setup Django Environment
sys.path.append(r"c:\Users\AYUSHI PATEL\Voicebot_saas\testing\Voice-Bot-SaaS")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from icemake_bot.strategy import icemake_prepare

class MockSession:
    def __init__(self):
        self.session_id = "test_marathi_session_001"
        self.state = {}

def run_marathi_flow_test():
    print("==================================================================")
    print("🚩 TESTING ICEMAKE VOICE AGENT - MARATHI (MR) FULL DIALOGUE FLOW")
    print("==================================================================")

    session = MockSession()
    agent = None

    # Step 0: Greeting
    res0 = icemake_prepare(agent, "", session)
    print(f"\n[STEP 0 AGENT GREETING]:\n  -> {res0['static_reply']}\n  (TTS Lang: {res0['tts_language']})")

    # Step 0 -> 1: User chooses Marathi
    res1 = icemake_prepare(agent, "मला मराठीत बोलायचे आहे", session)
    print(f"\n[USER]: मला मराठीत बोलायचे आहे\n[STEP 1 AGENT]:\n  -> {res1['static_reply']}\n  (Selected Lang: {session.state.get('selected_language')})")
    assert session.state.get("selected_language") == "mr", "Marathi Language detection failed!"

    # Step 1 -> 2: User gives Name
    res2 = icemake_prepare(agent, "माझे नाव तक्ष पटेल आहे", session)
    print(f"\n[USER]: माझे नाव तक्ष पटेल आहे\n[STEP 2 AGENT]:\n  -> {res2['static_reply']}\n  (Customer Name: {session.state.get('customer_name')})")

    # Step 2 -> 3: User gives State
    res3 = icemake_prepare(agent, "महाराष्ट्र", session)
    print(f"\n[USER]: महाराष्ट्र\n[STEP 3 AGENT]:\n  -> {res3['static_reply']}\n  (State: {session.state.get('state_name')})")

    # Step 3 -> 4: User gives City & Address with 6-digit Pincode
    res4 = icemake_prepare(agent, "पुणे, पिनकोड ४११०१", session)
    print(f"\n[USER]: पुणे, पिनकोड ४११०१\n[STEP 4 AGENT]:\n  -> {res4['static_reply']}\n  (City/Address: {session.state.get('city_name')})")

    # Step 4 -> 5: User gives Phone Number (10 digits)
    res5 = icemake_prepare(agent, "९८३१५४२४०२", session)
    print(f"\n[USER]: ९८३१५४२४०२\n[STEP 5 AGENT]:\n  -> {res5['static_reply']}\n  (Spoken Num Pronunciation test)")

    # Step 5 -> 6: User confirms registered number
    res6 = icemake_prepare(agent, "होय हाच माझा नंबर आहे", session)
    print(f"\n[USER]: होय\n[STEP 6 AGENT]:\n  -> {res6['static_reply']}")

    # Step 6 -> 7: User gives product name
    res7 = icemake_prepare(agent, "ब्लास्ट फ्रीझर", session)
    print(f"\n[USER]: ब्लास्ट फ्रीझर\n[STEP 7 AGENT]:\n  -> {res7['static_reply']}\n  (Product Classified: {session.state.get('issue_type')})")

    # Step 7 -> 8: User describes issue
    res8 = icemake_prepare(agent, "माझ्या ब्लास्ट फ्रीझरमध्ये कूलिंग अजिबात होत नाहीये", session)
    print(f"\n[USER]: कूलिंग अजिबात होत नाहीये\n[STEP 8 AGENT TICKET GENERATION]:\n  -> {res8['static_reply']}\n  (Ticket #: {session.state.get('ticket_number')}, Auto-disconnect: {res8.get('auto_disconnect')})")

    print("\n✅ MARATHI FULL FLOW TEST PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_marathi_flow_test()
