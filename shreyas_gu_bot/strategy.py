# shreyas_gu_bot/strategy.py

import logging
import re
import random
from .prompts import SHREYAS_GU_SYSTEM_PROMPT
from conversations.services.core.strategies import save_session

logger = logging.getLogger("ShreyasGuBotStrategy")

MAX_MESSAGE_LENGTH = 1000
MAX_TURNS = 10

def _shreyas_gu_sanitise(message: str) -> str:
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
        logger.error(f"Error building database history for Shreyas Gu: {e}")
    return ""

# ─── NON-STREAMING (text fallback) ───────────────────────

def shreyas_gu_strategy(agent, message, session, **kwargs):
    state: dict = session.state or {}
    raw_message = _shreyas_gu_sanitise(message)
    msg = raw_message.lower()
    conversation_history: list = state.get("conversation_history", [])

    if any(w in msg for w in ["bye", "goodbye", "exit", "quit", "see you", "આવજો", "બાય"]):
        save_session(session, {})
        return "શ્રેયસ ફાઉન્ડેશનમાં કોલ કરવા બદલ આભાર. તમારો દિવસ શુભ રહે! [END_CALL]"

    if not state.get("intro_shown"):
        reply = (
            "નમસ્તે જી! શ્રેયસ ફાઉન્ડેશન સ્પોર્ટ્સ એક્ટિવિટીઝમાં તમારું ખૂબ ખૂબ સ્વાગત છે. અમારે ત્યાં બાળકો માટે ઘોડેસવારી, સ્કેટિંગ, ફૂટબોલ અને પર્સનાલિટી ડેવલપમેન્ટ જેવા સરસ પ્રોગ્રામ્સ ચાલે છે. તો તમારા બાળકને આમાંથી શેમાં રસ છે?"
        )
        state["intro_shown"] = True
        state["conversation_history"] = [f"Agent: {reply}"]
        save_session(session, state)
        return reply

    conversation_history.append(f"User: {raw_message}")
    if len(conversation_history) > MAX_TURNS:
        conversation_history = conversation_history[-MAX_TURNS:]

    history_text = get_db_history_text(session.session_id)
    system_prompt = SHREYAS_GU_SYSTEM_PROMPT.format(history_text=history_text)

    from conversations.services.azure_openai_service import generate_response
    response = generate_response(system_prompt, raw_message)

    conversation_history.append(f"Agent: {response}")
    state["conversation_history"] = conversation_history
    state["last_bot_message"] = response
    save_session(session, state)

    return response

# ─── STREAMING PREPARE / FINALIZE ────────────────────────

def select_smart_gu_filler(user_msg: str) -> str:
    msg = user_msg.lower()
    
    # 1. Program Selection keywords
    program_keywords = [
        "horse", "riding", "skate", "skating", "foot", "football", "life", "skill", "skills", "comm", "communication",
        "ઘોડેસવારી", "હોર્સ", "રાઇડિંગ", "સ્કેટિંગ", "સ્કેટ", "ફૂટબોલ", "જીવન", "કૌશલ્ય", "સ્કિલ", "સ્કિલ્સ", "સંવાદ", "કોમ્યુનિકેશન","ઘોડે જવાહારી","ઘોડેસવારી","ઘોડે"
    ]
    if any(k in msg for k in program_keywords):
        return random.choice([
            "shreyas_gu_bot/filler_1_a.raw",
            "shreyas_gu_bot/filler_1_b.raw",
            "shreyas_gu_bot/filler_1_c.raw",
            "shreyas_gu_bot/filler_1_d.raw",
            "shreyas_gu_bot/filler_1_e.raw"
        ])
        
    # 2. Age / Timing
    age_keywords = [
        "years", "old", "age", "timing", "timings", "batch", "schedule", "schedules", "time",
        "વર્ષ", "ઉંમર", "સમય", "બેચ", "સાંજ", "સાંજે", "શેડ્યૂલ", "દિવસ"
    ]
    has_digit = any(char.isdigit() for char in msg)
    if has_digit or any(k in msg for k in age_keywords):
        return random.choice([
            "shreyas_gu_bot/filler_2_a.raw",
            "shreyas_gu_bot/filler_2_b.raw",
            "shreyas_gu_bot/filler_2_c.raw",
            "shreyas_gu_bot/filler_2_d.raw",
            "shreyas_gu_bot/filler_2_e.raw"
        ])
        
    # 3. WhatsApp / Consent
    consent_keywords = [
        "yes", "please", "send", "sure", "ok", "okay", "whatsapp", "fine", "yeah", "agree", "confirm",
        "હા", "હાજી", "મોકલો", "મોકલી", "સારું", "બરાબર", "વોટ્સએપ", "ચોક્કસ"
    ]
    if any(k in msg for k in consent_keywords):
        return random.choice([
            "shreyas_gu_bot/filler_3_a.raw",
            "shreyas_gu_bot/filler_3_b.raw",
            "shreyas_gu_bot/filler_3_c.raw",
            "shreyas_gu_bot/filler_3_d.raw",
            "shreyas_gu_bot/filler_3_e.raw"
        ])
        
    # 4. Question / Inquiry / General questions
    question_keywords = [
        "what", "where", "why", "how", "when", "who", "fee", "fees", "cost", "price", "prices", "school", "principal", "campus",
        "શું", "ક્યાં", "કેમ", "કેવી", "કેવો", "ક્યારે", "કોણ", "ફી", "ચાર્જ", "કિંમત", "સ્કૂલ", "શાળા", "આચાર્ય"
    ]
    if any(k in msg for k in question_keywords) or "?" in msg:
        return random.choice([
            "shreyas_gu_bot/filler_4_a.raw",
            "shreyas_gu_bot/filler_4_b.raw",
            "shreyas_gu_bot/filler_4_c.raw",
            "shreyas_gu_bot/filler_4_d.raw",
            "shreyas_gu_bot/filler_4_e.raw"
        ])
        
    # 5. Default/Fallback
    return random.choice([
        "shreyas_gu_bot/filler_5_a.raw",
        "shreyas_gu_bot/filler_5_b.raw",
        "shreyas_gu_bot/filler_5_c.raw",
        "shreyas_gu_bot/filler_5_d.raw",
        "shreyas_gu_bot/filler_5_e.raw"
    ])

