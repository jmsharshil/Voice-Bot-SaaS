import re
from conversations.services.core.strategies import save_session

def hospital_minimal_strategy(agent, message, session, **kwargs):
    res = hospital_minimal_prepare(agent, message, session, **kwargs)
    return res.get("static_reply", "Sorry, could you please repeat?")

def hospital_minimal_prepare(agent, message, session, **kwargs):
    state = session.state or {}
    raw_message = message.lower().strip()

    # 1. Start - Play greeting
    if not state.get("intro_shown"):
        state["intro_shown"] = True
        state["step"] = "confirm_interest"
        save_session(session, state)
        return {
            "static_reply": "[PLAY_AUDIO:hosp_step1_greeting.raw]",
            "tts_language": "en",
            "session": session,
            "state": state
        }

    current_step = state.get("step")
    if not current_step:
        current_step = "confirm_interest"
        state["step"] = "confirm_interest"

    # 2. Handle Greeting Response
    if current_step == "confirm_interest":
        yes_keywords = ["yes", "haan", "yeah", "ok", "confirm", "sure", "please", "येस", "हाँ", "हा", "हाँ जी", "જી", "હા", "ચોક્કસ", "कर दो", "कर दीजिए"]
        no_keywords = ["no", "na", "nahi", "cancel", "stop", "નહીં", "નથી", "નહિ", "नही", "नहीं", "ना", "ના", "નાના", "cancel"]

        if any(yes in raw_message for yes in yes_keywords):
            state["step"] = "select_slot"
            save_session(session, state)
            return {
                "static_reply": "[PLAY_AUDIO:hosp_step2_ask_slot.raw]",
                "tts_language": "en",
                "session": session,
                "state": state
            }
        elif any(no in raw_message for no in no_keywords):
            save_session(session, {}) # Clear session
            return {
                "static_reply": "[PLAY_AUDIO:hosp_step_cancellation.raw]",
                "auto_disconnect": True,
                "skip_name_collection": True,
                "tts_language": "en",
                "session": session,
                "state": state
            }
        else:
            # Fallback instead of cancellation: ask again and remain in confirm_interest step
            return {
                "static_reply": "I'm sorry, I didn't get that. Can we confirm your appointment?",
                "tts_language": "en",
                "session": session,
                "state": state
            }

    # 3. Handle Slot Selection Response
    elif current_step == "select_slot":
        state["selected_slot"] = raw_message
        save_session(session, state)
        return {
            "static_reply": "[PLAY_AUDIO:hosp_step3_closing.raw]",
            "auto_disconnect": True,
            "skip_name_collection": True,
            "tts_language": "en",
            "session": session,
            "state": state
        }

    return {
        "static_reply": "Sorry, I didn't get that.",
        "tts_language": "en",
        "session": session,
        "state": state
    }

def hospital_minimal_finalize(response, prep_result):
    pass
