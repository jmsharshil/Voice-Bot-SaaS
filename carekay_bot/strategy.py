import logging
from typing import Dict, Any
from .prompts import CAREKAY_SYSTEM_PROMPT, get_carekay_lang_instruction
from conversations.services.core.strategies import save_session, build_history_text, is_farewell

logger = logging.getLogger("CarekayBotStrategy")

# Constants
MAX_MESSAGE_LENGTH = 1000
MAX_TURNS = 10

def _carekay_sanitise(message: str) -> str:
    return message.strip()[:MAX_MESSAGE_LENGTH]

# ─── NON-STREAMING (text fallback) ───────────────────────

def carekay_strategy(agent, message, session, **kwargs):
    state: dict = session.state or {}
    raw_message = _carekay_sanitise(message)
    msg = raw_message.lower()
    conversation_history: list = state.get("conversation_history", [])

    if is_farewell(msg):
        save_session(session, {})
        return "આવજો! [END_CALL]"

    if not state.get("intro_shown"):
        reply = (
            "હલો, નમસ્તે જી! હું કેરકે ઇન્શ્યોરન્સમાંથી કેય વાત કરું છું. તમારી ગાડીનો મોટર ઇન્શ્યોરન્સ આવતા અઠવાડિયે એક્સપાયર થઈ રહ્યો છે. તો શું તમારી સાથે ૨ મિનિટ વાત થઈ શકે?"
        )
        state["intro_shown"] = True
        state["call_phase"] = "greeting"
        state["conversation_history"] = [f"Agent: {reply}"]
        save_session(session, state)
        return reply

    conversation_history.append(f"User: {raw_message}")
    if len(conversation_history) > MAX_TURNS:
        conversation_history = conversation_history[-MAX_TURNS:]

    history_text = build_history_text(conversation_history)

    detected_lang = state.get("detected_language", "gu")
    lang_instruction = get_carekay_lang_instruction(detected_lang)

    system_prompt = CAREKAY_SYSTEM_PROMPT.format(
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

def carekay_prepare(agent, message, session, detected_language=None, **kwargs):
    state = session.state or {}
    raw_message = _carekay_sanitise(message)
    msg = raw_message.lower()
    conversation_history = state.get("conversation_history", [])

    if detected_language:
        state["detected_language"] = detected_language

    # FAREWELL
    if is_farewell(msg):
        save_session(session, {})
        return {
            "static_reply": "આવજો! [END_CALL]",
            "tts_language": "gu"
        }

    # INTRO
    if not state.get("intro_shown"):
        reply = "હલો, નમસ્તે જી! હું કેરકે ઇન્શ્યોરન્સમાંથી કેય વાત કરું છું. તમારી ગાડીનો મોટર ઇન્શ્યોરન્સ આવતા અઠવાડિયે એક્સપાયર થઈ રહ્યો છે. તો શું તમારી સાથે ૨ મિનિટ વાત થઈ શકે?"
        state["intro_shown"] = True
        state["call_phase"] = "greeting"
        state["conversation_history"] = [f"Agent: {reply}"]
        save_session(session, state)
        return {
            "static_reply": "[PLAY_AUDIO:carekay_bot/carekay_step1_greeting.raw]",
            "tts_language": "gu"
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
    lang_instruction = get_carekay_lang_instruction(detected_lang)

    system_prompt = CAREKAY_SYSTEM_PROMPT.format(
        language_instruction=lang_instruction,
        history_text=history_text,
    )

    current_phase = state.get("call_phase", "greeting")

    # Define common negative keywords
    negative_keywords = [
        "no", "nah", "nope", "not", "won't", "cant", "can't", "delay", "busy", "never", "cancel", "stop", "dont",
        "nahi", "na", "baad mein", "abhi nahi", "wrong number", "busy hoon", "meeting",
        "નથી", "ના", "નહીં", "નથી લેવી", "પૈસા નથી", "વ્યસ્ત છું", "પછી", "ના ભાઈ", "ના જી", "ખોટો નંબર", "ખોટો ફોન",
        "નથી જોઈતું", "નથી કરવું", "વાત નથી કરવી", "અત્યારે નહીં"
    ]

    # Define positive/confirmation keywords
    positive_keywords = [
        "yes", "sure", "yeah", "ok", "okay", "send", "tell",
        "haan", "boliye", "kahiye", "haan bolo", "bhejo",
        "હા", "હા બોલો", "બોલો", "કેમ છો", "હા કહો", "હાજી", "મોકલો", "ભલે", "ભલે મોકલી દો", "હા મોકલો", "ચોક્કસ"
    ]

    if current_phase == "greeting":
        if any(neg in msg for neg in negative_keywords):
            save_session(session, {}) # clear session
            return {
                "static_reply": "[PLAY_AUDIO:carekay_bot/carekay_rejection.raw] [END_CALL]",
                "tts_language": "gu",
                "auto_disconnect": True,
                "skip_name_collection": True
            }
        elif any(pos in msg for pos in positive_keywords):
            state["call_phase"] = "ask_whatsapp"
            save_session(session, state)
            return {
                "static_reply": "[PLAY_AUDIO:carekay_bot/carekay_step2_ask_whatsapp.raw]",
                "tts_language": "gu"
            }

    elif current_phase == "ask_whatsapp":
        if any(neg in msg for neg in negative_keywords):
            save_session(session, {}) # clear session
            return {
                "static_reply": "[PLAY_AUDIO:carekay_bot/carekay_rejection.raw] [END_CALL]",
                "tts_language": "gu",
                "auto_disconnect": True,
                "skip_name_collection": True
            }
        elif any(pos in msg for pos in positive_keywords):
            state["call_phase"] = "closing"
            save_session(session, state)
            return {
                "static_reply": "[PLAY_AUDIO:carekay_bot/carekay_step3_closing.raw] [BOOKING_CONFIRMED] [END_CALL]",
                "tts_language": "gu",
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
        "tts_language": "gu",
    }

def carekay_finalize(response, prep_result):
    state = prep_result["state"]
    session = prep_result["session"]
    conversation_history = prep_result["conversation_history"]

    conversation_history.append(f"Agent: {response}")
    state["conversation_history"] = conversation_history
    state["last_bot_message"] = response
    save_session(session, state)
