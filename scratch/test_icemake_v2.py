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

    # Step 1: Greeting (asks language preference without naming languages)
    r0 = icemake_v2_prepare(agent, "", session, detected_language="en")
    print(f"Bot (Step 1): {r0['static_reply']}")
    assert "Welcome to Ice Make Refrigeration Limited" in r0['static_reply']
    assert "Which language would you prefer to speak in?" in r0['static_reply']
    assert "English or Hindi" not in r0['static_reply']

    # Step 2: Customer Response - Language Preference
    r1 = icemake_v2_prepare(agent, "English", session, detected_language="en")
    print(f"Customer: English")
    print(f"Bot (Step 2): {r1['static_reply']}")
    assert "name" in r1['static_reply'].lower()

    # Step 2: Customer Name
    r2 = icemake_v2_prepare(agent, "Ram", session, detected_language="en")
    print(f"Customer: Ram")
    print(f"Bot (Step 3): {r2['static_reply']}")
    assert "address with pincode" in r2['static_reply'].lower()
    assert session.state.get("customer_name") == "Ram"

    # Step 3 Test: Invalid Pincode (e.g. 5 digits)
    r_inv = icemake_v2_prepare(agent, "My address is Kallur pincode 51635", session, detected_language="en")
    print(f"Customer (invalid pin): My address is Kallur pincode 51635")
    print(f"Bot: {r_inv['static_reply']}")
    assert "must be exactly 6 digits" in r_inv['static_reply'].lower()

    # Step 3: Address (e.g. "Plot 102, GIDC Vatva" without pincode)
    r3 = icemake_v2_prepare(agent, "Plot 102, GIDC Vatva", session, detected_language="en")
    print(f"Customer: Plot 102, GIDC Vatva")
    print(f"Bot (State Prompt): {r3['static_reply']}")
    assert "state" in r3['static_reply'].lower(), f"Expected state prompt, got: {r3['static_reply']}"
    assert "dantali" not in r3['static_reply'].lower(), "Should NOT trigger office location FAQ!"

    # Step 4: State (e.g. "Gujarat")
    r4 = icemake_v2_prepare(agent, "Gujarat", session, detected_language="en")
    print(f"Customer: Gujarat")
    print(f"Bot (Serial Number Prompt): {r4['static_reply']}")
    assert "serial number" in r4['static_reply'].lower(), f"Expected serial number prompt, got: {r4['static_reply']}"
    assert "Mr." not in r4['static_reply'], "Should NOT use 'Mr.'"
    assert "Sir" not in r4['static_reply'], "Should NOT use 'Sir'"
    assert session.state.get("state_name") == "Gujarat"

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

    # Step 8: Mobile Number - Turn 1 (User speaks first 5 digits and pauses to think)
    r8_part = icemake_v2_prepare(agent, "89857", session, detected_language="en")
    print(f"Customer (Turn 1 partial): 89857")
    print(f"Bot (Silent Wait): '{r8_part['static_reply']}'")
    assert r8_part['static_reply'] == "", "Bot must wait silently without interrupting for partial phone number!"
    assert session.state.get("partial_phone_digits") == "89857"

    # Step 8: Mobile Number - Turn 2 (User speaks remaining 5 digits)
    r8 = icemake_v2_prepare(agent, "55019", session, detected_language="en")
    print(f"Customer (Turn 2 remaining): 55019")
    print(f"Bot (Step 9 Confirm): {r8['static_reply']}")
    assert "Eight Nine Eight Five" in r8['static_reply']
    assert session.state.get("registered_mobile") == "8985755019"

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
    assert "Mr." not in r10['static_reply'], "Should NOT use 'Mr.'"
    assert "Sir" not in r10['static_reply'], "Should NOT use 'Sir'"
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
    assert "किस भाषा में बात करना पसंद करेंगे?" in r_hi_0['static_reply']
    assert "हिंदी या अंग्रेज़ी" not in r_hi_0['static_reply']

    r_hi_1 = icemake_v2_prepare(agent, "हिंदी", session_hi, detected_language="hi")
    print(f"Customer: हिंदी")
    print(f"Bot Hindi (Step 2): {r_hi_1['static_reply']}")
    assert "नाम" in r_hi_1['static_reply']
    assert "शुभ नाम" in r_hi_1['static_reply']
    assert "सकती हूँ" in r_hi_1['static_reply'], "Name prompt must use female inflection 'सकती हूँ'"

    r_hi_2 = icemake_v2_prepare(agent, "सुरेश", session_hi, detected_language="hi")
    print(f"Customer: सुरेश")
    print(f"Bot Hindi (Step 3): {r_hi_2['static_reply']}")
    assert "सुरेश जी" in r_hi_2['static_reply']
    assert "पिनकोड" in r_hi_2['static_reply']

    r_hi_3 = icemake_v2_prepare(agent, "अहमदाबाद 382445", session_hi, detected_language="hi")
    print(f"Customer: अहमदाबाद 382445")
    print(f"Bot Hindi (State Prompt): {r_hi_3['static_reply']}")
    assert "राज्य" in r_hi_3['static_reply']

    r_hi_4 = icemake_v2_prepare(agent, "गुजरात", session_hi, detected_language="hi")
    print(f"Customer: गुजरात")
    print(f"Bot Hindi (Serial Prompt): {r_hi_4['static_reply']}")
    assert "सीरियल नंबर" in r_hi_4['static_reply']

    # 6. Gujarati Test: Complete Trilingual Flow
    print("\n6. Testing Gujarati Full Call Flow...")
    session_id_gu = f"test_session_gu_{uuid.uuid4().hex[:8]}"
    conv_gu = Conversation.objects.create(
        agent=agent,
        session_id=session_id_gu,
        user_number="9104142402"
    )
    session_gu = ConversationSession.objects.create(agent=agent, session_id=session_id_gu)

    # Step 0: Greeting
    r_gu_0 = icemake_v2_prepare(agent, "", session_gu, detected_language="gu")
    print(f"Bot Gujarati (Step 0): {r_gu_0['static_reply']}")
    assert "આઈસ મેક" in r_gu_0['static_reply']
    assert "તમે કઈ ભાષામાં વાત કરવાનું પસંદ કરશો?" in r_gu_0['static_reply']

    # Step 1: Language selection
    r_gu_1 = icemake_v2_prepare(agent, "ગુજરાતી", session_gu, detected_language="gu")
    print(f"Customer: ગુજરાતી")
    print(f"Bot Gujarati (Step 1): {r_gu_1['static_reply']}")
    assert "નામ" in r_gu_1['static_reply']
    assert "શુભ નામ" in r_gu_1['static_reply']

    # Step 2: Name
    r_gu_2 = icemake_v2_prepare(agent, "ભાવેશ", session_gu, detected_language="gu")
    print(f"Customer: ભાવેશ")
    print(f"Bot Gujarati (Step 2): {r_gu_2['static_reply']}")
    assert "ભાવેશ જી" in r_gu_2['static_reply']
    assert "સરનામું" in r_gu_2['static_reply']

    # Step 3: Address with pincode
    r_gu_3 = icemake_v2_prepare(agent, "પ્લોટ ૪૫, જીઆઇડીસી વટવા 382445", session_gu, detected_language="gu")
    print(f"Customer: પ્લોટ ૪૫, જીઆઇડીસી વટવા 382445")
    print(f"Bot Gujarati (State Prompt): {r_gu_3['static_reply']}")
    assert "રાજ્ય" in r_gu_3['static_reply']

    # Step 4: State
    r_gu_4 = icemake_v2_prepare(agent, "ગુજરાત", session_gu, detected_language="gu")
    print(f"Customer: ગુજરાત")
    print(f"Bot Gujarati (Serial Prompt): {r_gu_4['static_reply']}")
    assert "સિરીયલ નંબર" in r_gu_4['static_reply']

    # Step 7: Machine Serial Number
    r_gu_5 = icemake_v2_prepare(agent, "IK992233", session_gu, detected_language="gu")
    print(f"Customer: IK992233")
    print(f"Bot Gujarati (Step 7 Confirm): {r_gu_5['static_reply']}")
    assert "IK992233" in r_gu_5['static_reply']
    assert "સાચો" in r_gu_5['static_reply']

    # Step 8: Confirm Serial
    r_gu_6 = icemake_v2_prepare(agent, "હા", session_gu, detected_language="gu")
    print(f"Customer: હા")
    print(f"Bot Gujarati (Step 8): {r_gu_6['static_reply']}")
    assert "મોબાઈલ નંબર" in r_gu_6['static_reply']

    # Step 9: Partial phone accumulation in Gujarati
    r_gu_7a = icemake_v2_prepare(agent, "91041", session_gu, detected_language="gu")
    print(f"Customer (Turn 1 partial): 91041")
    assert r_gu_7a['static_reply'] == "", "Bot must wait silently for partial number"

    r_gu_7b = icemake_v2_prepare(agent, "42402", session_gu, detected_language="gu")
    print(f"Customer (Turn 2 remaining): 42402")
    print(f"Bot Gujarati (Step 9 Confirm): {r_gu_7b['static_reply']}")
    assert "નવ એક ઝીરો ચાર એક ચાર બે ચાર ઝીરો બે" in r_gu_7b['static_reply']

    # Step 10: Confirm phone
    r_gu_8 = icemake_v2_prepare(agent, "હા, બરાબર છે", session_gu, detected_language="gu")
    print(f"Customer: હા, બરાબર છે")
    print(f"Bot Gujarati (Step 10): {r_gu_8['static_reply']}")
    assert "સમસ્યા" in r_gu_8['static_reply']

    # Step 11: Issue description
    r_gu_9 = icemake_v2_prepare(agent, "ડીપ ફ્રીઝરમાં બરફ જામતો નથી અને કૂલિંગ બંધ થઈ ગયું છે.", session_gu, detected_language="gu")
    print(f"Customer: ડીપ ફ્રીઝરમાં બરફ જામતો નથી અને કૂલિંગ બંધ થઈ ગયું છે.")
    print(f"Bot Gujarati (Step 11): {r_gu_9['static_reply']}")
    assert "SR S" in r_gu_9['static_reply']
    assert "ફરિયાદ નોંધાઈ ગઈ છે" in r_gu_9['static_reply']
    assert "[FLOW_COMPLETE]" in r_gu_9['static_reply']
    assert r_gu_9.get("auto_disconnect") is True

    # Verify Gujarati Ticket in Database
    ticket_gu = IcemakeTicket.objects.filter(conversation=conv_gu).first()
    assert ticket_gu is not None, "Gujarati IcemakeTicket must be created in DB"
    print(f"\n   Verified Gujarati DB Ticket: {ticket_gu.ticket_number}, Lang: {ticket_gu.language}, Mobile: {ticket_gu.registered_mobile}")
    assert ticket_gu.language == "gu"
    assert ticket_gu.registered_mobile == "9104142402"

    # 7. Verify Telephony Connection: Zero Duplicate Greeting
    print("\n7. Verifying Telephony Connection (Zero Duplicate Greeting)...")
    session_id_tele = f"test_session_tele_{uuid.uuid4().hex[:8]}"
    session_tele = ConversationSession.objects.create(
        agent=agent,
        session_id=session_id_tele,
        state={"intro_shown": True, "current_step": 1, "selected_language": "en"}
    )
    # Caller speaks for the first time after hearing the greeting played by the telephony consumer:
    r_tele = icemake_v2_prepare(agent, "I have a complaint.", session_tele, detected_language="en")
    print(f"Customer: I have a complaint.")
    print(f"Bot Reply: {r_tele['static_reply']}")
    assert "Welcome to Ice Make" not in r_tele['static_reply'], "Greeting must NOT repeat!"
    assert "Which language" not in r_tele['static_reply'], "Language prompt must NOT repeat!"
    assert "name" in r_tele['static_reply'].lower(), "Bot must directly ask for customer name!"
    # 8. Verifying Strict Language Locking (NO Auto-Switching Even If Caller Uses English Words / Azure Detects 'en')
    print("\n8. Verifying Strict Language Locking (NO Auto-Switching)...")
    session_id_lock = f"test_session_lock_{uuid.uuid4().hex[:8]}"
    conv_lock = Conversation.objects.create(
        agent=agent,
        session_id=session_id_lock,
        user_number="9876543210"
    )
    session_lock = ConversationSession.objects.create(agent=agent, session_id=session_id_lock)

    # Step 0: Greeting
    r_lock_0 = icemake_v2_prepare(agent, "", session_lock, detected_language="en")
    assert r_lock_0.get("language_locked") is False, "Language should NOT be locked at Step 0"

    # Step 1: Customer explicitly chooses Gujarati
    r_lock_1 = icemake_v2_prepare(agent, "ગુજરાતી", session_lock, detected_language="gu")
    print(f"Customer selects: ગુજરાતી")
    print(f"Bot (Step 1): {r_lock_1['static_reply']}")
    assert r_lock_1["tts_language"] == "gu"
    assert r_lock_1.get("language_locked") is True, "Language MUST be locked after user selects Gujarati"
    assert session_lock.state.get("selected_language") == "gu"

    # Step 2: Customer speaks name in English, Azure STT falsely tags detected_language='en'
    r_lock_2 = icemake_v2_prepare(agent, "My name is Hitesh Patel", session_lock, detected_language="en")
    print(f"Customer (Step 2, Azure tag 'en'): My name is Hitesh Patel")
    print(f"Bot (Step 2): {r_lock_2['static_reply']}")
    assert r_lock_2["tts_language"] == "gu", f"Expected 'gu', got {r_lock_2['tts_language']}"
    assert "સરનામું" in r_lock_2["static_reply"], "Bot must reply in Gujarati, NOT switch to English!"

    # Step 3: Customer speaks address with English street name, Azure STT tags 'en'
    r_lock_3 = icemake_v2_prepare(agent, "Plot 102 GIDC Vatva Ahmedabad 382445", session_lock, detected_language="en")
    print(f"Customer (Step 3, Azure tag 'en'): Plot 102 GIDC Vatva Ahmedabad 382445")
    print(f"Bot (Step 3 State Prompt): {r_lock_3['static_reply']}")
    assert r_lock_3["tts_language"] == "gu"
    assert "રાજ્ય" in r_lock_3["static_reply"], "State prompt must remain in Gujarati!"

    # Step 4: Customer answers state in English, Azure STT tags 'en'
    r_lock_4 = icemake_v2_prepare(agent, "Gujarat", session_lock, detected_language="en")
    print(f"Customer (Step 4, Azure tag 'en'): Gujarat")
    print(f"Bot (Step 4 Serial Prompt): {r_lock_4['static_reply']}")
    assert r_lock_4["tts_language"] == "gu"
    assert "સિરીયલ નંબર" in r_lock_4["static_reply"], "Serial prompt must remain in Gujarati!"

    # Step 7: Customer gives alphanumeric serial, Azure STT tags 'en'
    r_lock_5 = icemake_v2_prepare(agent, "IK998877", session_lock, detected_language="en")
    print(f"Customer (Step 7, Azure tag 'en'): IK998877")
    print(f"Bot (Step 7 Confirm): {r_lock_5['static_reply']}")
    assert r_lock_5["tts_language"] == "gu"
    assert "સાચો" in r_lock_5["static_reply"], "Serial confirmation must remain in Gujarati!"

    # Step 8: Customer confirms in English, Azure STT tags 'en'
    r_lock_6 = icemake_v2_prepare(agent, "Yes", session_lock, detected_language="en")
    print(f"Customer (Step 8, Azure tag 'en'): Yes")
    print(f"Bot (Step 8): {r_lock_6['static_reply']}")
    assert r_lock_6["tts_language"] == "gu"
    assert "મોબાઈલ નંબર" in r_lock_6["static_reply"], "Mobile number prompt must remain in Gujarati!"

    # Step 9: Customer speaks phone number, Azure STT tags 'en'
    r_lock_7 = icemake_v2_prepare(agent, "9876543210", session_lock, detected_language="en")
    print(f"Customer (Step 9, Azure tag 'en'): 9876543210")
    print(f"Bot (Step 9 Confirm): {r_lock_7['static_reply']}")
    assert r_lock_7["tts_language"] == "gu"
    assert "નવ આઠ સાત" in r_lock_7["static_reply"], "Spoken phone number must be in Gujarati words!"

    # Step 10: Customer confirms phone in English, Azure STT tags 'en'
    r_lock_8 = icemake_v2_prepare(agent, "Yes, absolutely correct", session_lock, detected_language="en")
    print(f"Customer (Step 10, Azure tag 'en'): Yes, absolutely correct")
    print(f"Bot (Step 10): {r_lock_8['static_reply']}")
    assert r_lock_8["tts_language"] == "gu"
    assert "સમસ્યા" in r_lock_8["static_reply"], "Complaint detail prompt must remain in Gujarati!"

    # Step 11: Customer describes issue in English, Azure STT tags 'en'
    r_lock_9 = icemake_v2_prepare(agent, "Compressor is making loud noise and not cooling at all.", session_lock, detected_language="en")
    print(f"Customer (Step 11, Azure tag 'en'): Compressor is making loud noise and not cooling at all.")
    print(f"Bot (Step 11 Closing): {r_lock_9['static_reply']}")
    assert r_lock_9["tts_language"] == "gu"
    assert "ફરિયાદ નોંધાઈ ગઈ છે" in r_lock_9["static_reply"], "Closing reply must remain in Gujarati!"
    assert "[FLOW_COMPLETE]" in r_lock_9["static_reply"]

    # Verify Final Ticket in DB
    ticket_lock = IcemakeTicket.objects.filter(conversation=conv_lock).first()
    assert ticket_lock is not None, "Ticket must be created in DB"
    assert ticket_lock.language == "gu", f"Ticket language must be 'gu', got '{ticket_lock.language}'"
    print(f"   ✅ Verified: All 11 steps strictly remained in Gujarati with zero auto-switch!")

    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    test_icemake_v2()
