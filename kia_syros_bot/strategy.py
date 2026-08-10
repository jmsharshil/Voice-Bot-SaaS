# kia_syros_bot/strategy.py

import logging
import re
import random
from .prompts import KIA_SYROS_SYSTEM_PROMPT
from conversations.services.core.strategies import save_session

logger = logging.getLogger("KiaSyrosBotStrategy")

MAX_MESSAGE_LENGTH = 1000
MAX_TURNS = 10

def _kia_syros_sanitise(message: str) -> str:
    return message.strip()[:MAX_MESSAGE_LENGTH]

def get_db_history_text(session_id: str) -> str:
    from conversations.models import Conversation, Message
    try:
        conv = Conversation.objects.filter(session_id=session_id).first()
        if conv:
            messages = Message.objects.filter(conversation=conv).order_by("created_at")
            history_lines = []
            for m in messages:
                role = "Customer" if m.role == "user" else "Agent"
                clean_text = re.sub(r'\[\s*PHASE:[^\]]*\]', '', m.text, flags=re.I)
                clean_text = re.sub(r'\[\s*PLAY_AUDIO:[^\]]*\]', '', clean_text, flags=re.I)
                for t in ["[BOOKING_CONFIRMED]", "[NOT_INTERESTED]", "[LEAD_COMPLETE]", "[END_CALL]"]:
                    clean_text = clean_text.replace(t, "")
                clean_text = clean_text.strip()
                if clean_text:
                    history_lines.append(f"{role}: {clean_text}")
            return "\n".join(history_lines)
    except Exception as e:
        logger.error(f"Error building database history for Kia Syros: {e}")
    return ""

# ─── NON-STREAMING (text fallback) ───────────────────────

def kia_syros_strategy(agent, message, session, **kwargs):
    state: dict = session.state or {}
    raw_message = _kia_syros_sanitise(message)
    msg = raw_message.lower()
    conversation_history: list = state.get("conversation_history", [])

    if any(w in msg for w in ["bye", "goodbye", "exit", "quit", "see you"]):
        save_session(session, {})
        return "Thank you. Hamari EV Sales Expert team aapse jald hi contact karegi aur aage ki process mein assist karegi. Have a great day! [END_CALL]"

    customer_name = state.get("customer_name")
    if not state.get("intro_shown"):
        if customer_name and customer_name != "Sir/Ma'am":
            reply = (
                f"Hello, kya meri baat {customer_name} se ho rahi hai? Main Westcoast Kia se bol rahi hoon. "
                "Aapne pehle hamare dealership par enquiry ki thi. Isliye hum aapko all-new Kia Syros EV ke "
                "exclusive test drive experience ke liye invite karna chahte hain."
            )
        else:
            reply = (
                "Hello, kya meri baat aapse ho rahi hai? Main Westcoast Kia se bol rahi hoon. "
                "Aapne pehle hamare dealership par enquiry ki thi. Isliye hum aapko all-new Kia Syros EV ke "
                "exclusive test drive experience ke liye invite karna chahte hain."
            )
        state["intro_shown"] = True
        state["conversation_history"] = [f"Agent: {reply}"]
        save_session(session, state)
        return reply

    conversation_history.append(f"User: {raw_message}")
    if len(conversation_history) > MAX_TURNS:
        conversation_history = conversation_history[-MAX_TURNS:]

    history_text = get_db_history_text(session.session_id)
    system_prompt = KIA_SYROS_SYSTEM_PROMPT.format(customer_name=customer_name, history_text=history_text)

    from conversations.services.azure_openai_service import generate_response
    response = generate_response(system_prompt, raw_message)

    conversation_history.append(f"Agent: {response}")
    state["conversation_history"] = conversation_history
    state["last_bot_message"] = response
    save_session(session, state)

    return response

# ─── SMART FILLERS SELECTION ─────────────────────────────

# ─── SMART FILLERS SELECTION ─────────────────────────────

