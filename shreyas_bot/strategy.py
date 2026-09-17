# shreyas_bot/strategy.py

import logging
import re
import random
from .prompts import SHREYAS_SYSTEM_PROMPT
from conversations.services.core.strategies import save_session

logger = logging.getLogger("ShreyasBotStrategy")

MAX_MESSAGE_LENGTH = 1000
MAX_TURNS = 10

def _shreyas_sanitise(message: str) -> str:
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
        logger.error(f"Error building database history for Shreyas: {e}")
    return ""

# ─── NON-STREAMING (text fallback) ───────────────────────

def shreyas_strategy(agent, message, session, **kwargs):
    state: dict = session.state or {}
    raw_message = _shreyas_sanitise(message)
    msg = raw_message.lower()
    conversation_history: list = state.get("conversation_history", [])

    if any(w in msg for w in ["bye", "goodbye", "exit", "quit", "see you"]):
        save_session(session, {})
        return "Thank you for calling Shreyas Foundation. Have a wonderful day! [END_CALL]"

    if not state.get("intro_shown"):
        reply = (
            "namaste, Welcome to Shreyas Foundation Sports & Outreach Programs — we offer horse riding, skating, football, life-skills, and communication programs, open to all. Which one would your child like to try?"
        )
        state["intro_shown"] = True
        state["conversation_history"] = [f"Agent: {reply}"]
        save_session(session, state)
        return reply

    conversation_history.append(f"User: {raw_message}")
    if len(conversation_history) > MAX_TURNS:
        conversation_history = conversation_history[-MAX_TURNS:]

    history_text = get_db_history_text(session.session_id)
    system_prompt = SHREYAS_SYSTEM_PROMPT.format(history_text=history_text)

    from conversations.services.azure_openai_service import generate_response
    response = generate_response(system_prompt, raw_message)

    conversation_history.append(f"Agent: {response}")
    state["conversation_history"] = conversation_history
    state["last_bot_message"] = response
    save_session(session, state)

    return response

# ─── SMART FILLERS SELECTION ─────────────────────────────

def select_smart_filler(user_msg: str) -> str:
    msg = user_msg.lower()
    
    # 1. Program Selection keywords
    program_keywords = ["horse", "riding", "skate", "skating", "foot", "football", "life", "skill", "skills", "comm", "communication"]
    if any(k in msg for k in program_keywords):
        return random.choice([
            "shreyas_bot/filler_1_a.raw",
            "shreyas_bot/filler_1_b.raw",
            "shreyas_bot/filler_1_c.raw",
            "shreyas_bot/filler_1_d.raw",
            "shreyas_bot/filler_1_e.raw"
        ])
        
    # 2. Age / Timing
    age_keywords = ["years", "old", "age", "timing", "timings", "batch", "schedule", "schedules", "time"]
    has_digit = any(char.isdigit() for char in msg)
    if has_digit or any(k in msg for k in age_keywords):
        return random.choice([
            "shreyas_bot/filler_2_a.raw",
            "shreyas_bot/filler_2_b.raw",
            "shreyas_bot/filler_2_c.raw",
            "shreyas_bot/filler_2_d.raw",
            "shreyas_bot/filler_2_e.raw"
        ])
        
    # 3. WhatsApp / Consent
    consent_keywords = ["yes", "please", "send", "sure", "ok", "okay", "whatsapp", "fine", "yeah", "agree", "confirm"]
    if any(k in msg for k in consent_keywords):
        return random.choice([
            "shreyas_bot/filler_3_a.raw",
            "shreyas_bot/filler_3_b.raw",
            "shreyas_bot/filler_3_c.raw",
            "shreyas_bot/filler_3_d.raw",
            "shreyas_bot/filler_3_e.raw"
        ])
        
    # 4. Question / Inquiry / General questions
    question_keywords = ["what", "where", "why", "how", "when", "who", "fee", "fees", "cost", "price", "prices", "school", "principal", "campus"]
    if any(k in msg for k in question_keywords) or "?" in msg:
        return random.choice([
            "shreyas_bot/filler_4_a.raw",
            "shreyas_bot/filler_4_b.raw",
            "shreyas_bot/filler_4_c.raw",
            "shreyas_bot/filler_4_d.raw",
            "shreyas_bot/filler_4_e.raw"
        ])
        
    # 5. Default/Fallback
    return random.choice([
        "shreyas_bot/filler_5_a.raw",
        "shreyas_bot/filler_5_b.raw",
        "shreyas_bot/filler_5_c.raw",
        "shreyas_bot/filler_5_d.raw",
        "shreyas_bot/filler_5_e.raw"
    ])


# ─── STREAMING PREPARE / FINALIZE ────────────────────────

def shreyas_prepare(agent, message, session, detected_language=None, **kwargs):
    state = session.state or {}
    raw_message = _shreyas_sanitise(message)
    msg = raw_message.lower()
    conversation_history = state.get("conversation_history", [])
    detected_lang = detected_language or "en"

    # FAREWELL
    if any(w in msg for w in ["bye", "goodbye", "exit", "quit", "see you"]):
        save_session(session, {})
        return {
            "static_reply": "Thank you for calling Shreyas Foundation. Have a wonderful day! [END_CALL]",
            "tts_language": detected_lang,
            "auto_disconnect": True
        }

    # INTRO
    if not state.get("intro_shown"):
        reply = (
            "namaste, Welcome to Shreyas Foundation Sports & Outreach Programs — we offer horse riding, skating, football, life-skills, and communication programs, open to all. Which one would your child like to try?"
        )
        state["intro_shown"] = True
        state["conversation_history"] = [f"Agent: {reply}"]
        save_session(session, state)
        return {
            "static_reply": "[PLAY_AUDIO:shreyas_bot/shreyas_step1_greeting.raw]",
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
    system_prompt = SHREYAS_SYSTEM_PROMPT.format(history_text=history_text)

    # Select a smart context-matching filler file to play before LLM stream starts
    filler_file = select_smart_filler(raw_message)

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

def shreyas_finalize(response, prep_result):
    state = prep_result["state"]
    session = prep_result["session"]
    conversation_history = prep_result["conversation_history"]

    conversation_history.append(f"Agent: {response}")
    state["conversation_history"] = conversation_history
    state["last_bot_message"] = response
    save_session(session, state)