def shreyas_gu_prepare(agent, message, session, detected_language=None, **kwargs):
    state = session.state or {}
    raw_message = _shreyas_gu_sanitise(message)
    msg = raw_message.lower()
    conversation_history = state.get("conversation_history", [])
    detected_lang = detected_language or "gu"

    # FAREWELL
    if any(w in msg for w in ["bye", "goodbye", "exit", "quit", "see you", "આવજો", "બાય"]):
        save_session(session, {})
        return {
            "static_reply": "શ્રેયસ ફાઉન્ડેશનમાં કોલ કરવા બદલ આભાર. તમારો દિવસ શુભ રહે! [END_CALL]",
            "tts_language": detected_lang,
            "auto_disconnect": True
        }

    # INTRO
    if not state.get("intro_shown"):
        reply = (
            "નમસ્તે જી! શ્રેયસ ફાઉન્ડેશન સ્પોર્ટ્સ એક્ટિવિટીઝમાં તમારું ખૂબ ખૂબ સ્વાગત છે. અમારે ત્યાં બાળકો માટે ઘોડેસવારી, સ્કેટિંગ, ફૂટબોલ અને પર્સનાલિટી ડેવલપમેન્ટ જેવા સરસ પ્રોગ્રામ્સ ચાલે છે. તો તમારા બાળકને આમાંથી શેમાં રસ છે?"
        )
        state["intro_shown"] = True
        state["conversation_history"] = [f"Agent: {reply}"]
        save_session(session, state)
        return {
            "static_reply": "[PLAY_AUDIO:shreyas_gu_bot/shreyas_gu_step1_greeting.raw]",
            "tts_language": detected_lang
        }

    # UPDATE COUNTER
    exchange_count = state.get("exchange_count", 0)
    exchange_count += 1
    state["exchange_count"] = exchange_count

    conversation_history.append(f"User: {raw_message}")
    if len(conversation_history) > MAX_TURNS:
        conversation_history = conversation_history[-MAX_TURNS:]

    history_text = get_db_history_text(session.session_id)
    system_prompt = SHREYAS_GU_SYSTEM_PROMPT.format(history_text=history_text)

    # Select a smart context-matching filler file to play before LLM stream starts
    filler_file = select_smart_gu_filler(raw_message)

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

def shreyas_gu_finalize(response, prep_result):
    state = prep_result["state"]
    session = prep_result["session"]
    conversation_history = prep_result["conversation_history"]

    conversation_history.append(f"Agent: {response}")
    state["conversation_history"] = conversation_history
    state["last_bot_message"] = response
    save_session(session, state)
