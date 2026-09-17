import logging
from typing import Dict, Any
from .prompts import REMINDER_SYSTEM_PROMPT, get_reminder_lang_instruction
from conversations.services.core.strategies import save_session, build_history_text, is_farewell

logger = logging.getLogger("ReminderBotStrategy")

# Constants
MAX_MESSAGE_LENGTH = 1000
MAX_TURNS = 10

def _reminder_sanitise(message: str) -> str:
    return message.strip()[:MAX_MESSAGE_LENGTH]

# ─── NON-STREAMING (text fallback) ───────────────────────

def reminder_bot_strategy(agent, message, session, **kwargs):
    state: dict = session.state or {}
    raw_message = _reminder_sanitise(message)
    msg = raw_message.lower()
    conversation_history: list = state.get("conversation_history", [])

    if is_farewell(msg):
        save_session(session, {})
        return "આવજો! [END_CALL]"

    if not state.get("intro_shown"):
        reply = (
            "નમસ્તે! હું જે એમ એસ બેંકમાંથી નવ્યા બોલું છું. તમારી ઈ એમ આઈ ની તારીખ નજીક છે, તમે ક્યારે ચુકવણી કરશો?"
        )
        state["intro_shown"] = True
        state["call_phase"] = "interest_confirmation"
        state["conversation_history"] = [f"Agent: {reply}"]
        save_session(session, state)
        return reply

    conversation_history.append(f"User: {raw_message}")
    if len(conversation_history) > MAX_TURNS:
        conversation_history = conversation_history[-MAX_TURNS:]

    history_text = build_history_text(conversation_history)

    detected_lang = state.get("detected_language", "gu")
    lang_instruction = get_reminder_lang_instruction(detected_lang)

    system_prompt = REMINDER_SYSTEM_PROMPT.format(
        language_instruction=lang_instruction,
        history_text=history_text,
    )

    from conversations.services.azure_openai_service import generate_response
    response = generate_response(system_prompt, raw_message)

    conversation_history.append(f"Agent: {response}")
    state["conversation_history"] = conversation_history
    state["last_bot_message"] = response
    save_session(session, state)

    return response

# ─── STREAMING PREPARE / FINALIZE ────────────────────────

def reminder_bot_prepare(agent, message, session, detected_language=None, **kwargs):
    state = session.state or {}
    raw_message = _reminder_sanitise(message)
    msg = raw_message.lower()
    conversation_history = state.get("conversation_history", [])

    if detected_language:
        state["detected_language"] = detected_language

    # FAREWELL
    if is_farewell(msg):
        save_session(session, {})
        return {
            "static_reply": "આવજો! [END_CALL]",
            "tts_language": detected_language or "gu"
        }

    # INTRO
    if not state.get("intro_shown"):
        reply = "નમસ્તે! હું જે એમ એસ બેંકમાંથી નવ્યા બોલું છું. તમારી ઈ એમ આઈ ની તારીખ નજીક છે, તમે ક્યારે ચુકવણી કરશો?"
        state["intro_shown"] = True
        state["call_phase"] = "interest_confirmation"
        state["conversation_history"] = [f"Agent: {reply}"]
        save_session(session, state)
        return {
            "static_reply": "[PLAY_AUDIO:reminder_bot/reminder_step1_greeting.raw]",
            "tts_language": detected_language or "gu"
        }

    # UPDATE COUNTER
    exchange_count = state.get("exchange_count", 0)
    exchange_count += 1
    state["exchange_count"] = exchange_count

    # HISTORY BUILD
    conversation_history.append(f"User: {raw_message}")
    if len(conversation_history) > MAX_TURNS:
        conversation_history = conversation_history[-MAX_TURNS:]

    history_text = build_history_text(conversation_history)

    detected_lang = state.get("detected_language", "gu")
    lang_instruction = get_reminder_lang_instruction(detected_lang)

    system_prompt = REMINDER_SYSTEM_PROMPT.format(
        language_instruction=lang_instruction,
        history_text=history_text,
    )

    current_phase = state.get("call_phase", "interest_confirmation")

    if current_phase == "interest_confirmation":
        # Check negative keywords in Gujarati, Hindi and English
        negative_keywords = [
            "no", "nah", "nope", "not", "won't", "cant", "can't", "delay", "busy", "never",
            "nahi", "na", "nahi dunga", "paise nahi hai", "baad mein", "abhi nahi", "wrong number",
            "નથી", "ના", "નહીં", "નથી લેવી", "નથી ચૂકવવી", "પૈસા નથી", "વ્યસ્ત છું", "પછી", "ના ભાઈ"
        ]

        if any(neg in msg for neg in negative_keywords):
            save_session(session, {}) # clear session
            return {
                "static_reply": "[PLAY_AUDIO:reminder_bot/reminder_step_rejection.raw] [END_CALL]",
                "tts_language": detected_lang,
                "auto_disconnect": True,
                "skip_name_collection": True
            }
        else:
            state["call_phase"] = "ask_payment_mode"
            save_session(session, state)
            return {
                "static_reply": "[PLAY_AUDIO:reminder_bot/reminder_step2_ask_mode.raw]",
                "tts_language": detected_lang
            }

    elif current_phase == "ask_payment_mode":
        state["payment_mode"] = raw_message
        state["call_phase"] = "closing"
        save_session(session, state)
        return {
            "static_reply": "[PLAY_AUDIO:reminder_bot/reminder_step3_closing.raw] [BOOKING_CONFIRMED] [END_CALL]",
            "tts_language": detected_lang,
            "auto_disconnect": True,
            "skip_name_collection": True
        }

    return {
        "system_prompt": system_prompt,
        "user_message": raw_message,
        "state": state,
        "conversation_history": conversation_history,
        "session": session,
        "skip_input_translation": True,
        "skip_output_translation": True,
        "translate_input_to": "original",
        "tts_language": detected_lang,
    }

def reminder_bot_finalize(response, prep_result):
    state = prep_result["state"]
    session = prep_result["session"]
    conversation_history = prep_result["conversation_history"]

    conversation_history.append(f"Agent: {response}")
    state["conversation_history"] = conversation_history
    state["last_bot_message"] = response
    save_session(session, state)