KIA_SYROS_FILLER_TEXTS = {
    # Category 1: Confirmation
    "kia_syros_bot/filler_1_a.raw": "Ji bilkul, main abhi check karti hoon...",
    "kia_syros_bot/filler_1_b.raw": "Sure, main details note kar rahi hoon...",
    "kia_syros_bot/filler_1_c.raw": "Theek hai, main abhi process karti hoon...",
    "kia_syros_bot/filler_1_d.raw": "Ji haan, main abhi process start karti hoon...",
    "kia_syros_bot/filler_1_e.raw": "Bilkul, main callback request register kar rahi hoon...",
    "kia_syros_bot/filler_1_f.raw": "Sure, main abhi isko note kar leti hoon...",
    "kia_syros_bot/filler_1_g.raw": "Ji bilkul, main abhi update kar rahi hoon...",

    # Category 2: Unsure
    "kia_syros_bot/filler_2_a.raw": "Acha, main aapko short mein samjha deti hoon...",
    "kia_syros_bot/filler_2_b.raw": "Got it, main iski details check karti hoon...",
    "kia_syros_bot/filler_2_c.raw": "Ji main samajh sakti hoon, ek second...",
    "kia_syros_bot/filler_2_d.raw": "Theek hai, main check karti hoon...",
    "kia_syros_bot/filler_2_e.raw": "Acha, aapki convenience ke hisab se...",
    "kia_syros_bot/filler_2_f.raw": "Ji, main short mein batane ki koshish karti hoon...",
    "kia_syros_bot/filler_2_g.raw": "Theek hai, main note kar rahi hoon...",

    # Category 3: Inquiry
    "kia_syros_bot/filler_3_a.raw": "Ji, iski details ke liye ek second...",
    "kia_syros_bot/filler_3_b.raw": "Achha sawal hai! Main system mein check karti hoon...",
    "kia_syros_bot/filler_3_c.raw": "Ji, main abhi information check karti hoon...",
    "kia_syros_bot/filler_3_d.raw": "Bilkul, iski specs ke baare mein...",
    "kia_syros_bot/filler_3_e.raw": "Ji haan, Syros EV ke baare mein...",
    "kia_syros_bot/filler_3_f.raw": "Acha, main details verify kar leti hoon...",
    "kia_syros_bot/filler_3_g.raw": "Sure, main details confirm kar rahi hoon...",

    # Category 4: Default
    "kia_syros_bot/filler_4_a.raw": "Ji, bilkul, ek second...",
    "kia_syros_bot/filler_4_b.raw": "Acha, main note kar rahi hoon...",
    "kia_syros_bot/filler_4_c.raw": "Ji, main abhi check karti hoon...",
    "kia_syros_bot/filler_4_d.raw": "Theek hai, please ek moment...",
    "kia_syros_bot/filler_4_e.raw": "Ji haan, just a second...",
    "kia_syros_bot/filler_4_f.raw": "Bilkul, main abhi check karti hoon...",
    "kia_syros_bot/filler_4_g.raw": "Okay, just a moment...",

    # Category 5: Identity Confirm
    "kia_syros_bot/filler_5_a.raw": "Ji achha, shukriya.",
    "kia_syros_bot/filler_5_b.raw": "Ji thank you confirm karne ke liye... "
}

