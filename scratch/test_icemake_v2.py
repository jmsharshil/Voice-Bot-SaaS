import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from conversations.services.core.behavior_router import get_role_strategy
from icemake_v2_bot.strategy import icemake_v2_prepare
from icemake_v2_bot.pincode_service import lookup_pincode
from icemake_bot.models import IcemakeTicket
from conversations.models import Conversation, ConversationSession
from agents.models import VoiceAgent
import uuid

def test_icemake_v2():
    print("=" * 60)
    print("🧪 TESTING ICEMAKE VOICE AGENT V2 (SCRIPT VERIFICATION)")
    print("=" * 60)

    # 1. Test Behavior Router Mapping
    strategy_key = get_role_strategy("Ice Make Cold Room Support V2")
    print(f"\n1. Role strategy mapping: {strategy_key}")
    assert strategy_key == "icemake_v2", f"Expected icemake_v2, got {strategy_key}"

    # 2. Test Postal Pincode Lookup
    print("\n2. Testing Pincode Lookup...")
    pin_res = lookup_pincode("516355")
    print(f"   Lookup 516355: {pin_res}")
    assert pin_res.get("state") != "", "Pincode state lookup should not be empty"

    # 3. Simulate Full English Call Flow
    print("\n3. Simulating Full English Call Flow (Steps 1 to 11)...")
    agent = VoiceAgent.objects.filter(name="Ice Make Support Agent V2").first()
    session_id = f"test_session_{uuid.uuid4().hex[:8]}"
    
    # Create DB Conversation for testing ticket saving
    conv = Conversation.objects.create(
        agent=agent,
        session_id=session_id,
        user_number="8985755019"
    )
    session = ConversationSession.objects.create(
        agent=agent,
        session_id=session_id
    )

    # Step 1: Greeting
    r0 = icemake_v2_prepare(agent, "", session, detected_language="en")
    print(f"Bot (Step 1): {r0['static_reply']}")
    assert "Welcome to Ice Make Refrigeration Limited" in r0['static_reply']

    # Step 2: Customer Response
    r1 = icemake_v2_prepare(agent, "I have a complaint.", session, detected_language="en")
    print(f"Customer: I have a complaint.")
    print(f"Bot (Step 3): {r1['static_reply']}")
    assert "name" in r1['static_reply'].lower()

    # Step 3: Customer Name
    r2 = icemake_v2_prepare(agent, "Ram", session, detected_language="en")
    print(f"Customer: Ram")
    print(f"Bot (Step 4): {r2['static_reply']}")
    assert "pincode" in r2['static_reply'].lower()
    assert session.state.get("customer_name") == "Ram"

    # Step 4: Postal Pincode
    r3 = icemake_v2_prepare(agent, "516355", session, detected_language="en")
    print(f"Customer: 516355")
    print(f"Bot (Step 5): {r3['static_reply']}")
    assert "pincode provided" in r3['static_reply'].lower()

    # Step 5: Address Confirmation (Customer says Yes)
    r4 = icemake_v2_prepare(agent, "Yes", session, detected_language="en")
    print(f"Customer: Yes")
    print(f"Bot (Step 6): {r4['static_reply']}")
    assert "landmark" in r4['static_reply'].lower()

    # Step 6: Full Address
    r5 = icemake_v2_prepare(agent, "Plot 12, Industrial Area, near City Gate", session, detected_language="en")
    print(f"Customer: Plot 12, Industrial Area, near City Gate")
    print(f"Bot (Step 7): {r5['static_reply']}")
    assert "serial number" in r5['static_reply'].lower()

    # Step 7: Machine Serial Number
    r6 = icemake_v2_prepare(agent, "xxxkk11234", session, detected_language="en")
    print(f"Customer: xxxkk11234")
    print(f"Bot (Step 7 Confirm): {r6['static_reply']}")
    assert "XXXKK11234" in r6['static_reply']

    # Step 7 Confirmation: Customer says Yes
    r7 = icemake_v2_prepare(agent, "Yes", session, detected_language="en")
    print(f"Customer: Yes")
    print(f"Bot (Step 8): {r7['static_reply']}")
    assert "mobile number" in r7['static_reply'].lower()
    assert session.state.get("machine_sr_no") == "XXXKK11234"

    # Step 8: Mobile Number
    r8 = icemake_v2_prepare(agent, "8985755019", session, detected_language="en")
    print(f"Customer: 8985755019")
    print(f"Bot (Step 9 Confirm): {r8['static_reply']}")
    assert "Eight Nine Eight Five" in r8['static_reply']

    # Step 9 Confirmation: Customer says Yes or OK
    r9 = icemake_v2_prepare(agent, "Yes", session, detected_language="en")
    print(f"Customer: Yes")
    print(f"Bot (Step 10): {r9['static_reply']}")
    assert "describe the issue" in r9['static_reply'].lower()

    # Step 10: Complaint Recording
    r10 = icemake_v2_prepare(agent, "The freezer compressor is not cooling and temperature is rising.", session, detected_language="en")
    print(f"Customer: The freezer compressor is not cooling and temperature is rising.")
    print(f"Bot (Step 11): {r10['static_reply']}")
    assert "SR S" in r10['static_reply']
    assert "[FLOW_COMPLETE]" in r10['static_reply']
    assert r10.get("auto_disconnect") is True

    # 4. Verify Ticket Creation in Database
    ticket = IcemakeTicket.objects.filter(conversation=conv).first()
    assert ticket is not None, "IcemakeTicket must be created in DB"
    print(f"\n4. Verified DB Ticket Created:")
    print(f"   Ticket Number: {ticket.ticket_number}")
    print(f"   Customer Name: {ticket.customer_name}")
    print(f"   Pincode: {ticket.pin_code}")
    print(f"   City/State: {ticket.city_state}")
    print(f"   Machine Serial No: {ticket.machine_sr_no}")
    print(f"   Registered Mobile: {ticket.registered_mobile}")
    print(f"   Issue Description: {ticket.issue_description}")
    assert ticket.ticket_number.startswith("SR S")
    assert ticket.machine_sr_no == "XXXKK11234"

    # 5. Hindi Test: Greeting & Flow
    print("\n5. Testing Hindi Bilingual Support...")
    session_id_hi = f"test_session_hi_{uuid.uuid4().hex[:8]}"
    session_hi = ConversationSession.objects.create(agent=agent, session_id=session_id_hi)
    r_hi_0 = icemake_v2_prepare(agent, "", session_hi, detected_language="hi")
    print(f"Bot Hindi (Step 1): {r_hi_0['static_reply']}")
    assert "आइस मेक" in r_hi_0['static_reply']
    assert "सकती हूँ" in r_hi_0['static_reply'], "Greeting must use female inflection 'सकती हूँ'"

    r_hi_1 = icemake_v2_prepare(agent, "मेरी एक शिकायत है।", session_hi, detected_language="hi")
    print(f"Customer: मेरी एक शिकायत है।")
    print(f"Bot Hindi (Step 2): {r_hi_1['static_reply']}")
    assert "नाम" in r_hi_1['static_reply']
    assert "सकती हूँ" in r_hi_1['static_reply'], "Name prompt must use female inflection 'सकती हूँ'"

    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    test_icemake_v2()
