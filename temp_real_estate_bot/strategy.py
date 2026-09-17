import logging
from typing import Dict, Any
from .prompts import REAL_ESTATE_SYSTEM_PROMPT, get_real_estate_lang_instruction
from conversations.services.core.strategies import save_session, build_history_text, is_farewell

logger = logging.getLogger("TempRealEstateBotStrategy")

# Constants
MAX_MESSAGE_LENGTH = 1000
MAX_TURNS = 10

def _real_estate_sanitise(message: str) -> str:
    return message.strip()[:MAX_MESSAGE_LENGTH]

# ─── NON-STREAMING (text fallback) ───────────────────────

def temp_real_estate_strategy(agent, message, session, **kwargs):
    state: dict = session.state or {}
    raw_message = _real_estate_sanitise(message)
    msg = raw_message.lower()
    conversation_history: list = state.get("conversation_history", [])

    if is_farewell(msg):
        save_session(session, {})
        return "આવજો! [END_CALL]"

    if not state.get("intro_shown"):
        reply = (
            "હલો, નમસ્તે જી! હું જે એમ એસ રિયલ એસ્ટેટ તરફથી નવ્યા વાત કરું છું. અમે અત્યારે ખૂબ જ સરસ લોકેશન પર લક્ઝુરિયસ ફ્લેટ્સ વેચી રહ્યા છીએ. તો મને જણાવશો ને, તમારે કયા પ્રકારનો ફ્લેટ જોઈએ છે, જેમ કે વન બીએચકે કે ટુ બીએચકે?"
        )
        state["intro_shown"] = True
        state["call_phase"] = "collect_flat_type"
        state["conversation_history"] = [f"Agent: {reply}"]
        save_session(session, state)
        return reply

    conversation_history.append(f"User: {raw_message}")
    if len(conversation_history) > MAX_TURNS:
        conversation_history = conversation_history[-MAX_TURNS:]

    history_text = build_history_text(conversation_history)

    detected_lang = state.get("detected_language", "gu")
    lang_instruction = get_real_estate_lang_instruction(detected_lang)

    system_prompt = REAL_ESTATE_SYSTEM_PROMPT.format(
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

def temp_real_estate_prepare(agent, message, session, detected_language=None, **kwargs):
    state = session.state or {}
    raw_message = _real_estate_sanitise(message)
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
        reply = "હલો, નમસ્તે જી! હું જે એમ એસ રિયલ એસ્ટેટ તરફથી નવ્યા વાત કરું છું. અમે અત્યારે ખૂબ જ સરસ લોકેશન પર લક્ઝુરિયસ ફ્લેટ્સ વેચી રહ્યા છીએ. તો મને જણાવશો ને, તમારે કયા પ્રકારનો ફ્લેટ જોઈએ છે, જેમ કે વન બીએચકે કે ટુ બીએચકે?"
        state["intro_shown"] = True
        state["call_phase"] = "collect_flat_type"
        state["conversation_history"] = [f"Agent: {reply}"]
        save_session(session, state)
        return {
            "static_reply": "[PLAY_AUDIO:temp_real_estate_bot/real_estate_step1_greeting.raw]",
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
    lang_instruction = get_real_estate_lang_instruction(detected_lang)

    system_prompt = REAL_ESTATE_SYSTEM_PROMPT.format(
        language_instruction=lang_instruction,
        history_text=history_text,
    )

    current_phase = state.get("call_phase", "collect_flat_type")

    if current_phase == "collect_flat_type":
        state["flat_type"] = raw_message
        state["call_phase"] = "collect_area"
        save_session(session, state)
        return {
            "static_reply": "[PLAY_AUDIO:temp_real_estate_bot/real_estate_step2_ask_area.raw]",
            "tts_language": detected_lang
        }

    elif current_phase == "collect_area":
        state["area"] = raw_message
        state["call_phase"] = "collect_budget"
        save_session(session, state)
        return {
            "static_reply": "[PLAY_AUDIO:temp_real_estate_bot/real_estate_step3_ask_budget.raw]",
            "tts_language": detected_lang
        }

    elif current_phase == "collect_budget":
        state["budget"] = raw_message
        state["call_phase"] = "collect_name"
        save_session(session, state)
        return {
            "static_reply": "[PLAY_AUDIO:temp_real_estate_bot/real_estate_step4_ask_name.raw]",
            "tts_language": detected_lang
        }

    elif current_phase == "collect_name":
        state["user_name"] = raw_message
        state["call_phase"] = "closing"
        save_session(session, state)
        return {
            "static_reply": "[PLAY_AUDIO:temp_real_estate_bot/real_estate_step5_closing.raw] [END_CALL]",
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

def temp_real_estate_finalize(response, prep_result):
    state = prep_result["state"]
    session = prep_result["session"]
    conversation_history = prep_result["conversation_history"]

    conversation_history.append(f"Agent: {response}")
    state["conversation_history"] = conversation_history
    state["last_bot_message"] = response
    save_session(session, state)
