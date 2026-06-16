import logging
from typing import Dict, Any
from .prompts import LOAN_SYSTEM_PROMPT, get_loan_lang_instruction
from conversations.services.core.strategies import save_session, build_history_text, is_farewell

logger = logging.getLogger("LoanBotStrategy")

# Constants
MAX_MESSAGE_LENGTH = 1000
MAX_TURNS = 10

def _loan_sanitise(message: str) -> str:
    return message.strip()[:MAX_MESSAGE_LENGTH]

# ─── NON-STREAMING (text fallback) ───────────────────────

def loan_bot_strategy(agent, message, session, **kwargs):
    state: dict = session.state or {}
    raw_message = _loan_sanitise(message)
    msg = raw_message.lower()
    conversation_history: list = state.get("conversation_history", [])

    if is_farewell(msg):
        save_session(session, {})
        return "Thank you for giving your time. Have a nice day! [END_CALL]"

    if not state.get("intro_shown"):
        reply = (
            "Hello! Main JMS Bank se bol rahi hoon. Hum kai tarah ke loans provide karte hain. "
            "Kya aap loan lene mein interested hain?"
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

    detected_lang = state.get("detected_language", "hi")
    lang_instruction = get_loan_lang_instruction(detected_lang)

    system_prompt = LOAN_SYSTEM_PROMPT.format(
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

def loan_bot_prepare(agent, message, session, detected_language=None, **kwargs):
    state = session.state or {}
    raw_message = _loan_sanitise(message)
    msg = raw_message.lower()
    conversation_history = state.get("conversation_history", [])

    if detected_language:
        state["detected_language"] = detected_language

    # FAREWELL
    if is_farewell(msg):
        save_session(session, {})
        return {
            "static_reply": "Thank you for giving your time. Have a nice day! [END_CALL]",
            "tts_language": detected_language or "hi"
        }

    # INTRO
    if not state.get("intro_shown"):
        reply = "Hello! Main JMS Bank se bol rahi hoon. Hum kai tarah ke loans provide karte hain. Kya aap loan lene mein interested hain?"
        state["intro_shown"] = True
        state["call_phase"] = "interest_confirmation"
        state["conversation_history"] = [f"Agent: {reply}"]
        save_session(session, state)
        return {
            "static_reply": "[PLAY_AUDIO:loan_bot/loan_step1_greeting.raw]",
            "tts_language": detected_language or "hi"
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

    detected_lang = state.get("detected_language", "hi")
    lang_instruction = get_loan_lang_instruction(detected_lang)

    system_prompt = LOAN_SYSTEM_PROMPT.format(
        language_instruction=lang_instruction,
        history_text=history_text,
    )

    current_phase = state.get("call_phase", "interest_confirmation")

    # If the request comes with a static bypass (e.g. matching an audio file directly)
    # the consumer might handle it, but we can also handle the fallback instructions:
    if current_phase == "interest_confirmation":
        yes_keywords = ["yes", "haan", "yeah", "ok", "confirm", "sure", "please", "हाँ", "हा", "हाँ जी", "कर दो", "कर दीजिए", "interested", "chahiye"]
        no_keywords = ["no", "na", "nahi", "cancel", "stop", "نહીં", "નથી", "નહિ", "नही", "नहीं", "ना", "ના", "નાના", "not interested", "nahi chahiye"]

        if any(no in msg for no in no_keywords):
            save_session(session, {}) # clear session
            return {
                "static_reply": "[PLAY_AUDIO:loan_bot/loan_step_rejection.raw] [END_CALL]",
                "tts_language": detected_lang,
                "auto_disconnect": True,
                "skip_name_collection": True
            }
        elif any(yes in msg for yes in yes_keywords):
            state["call_phase"] = "discover_loan_type"
            save_session(session, state)
            return {
                "static_reply": "[PLAY_AUDIO:loan_bot/loan_step2_discover_type.raw]",
                "tts_language": detected_lang
            }
        else:
            # Fallback to LLM if user response is ambiguous
            system_prompt += (
                "\n\n🚨 USER RESPONSE TO LOAN INTEREST GREETING 🚨\n"
                "Determine if the user is interested in a loan. If yes, explain our loan types and ask what they need.\n"
                "If no, thank them and say goodbye with the [END_CALL] tag.\n"
            )

    elif current_phase == "discover_loan_type":
        # Check if the user specified a loan type (e.g. home, business, personal, car)
        # We can extract details via LLM or just transition.
        state["call_phase"] = "collect_amount"
        state["loan_type"] = raw_message
        save_session(session, state)
        return {
            "static_reply": "[PLAY_AUDIO:loan_bot/loan_step3_discover_amount.raw]",
            "tts_language": detected_lang
        }

    elif current_phase == "collect_amount":
        state["loan_amount"] = raw_message
        state["call_phase"] = "closing"
        save_session(session, state)
        return {
            "static_reply": "[PLAY_AUDIO:loan_bot/loan_step4_closing.raw] [BOOKING_CONFIRMED] [END_CALL]",
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

def loan_bot_finalize(response, prep_result):
    state = prep_result["state"]
    session = prep_result["session"]
    conversation_history = prep_result["conversation_history"]

    conversation_history.append(f"Agent: {response}")
    state["conversation_history"] = conversation_history
    state["last_bot_message"] = response
    save_session(session, state)
