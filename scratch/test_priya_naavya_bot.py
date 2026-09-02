# scratch/test_priya_naavya_bot.py

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from agents.models import VoiceAgent
from conversations.models import ConversationSession
from priya_naavya_bot.strategy import priya_naavya_strategy, priya_naavya_prepare, OPENING_VARIANTS
from bot.views import pre_synthesize_greeting

def test_priya_bot():
    print("--- 1. Testing VoiceAgent Database Seeding ---")
    agent = VoiceAgent.objects.filter(name__icontains="Priya").first()
    assert agent is not None, "Priya VoiceAgent not found in DB!"
    print(f"Agent Found: {agent.name} (ID: {agent.id})")
    print(f"Role Name  : {agent.role_template.role_name}")

    print("\n--- 2. Testing Locked Opening Greeting ---")
    seen_variants = set()
    for i in range(5):
        sess = ConversationSession.objects.create(session_id=f"test_priya_rot_{i}", agent=agent)
        res = priya_naavya_prepare(agent, "hello", sess)
        reply = res["static_reply"]
        seen_variants.add(reply)
        sess.delete()
    
    print(f"Total Unique Opening Variants Observed: {len(seen_variants)} / 1 (Locked)")
    for v in seen_variants:
        print(f"  - '{v}'")
    assert len(seen_variants) == 1, "Expected single locked opening greeting!"

    print("\n--- 3. Testing Full Positive Stage Flow (Stages 1 -> 6) ---")
    sess = ConversationSession.objects.create(session_id="test_priya_flow_positive", agent=agent)
    
    # Turn 1: Opening
    res1 = priya_naavya_strategy(agent, "hello", sess)
    print(f"Stage 1 (Greeting)  : {res1['response']}")

    # Turn 2: User agrees to 2 minutes -> Stage 2 (Confirm Pain)
    res2 = priya_naavya_strategy(agent, "haan bolo, 2 minute hai mere paas", sess)
    print(f"Stage 2 (Confirm Pain): {res2['response']}")

    # Turn 3: User answers lead volume -> Stage 3 (Value Prop)
    res3 = priya_naavya_strategy(agent, "mahine mein around 100 leads aate hain, haan late reply se leads miss hote hain", sess)
    print(f"Stage 3 (Value Prop)  : {res3['response']}")

    # Turn 4: User responds positive -> Stage 4 (Meta Proof)
    res4 = priya_naavya_strategy(agent, "acha, yeh kaise kaam karta hai?", sess)
    print(f"Stage 4 (Meta Proof)  : {res4['response']}")

    # Turn 5: User is amazed -> Stage 5 (Soft CTA / Trial)
    res5 = priya_naavya_strategy(agent, "sach mein? mujhe toh pata bhi nahi chala ki AI baat kar raha hai!", sess)
    print(f"Stage 5 (Free Trial)  : {res5['response']}")

    # Turn 6: User agrees to trial -> Stage 6 (Book Demo)
    res6 = priya_naavya_strategy(agent, "theek hai, free trial de do, 3 din ka", sess)
    print(f"Stage 6 (Book Demo)   : {res6['response']}")

    sess.delete()

    print("\n--- 4. Testing Objection Handling Matrix ---")
    
    # Objection 1: Interested nahi hoon
    sess_obj1 = ConversationSession.objects.create(session_id="test_obj1", agent=agent)
    priya_naavya_strategy(agent, "hello", sess_obj1)
    res_obj1 = priya_naavya_strategy(agent, "interested nahi hoon", sess_obj1)
    print(f"Objection 1 (Not Interested) : {res_obj1['response']}")
    sess_obj1.delete()

    # Objection 2: WhatsApp pe bhej do
    sess_obj2 = ConversationSession.objects.create(session_id="test_obj2", agent=agent)
    priya_naavya_strategy(agent, "hello", sess_obj2)
    res_obj2 = priya_naavya_strategy(agent, "whatsapp pe details bhej do", sess_obj2)
    print(f"Objection 2 (WhatsApp Details): {res_obj2['response']}")
    sess_obj2.delete()

    # Objection 3: Already staff hai
    sess_obj3 = ConversationSession.objects.create(session_id="test_obj3", agent=agent)
    priya_naavya_strategy(agent, "hello", sess_obj3)
    res_obj3 = priya_naavya_strategy(agent, "humare paas already staff hai", sess_obj3)
    print(f"Objection 3 (Already Staff)  : {res_obj3['response']}")
    sess_obj3.delete()

    # Objection 4: Kitna cost hoga?
    sess_obj4 = ConversationSession.objects.create(session_id="test_obj4", agent=agent)
    priya_naavya_strategy(agent, "hello", sess_obj4)
    res_obj4 = priya_naavya_strategy(agent, "kitna cost hoga?", sess_obj4)
    print(f"Objection 4 (Pricing / Cost) : {res_obj4['response']}")
    sess_obj4.delete()

    # Objection 5: Yeh AI hai kya?
    sess_obj5 = ConversationSession.objects.create(session_id="test_obj5", agent=agent)
    priya_naavya_strategy(agent, "hello", sess_obj5)
    res_obj5 = priya_naavya_strategy(agent, "yeh AI hai kya, bot hai?", sess_obj5)
    print(f"Objection 5 (AI Reveal Check): {res_obj5['response']}")
    sess_obj5.delete()

    # Objection 6: Ji nahi main abhi free nahi hoon
    sess_obj6 = ConversationSession.objects.create(session_id="test_obj6", agent=agent)
    priya_naavya_strategy(agent, "hello", sess_obj6)
    res_obj6 = priya_naavya_strategy(agent, "ji nahi main abhi free nahi hoon", sess_obj6)
    print(f"Objection 6 (Busy / Not Free) : {res_obj6['response']}")
    sess_obj6.delete()

    # Objection 7: Devanagari Price ("जी उसका प्राइस क्या होता है")
    sess_obj7 = ConversationSession.objects.create(session_id="test_obj7", agent=agent)
    priya_naavya_prepare(agent, "hello", sess_obj7)
    res_obj7 = priya_naavya_prepare(agent, "जी उसका प्राइस क्या होता है", sess_obj7)
    assert res_obj7.get("static_reply") is not None, "Devanagari Price query should trigger fast-path static reply!"
    print(f"Objection 7 (Devanagari Price): {res_obj7['static_reply']}")
    sess_obj7.delete()

    # Objection 8: Devanagari WhatsApp ("जी आप मुझे व्हाट्सएप पे भेज दीजिए")
    sess_obj8 = ConversationSession.objects.create(session_id="test_obj8", agent=agent)
    priya_naavya_prepare(agent, "hello", sess_obj8)
    res_obj8 = priya_naavya_prepare(agent, "जी आप मुझे व्हाट्सएप पे भेज दीजिए", sess_obj8)
    assert res_obj8.get("static_reply") is not None, "Devanagari WhatsApp query should trigger fast-path static reply!"
    print(f"Objection 8 (Devanagari WhatsApp): {res_obj8['static_reply']}")
    sess_obj8.delete()

    # Objection 9: Devanagari AI Reveal ("AI बात कर रहा है क्या आप")
    sess_obj9 = ConversationSession.objects.create(session_id="test_obj9", agent=agent)
    priya_naavya_prepare(agent, "hello", sess_obj9)
    res_obj9 = priya_naavya_prepare(agent, "AI बात कर रहा है क्या आप", sess_obj9)
    assert res_obj9.get("static_reply") is not None, "Devanagari AI query should trigger fast-path static reply!"
    print(f"Objection 9 (Devanagari AI Reveal): {res_obj9['static_reply']}")
    sess_obj9.delete()

    print("\n--- 5. Testing Outbound Pre-Synthesis ---")
    test_phone = "9998887779"
    pre_synthesize_greeting(str(agent.id), test_phone, name="Ramesh", language="hi")
    
    raw_path = os.path.join("mp3_responses", f"pre_synthesized_{agent.id}_{test_phone}.raw")
    assert os.path.exists(raw_path), f"Pre-synthesized file not found at {raw_path}"
    file_size = os.path.getsize(raw_path)
    print(f"Pre-synthesized audio size: {file_size} bytes")
    assert file_size > 5000, "Pre-synthesized audio file is suspiciously small!"

    print("\n✅ SUCCESS: All Priya Naavya.ai Voice Agent tests passed cleanly!")

if __name__ == "__main__":
    test_priya_bot()