def select_kia_syros_filler(user_msg: str, state: dict) -> str:
    msg = user_msg.lower()
    
    # 1. Product details, price, features, range, etc. (Category 3)
    inquiry_keywords = [
        "price", "range", "feature", "features", "offer", "offers", "finance", "exchange",
        "daam", "rate", "cost", "km", "charge", "charging", "battery", "mileage", "spec", "specs",
        "keemat", "kimat", "paisey", "paise", "average", "kitna deti hai", "free", "test drive",
        "details", "info", "information","कीमत", "रेंज", "फीचर", "फीचर्स", "ऑफर", "ऑफर्स", "फाइनेंस", "एक्सचेंज",
        "दाम", "रेट", "लागत", "किलोमीटर", "चार्ज", "चार्जिंग", "बैटरी", "माइलेज",
        "स्पेक", "स्पेक्स", "कीमत", "कीमत", "पैसे", "पैसे", "औसत", "कितना देती है",
        "फ्री", "टेस्ट ड्राइव", "डिटेल्स", "जानकारी", "जानकारी","प्राइस", "रेंज", "फीचर", "फीचर्स", "ऑफर", "ऑफर्स", "फाइनेंस", "एक्सचेंज",
        "दाम", "रेट", "कॉस्ट", "केएम", "चार्ज", "चार्जिंग", "बैटरी", "माइलेज",
        "स्पेक", "स्पेक्स", "कीमत", "किमत", "पैसे", "पैसे", "एवरेज", "कितना देती है",
        "फ्री", "टेस्ट ड्राइव", "डिटेल्स", "इन्फो", "इन्फॉर्मेशन"
    ]
    if any(re.search(r'\b' + re.escape(k) + r'\b', msg) for k in inquiry_keywords):
        files = [
            "kia_syros_bot/filler_3_a.raw",
            "kia_syros_bot/filler_3_b.raw",
            "kia_syros_bot/filler_3_c.raw",
            "kia_syros_bot/filler_3_d.raw",
            "kia_syros_bot/filler_3_e.raw",
            "kia_syros_bot/filler_3_f.raw",
            "kia_syros_bot/filler_3_g.raw"
        ]
    # 2. Unsure / Hesitant / Rejection (Category 2)
    elif any(re.search(r'\b' + re.escape(k) + r'\b', msg) for k in [
        "unsure", "not sure", "no", "nahi", "na", "busy", "time nahi", "baad mein", "later",
        "call back", "fursat nahi", "busy hoon", "nahi chahiye", "no thanks",
        "असुरक्षित", "पक्का नहीं", "नहीं", "नहीं", "ना", "व्यस्त", "समय नहीं", "बाद में",
        "कॉल बैक", "फुरसत नहीं", "व्यस्त हूँ", "नहीं चाहिए", "नो थैंक्स","अनश्योर", "नॉट श्योर", "नो", "नहीं", "ना", "बिज़ी", "टाइम नहीं", "बाद में", "लेटर",
        "कॉल बैक", "फुर्सत नहीं", "बिज़ी हूं", "नहीं चाहिए", "नो थैंक्स"
    ]):
        files = [
            "kia_syros_bot/filler_2_a.raw",
            "kia_syros_bot/filler_2_b.raw",
            "kia_syros_bot/filler_2_c.raw",
            "kia_syros_bot/filler_2_d.raw",
            "kia_syros_bot/filler_2_e.raw",
            "kia_syros_bot/filler_2_f.raw",
            "kia_syros_bot/filler_2_g.raw"
        ]
    # 3. Confirmation / Yes (Category 1)
    elif any(re.search(r'\b' + re.escape(k) + r'\b', msg) for k in [
        "yes", "haan", "sure", "ok", "okay", "haa", "ha", "thik hai", "theek hai", "bhej",
        "karo", "talk", "agree", "confirm", "kar do", "haan ji", "sahi hai", "bilkul",
        "हाँ", "श्योर", "ओके", "ओके", "हाँ", "हा", "ठीक है", "ठीक है", "भेज",
        "करो", "टॉक", "एग्री", "कन्फर्म", "कर दो", "हाँ जी", "सही है", "बिल्कुल",
        "यस", "श्योर", "ओके", "ओके", "हाँ", "हा", "ठीक है", "ठीक है", "भेज",
        "करो", "टॉक", "एग्री", "कन्फर्म", "कर दो", "हाँ जी", "सही है", "बिल्कुल"
    ]):
        files = [
            "kia_syros_bot/filler_1_a.raw",
            "kia_syros_bot/filler_1_b.raw",
            "kia_syros_bot/filler_1_c.raw",
            "kia_syros_bot/filler_1_d.raw",
            "kia_syros_bot/filler_1_e.raw",
            "kia_syros_bot/filler_1_f.raw",
            "kia_syros_bot/filler_1_g.raw"
        ]
    # 4. Default / General / Fallback (Category 4)
    else:
        files = [
            "kia_syros_bot/filler_4_a.raw",
            "kia_syros_bot/filler_4_b.raw",
            "kia_syros_bot/filler_4_c.raw",
            "kia_syros_bot/filler_4_d.raw",
            "kia_syros_bot/filler_4_e.raw",
            "kia_syros_bot/filler_4_f.raw",
            "kia_syros_bot/filler_4_g.raw"
        ]

    # No-repetition logic: filter out already played fillers in this session
    played = state.get("played_fillers", [])
    available = [f for f in files if f not in played]
    if not available:
        available = files
        state["played_fillers"] = [p for p in played if p not in files]
        played = state["played_fillers"]

    chosen = random.choice(available)
    played.append(chosen)
    state["played_fillers"] = played
    return chosen


