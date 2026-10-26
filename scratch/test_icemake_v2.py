import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from conversations.services.core.behavior_router import get_role_strategy
from icemake_v2_bot.strategy import icemake_v2_prepare
from icemake_bot.models import IcemakeTicket
from conversations.models import Conversation, ConversationSession
from agents.models import VoiceAgent
import uuid

def test_icemake_v2():
    print("=" * 60)
    print("🧪 TESTING ICEMAKE V2 (UNIFIED V1 SCRIPT & MULTI-LANGUAGE)")
    print("=" * 60)

    # 1. Test Behavior Router Mapping
    strategy_key = get_role_strategy("Ice Make Cold Room Support V2")
    print(f"\n1. Role strategy mapping: {strategy_key}")
    assert strategy_key == "icemake_v2", f"Expected icemake_v2, got {strategy_key}"

    agent = VoiceAgent.objects.filter(name__icontains="Ice Make").first()
    assert agent is not None, "VoiceAgent for Ice Make must exist"

    # 2. Simulate Full English Call Flow
    print("\n2. Simulating Full English Call Flow (Steps 0 to 8)...")
    session_id_en = f"test_session_en_{uuid.uuid4().hex[:8]}"
    conv_en = Conversation.objects.create(
        agent=agent,
        session_id=session_id_en,
        user_number="8985755019"
    )
    session_en = ConversationSession.objects.create(
        agent=agent,
        session_id=session_id_en
    )

    # Step 0: Greeting
    r0 = icemake_v2_prepare(agent, "", session_en)
    print(f"Bot (Step 0 Greeting): {r0['static_reply']}")
    assert "Welcome to Ice Make twenty four by seven service support" in r0['static_reply']
    assert r0['strategy_key'] == "icemake_v2"

    # Step 0 Response: Customer chooses English
    r1 = icemake_v2_prepare(agent, "English", session_en)
    print(f"Customer: English")
    print(f"Bot (Step 1 Ask Name): {r1['static_reply']}")
    assert "name" in r1['static_reply'].lower()
    assert session_en.state.get("selected_language") == "en"
    assert session_en.state.get("language_locked") is True
    assert r1.get("language_locked") is True

    # Step 1: Customer Name
    r2 = icemake_v2_prepare(agent, "Ram Sharma", session_en)
    print(f"Customer: Ram Sharma")
    print(f"Bot (Step 2 Ask State): {r2['static_reply']}")
    assert "state" in r2['static_reply'].lower()
    assert session_en.state.get("customer_name") == "Ram Sharma"

    # Step 2: Customer State
    r3 = icemake_v2_prepare(agent, "Gujarat", session_en)
    print(f"Customer: Gujarat")
    print(f"Bot (Step 3 Ask Address/Pincode): {r3['static_reply']}")
    assert "address" in r3['static_reply'].lower() or "city" in r3['static_reply'].lower()

    # Step 3 Test: Invalid Pincode (e.g. 5 digits)
    r_inv = icemake_v2_prepare(agent, "My address is Vatva pincode 38244", session_en)
    print(f"Customer (invalid pin): My address is Vatva pincode 38244")
    print(f"Bot (Pincode error): {r_inv['static_reply']}")
    assert "pincode must be 6 digits" in r_inv['static_reply'].lower() or "invalid" in r_inv['static_reply'].lower()

    # Step 3: Valid Address with Pincode
    r4 = icemake_v2_prepare(agent, "Plot 102 GIDC Vatva, Ahmedabad 382445", session_en)
    print(f"Customer: Plot 102 GIDC Vatva, Ahmedabad 382445")
    print(f"Bot (Step 4 Ask Phone): {r4['static_reply']}")
    assert "phone number" in r4['static_reply'].lower()

    # Step 4: Phone partial silent wait test
    r5_part = icemake_v2_prepare(agent, "89857", session_en)
    print(f"Customer (Turn 1 partial): 89857")
    print(f"Bot (Silent wait): '{r5_part['static_reply']}'")
    assert r5_part['static_reply'] == "", "Bot must wait silently for partial phone digits"

    # Step 4: Phone remaining digits
    r5 = icemake_v2_prepare(agent, "55019", session_en)
    print(f"Customer (Turn 2 remaining): 55019")
    print(f"Bot (Step 5 Confirm Number): {r5['static_reply']}")
    assert "eight, nine, eight, five, seven, five, five, zero, one, nine" in r5['static_reply'].lower() or "8985755019" in r5['static_reply']

    # Step 5: Confirm registered number
    r6 = icemake_v2_prepare(agent, "Yes, it is my registered number", session_en)
    print(f"Customer: Yes, it is my registered number")
    print(f"Bot (Step 6 Ask Serial Number): {r6['static_reply']}")
    assert "serial number" in r6['static_reply'].lower()

    # Step 6: Customer speaks partial serial number and pauses to think
    r7_part = icemake_v2_prepare(agent, "84", session_en)
    print(f"Customer (Turn 1 partial serial): 84")
    print(f"Bot (Silent wait): '{r7_part['static_reply']}'")
    assert r7_part['static_reply'] == "", "Expected silent wait for partial serial number"

    # Step 6: Customer speaks remaining serial number
    r7 = icemake_v2_prepare(agent, "920", session_en)
    print(f"Customer (Turn 2 remaining serial): 920")
    print(f"Bot (Step 7 Ask Issue): {r7['static_reply']}")
    assert "freezer" in r7['static_reply'].lower()
    assert "describe the issue you are facing with freezer" in r7['static_reply'].lower()

    # Step 7: Issue description
    r8 = icemake_v2_prepare(agent, "The compressor is vibrating and cooling is not effective.", session_en)
    print(f"Customer: The compressor is vibrating and cooling is not effective.")
    print(f"Bot (Step 8 Closing & Ticket): {r8['static_reply']}")
    assert "V, C" in r8['static_reply'] or "VC" in r8['static_reply']
    assert "[FLOW_COMPLETE]" in r8['static_reply']
    assert r8.get("auto_disconnect") is True
    assert r8['strategy_key'] == "icemake_v2"

    # Verify DB Ticket
    ticket_en = IcemakeTicket.objects.filter(conversation=conv_en).first()
    assert ticket_en is not None, "IcemakeTicket must be created in DB"
    assert ticket_en.ticket_number.startswith("VC")
    print(f"   ✅ Verified English DB Ticket: {ticket_en.ticket_number}, Product: {ticket_en.machine_model_no}")

    # 3. Simulate Full Gujarati Call Flow (10 Languages Support)
    print("\n3. Simulating Full Gujarati Call Flow (Steps 0 to 8)...")
    session_id_gu = f"test_session_gu_{uuid.uuid4().hex[:8]}"
    conv_gu = Conversation.objects.create(
        agent=agent,
        session_id=session_id_gu,
        user_number="9104142402"
    )
    session_gu = ConversationSession.objects.create(agent=agent, session_id=session_id_gu)

    # Step 0: Greeting
    r_gu_0 = icemake_v2_prepare(agent, "", session_gu)
    assert "Welcome to Ice Make twenty four by seven service support" in r_gu_0['static_reply']

    # Step 0: Customer selects Gujarati
    r_gu_1 = icemake_v2_prepare(agent, "ગુજરાતી", session_gu)
    print(f"Customer: ગુજરાતી")
    print(f"Bot (Step 1): {r_gu_1['static_reply']}")
    assert "નામ" in r_gu_1['static_reply']
    assert r_gu_1['tts_language'] == "gu"
    assert session_gu.state.get("selected_language") == "gu"

    # Step 1: Customer Name
    r_gu_2 = icemake_v2_prepare(agent, "ભાવેશ પટેલ", session_gu)
    print(f"Customer: ભાવેશ પટેલ")
    print(f"Bot (Step 2): {r_gu_2['static_reply']}")
    assert "રાજ્ય" in r_gu_2['static_reply']
    assert r_gu_2['tts_language'] == "gu"

    # Step 2: State
    r_gu_3 = icemake_v2_prepare(agent, "ગુજરાત", session_gu)
    print(f"Customer: ગુજરાત")
    print(f"Bot (Step 3): {r_gu_3['static_reply']}")
    assert "સરનામું" in r_gu_3['static_reply']
    assert r_gu_3['tts_language'] == "gu"

    # Step 3: Address & Pincode
    r_gu_4 = icemake_v2_prepare(agent, "વટવા જીઆઈડીસી અમદાવાદ 382445", session_gu)
    print(f"Customer: વટવા જીઆઈડીસી અમદાવાદ 382445")
    print(f"Bot (Step 4): {r_gu_4['static_reply']}")
    assert "નંબર" in r_gu_4['static_reply']
    assert r_gu_4['tts_language'] == "gu"

    # Step 4: Phone number
    r_gu_5 = icemake_v2_prepare(agent, "9104142402", session_gu)
    print(f"Customer: 9104142402")
    print(f"Bot (Step 5): {r_gu_5['static_reply']}")
    assert "નવ, એક, ઝીરો, ચાર, એક, ચાર, બે, ચાર, ઝીરો, બે" in r_gu_5['static_reply']
    assert "રજિસ્ટર્ડ નંબર" in r_gu_5['static_reply']
    assert r_gu_5['tts_language'] == "gu"

    # Step 5: Confirm registered number
    r_gu_6 = icemake_v2_prepare(agent, "હા, સાચો છે", session_gu)
    print(f"Customer: હા, સાચો છે")
    print(f"Bot (Step 6): {r_gu_6['static_reply']}")
    assert "સીરીયલ નંબર" in r_gu_6['static_reply']
    assert r_gu_6['tts_language'] == "gu"

    # Step 6: Customer is unsure and does NOT know the Serial Number
    r_gu_7 = icemake_v2_prepare(agent, "મને ખબર નથી, સીરીયલ નંબર ક્યાં હોય?", session_gu)
    print(f"Customer: મને ખબર નથી, સીરીયલ નંબર ક્યાં હોય?")
    print(f"Bot (Step 7 Guidance + Freezer Issue): {r_gu_7['static_reply']}")
    assert "ઇનવોઇસ" in r_gu_7['static_reply']
    assert "ફ્રીઝર" in r_gu_7['static_reply']
    assert "સમસ્યા" in r_gu_7['static_reply']
    assert r_gu_7['tts_language'] == "gu"

    # Step 7: Issue description
    r_gu_8 = icemake_v2_prepare(agent, "મશીનમાં તાપમાન ઘટી રહ્યું નથી અને બરફ જામતો નથી.", session_gu)
    print(f"Customer: મશીનમાં તાપમાન ઘટી રહ્યું નથી અને બરફ જામતો નથી.")
    print(f"Bot (Step 8 Closing): {r_gu_8['static_reply']}")
    assert "ફરિયાદ નોંધાઈ ગઈ છે" in r_gu_8['static_reply']
    assert "[FLOW_COMPLETE]" in r_gu_8['static_reply']
    assert r_gu_8['tts_language'] == "gu"
    assert r_gu_8['strategy_key'] == "icemake_v2"

    # Verify Gujarati DB Ticket
    ticket_gu = IcemakeTicket.objects.filter(conversation=conv_gu).first()
    assert ticket_gu is not None, "Gujarati IcemakeTicket must be created in DB"
    assert ticket_gu.language == "gu"
    print(f"   ✅ Verified Gujarati DB Ticket: {ticket_gu.ticket_number}, Lang: {ticket_gu.language}")

    # 4. Verifying Strict Language Locking (NO Auto-Switching Even If User Speaks English Loanwords/Digits)
    print("\n4. Verifying Strict Language Locking across all turns...")
    session_id_lock = f"test_session_lock_{uuid.uuid4().hex[:8]}"
    session_lock = ConversationSession.objects.create(agent=agent, session_id=session_id_lock)

    # Step 0: User selects Hindi
    r_hi_0 = icemake_v2_prepare(agent, "", session_lock)
    r_hi_1 = icemake_v2_prepare(agent, "हिंदी", session_lock)
    assert r_hi_1['tts_language'] == "hi"
    assert session_lock.state.get("selected_language") == "hi"
    assert r_hi_1.get("language_locked") is True

    # Step 1: User says name in English, Azure detects 'en'
    r_hi_2 = icemake_v2_prepare(agent, "My name is Rajesh", session_lock, detected_language="en")
    print(f"Customer (Step 1 with 'en'): My name is Rajesh")
    print(f"Bot Reply: {r_hi_2['static_reply']}")
    assert r_hi_2['tts_language'] == "hi", f"Expected 'hi', got {r_hi_2['tts_language']}"
    assert "राज्य" in r_hi_2['static_reply']

    # Step 2: User says state in English, Azure detects 'en'
    r_hi_3 = icemake_v2_prepare(agent, "Gujarat", session_lock, detected_language="en")
    assert r_hi_3['tts_language'] == "hi"
    assert "शहर" in r_hi_3['static_reply'] or "पता" in r_hi_3['static_reply']

    print("   ✅ Verified: Agent strictly locked to selected language across turns!")

    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    test_icemake_v2()
