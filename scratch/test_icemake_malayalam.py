import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from icemake_bot.strategy import icemake_prepare, _format_spoken_number, _format_spoken_ticket, _clean_conversational_text

class DummySession:
    def __init__(self, session_id="test_ml_session"):
        self.session_id = session_id
        self.state = {}
        self.user_number = "919876543210"

def run_malayalam_test():
    print("=" * 60)
    print("🧪 TESTING ICEMAKE VOICE AGENT - MALAYALAM INTEGRATION")
    print("=" * 60)

    # 1. Test Spoken Number & Spoken Ticket
    phone = "9876543210"
    ticket = "C030926777"
    spoken_phone = _format_spoken_number(phone, "ml")
    spoken_tkt = _format_spoken_ticket(ticket, "ml")
    print(f"📞 Spoken Number (ml): {spoken_phone}")
    print(f"🎫 Spoken Ticket (ml): {spoken_tkt}")

    assert "ഒൻപത്" in spoken_phone, "Malayalam spoken number digit missing"
    assert "സി" in spoken_tkt, "Malayalam spoken ticket C prefix missing"

    # 2. Test Conversational Cleaning
    cleaned_name = _clean_conversational_text("എന്റെ പേര് രാജേഷ് ആണ്")
    print(f"👤 Cleaned Name ('എന്റെ പേര് രാജേഷ് ആണ്'): '{cleaned_name}'")
    assert cleaned_name == "രാജേഷ്", f"Expected 'രാജേഷ്', got '{cleaned_name}'"

    # 3. Simulate Full Dialogue Flow
    session = DummySession()
    
    # Step 0: Greeting
    r0 = icemake_prepare(None, "", session)
    print(f"\n[Step 0 - Agent Greeting]: {r0['static_reply']}")

    # Step 0 -> Select Malayalam
    r1 = icemake_prepare(None, "മലയാളം", session)
    print(f"\n[Step 0 -> Selected Malayalam]: {r1['static_reply']}")
    assert session.state["selected_language"] == "ml"
    assert r1["tts_language"] == "ml"

    # Step 1 -> Customer Name
    r2 = icemake_prepare(None, "എന്റെ പേര് വിഷ്ണു ആണ്", session)
    print(f"\n[Step 1 -> Provided Name]: {r2['static_reply']}")
    assert "വിഷ്ണു" in r2["static_reply"]

    # Step 2 -> State
    r3 = icemake_prepare(None, "കേരളം", session)
    print(f"\n[Step 2 -> Provided State]: {r3['static_reply']}")

    # Step 3 -> Address & Pincode
    r4 = icemake_prepare(None, "കൊച്ചി, പിൻകോഡ് 682001", session)
    print(f"\n[Step 3 -> Provided Address]: {r4['static_reply']}")

    # Step 4 -> Phone Number
    r5 = icemake_prepare(None, "9876543210", session)
    print(f"\n[Step 4 -> Provided Phone]: {r5['static_reply']}")
    assert "സ്ഥിരീകരിക്കാമോ" in r5["static_reply"]

    # Step 5 -> Phone Confirmation
    r6 = icemake_prepare(None, "അതെ", session)
    print(f"\n[Step 5 -> Confirmed Phone]: {r6['static_reply']}")

    # Step 6 -> Product Selection
    r7 = icemake_prepare(None, "ചിലർ", session)
    print(f"\n[Step 6 -> Selected Product]: {r7['static_reply']}")

    # Step 7 -> Issue Description & Step 8 Ticket Generation
    r8 = icemake_prepare(None, "ചില്ലറിൽ കൂളിംഗ് ശരിയായി നടക്കുന്നില്ല", session)
    print(f"\n[Step 8 -> Ticket Generation]: {r8['static_reply']}")
    assert "[FLOW_COMPLETE]" in r8["static_reply"]
    assert "സി" in r8["static_reply"]

    print("\n" + "=" * 60)
    print("✅ SUCCESS! ALL MALAYALAM VOICE AGENT TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    run_malayalam_test()