# ─── STREAMING PREPARE / FINALIZE ────────────────────────

def kia_syros_prepare(agent, message, session, detected_language=None, **kwargs):
    state = session.state or {}
    if "conversation_history" not in state:
        state["conversation_history"] = []
    raw_message = _kia_syros_sanitise(message)
    msg = raw_message.lower()
    conversation_history = state["conversation_history"]
    detected_lang = detected_language or "hi"

    # STEP 0: INITIAL GREETING (Turn 1)
    raw_cust_name = state.get("customer_name")
    cust_display_name = raw_cust_name if (raw_cust_name and raw_cust_name != "Sir/Ma'am") else "आप"
    if not state.get("intro_shown"):
        reply = f"Hello, क्या मेरी बात {cust_display_name} से हो रही है?"
        state["intro_shown"] = True
        state["step"] = "greeting"
        state["conversation_history"] = [f"Agent: {reply}"]
        save_session(session, state)
        return {
            "static_reply": reply,
            "tts_language": detected_lang
        }

    # STEP 1 and onwards: DYNAMIC LLM RESPONSES
    exchange_count = state.get("exchange_count", 0)
    exchange_count += 1
    state["exchange_count"] = exchange_count

    conversation_history.append(f"User: {raw_message}")
    if len(conversation_history) > MAX_TURNS:
        conversation_history = conversation_history[-MAX_TURNS:]

    history_text = get_db_history_text(session.session_id)
    system_prompt = KIA_SYROS_SYSTEM_PROMPT.format(customer_name=cust_display_name, history_text=history_text)

    current_step = state.get("step")
    is_identity_confirm = (
        current_step == "greeting"
        and not any(re.search(r'\b' + re.escape(k) + r'\b', msg) for k in ["no", "nahi", "na", "wrong number", "busy"])
    )

    if is_identity_confirm:
        files = [
            "kia_syros_bot/filler_5_a.raw",
            "kia_syros_bot/filler_5_b.raw"
        ]
        state["step"] = "llm_fallback"
        
        played = state.get("played_fillers", [])
        available = [f for f in files if f not in played]
        if not available:
            available = files
            state["played_fillers"] = [p for p in played if p not in files]
            played = state["played_fillers"]
        
        filler_file = random.choice(available)
        played.append(filler_file)
        state["played_fillers"] = played
    else:
        filler_file = select_kia_syros_filler(raw_message, state)
        if current_step == "greeting":
            state["step"] = "llm_fallback"

    filler_text = KIA_SYROS_FILLER_TEXTS.get(filler_file, "")

    if filler_text:
        if is_identity_confirm:
            system_prompt += (
                f"\n\n⚠️ IMPORTANT INSTRUCTION FOR CONTINUATION:\n"
                f"The user has already heard you speak this filler phrase: '{filler_text}'.\n"
                f"You MUST write your response to introduce yourself and the dealership as per step 2 of the guide. "
                f"Do not repeat the filler. Start directly by introducing the dealership (e.g. 'Main Westcoast Kia se bol rahi hoon...')."
            )
        else:
            system_prompt += (
                f"\n\n⚠️ IMPORTANT INSTRUCTION FOR CONTINUATION:\n"
                f"The user has already heard you speak this filler phrase: '{filler_text}'.\n"
                f"You MUST write your response so it continues directly and naturally after this phrase, "
                f"acting as a single coherent statement. Do not repeat the filler, do not use any greetings "
                f"or introductory phrases (like 'Haan', 'Ji', 'Sure', 'Namaste'), and do not start a brand new "
                f"sentence if you can connect it with a conjunction (like 'aur', 'toh', 'isliye'). Start directly with the next word after the filler."
            )

    return {
        "system_prompt": system_prompt,
        "user_message": raw_message,
        "state": state,
        "conversation_history": conversation_history,
        "session": session,
        "play_filler": filler_file,
        "skip_input_translation": True,
        "skip_output_translation": True,
        "translate_input_to": "original",
        "tts_language": detected_lang,
    }

def kia_syros_finalize(response, prep_result):
    state = prep_result["state"]
    session = prep_result["session"]
    conversation_history = prep_result["conversation_history"]

    conversation_history.append(f"Agent: {response}")
    state["conversation_history"] = conversation_history
    state["last_bot_message"] = response
    save_session(session, state)
