# kia_syros_bot/strategy.py

import logging
import re
from .prompts import KIA_SYROS_SYSTEM_PROMPT
from conversations.services.core.strategies import save_session

logger = logging.getLogger("KiaSyrosBotStrategy")

MAX_MESSAGE_LENGTH = 1000
MAX_TURNS = 10

# ─── INTENT MATCHER (lazy-loaded) ────────────────────────

KIA_SYROS_MATCHER = None

def get_kia_syros_matcher():
    global KIA_SYROS_MATCHER
    if KIA_SYROS_MATCHER is None:
        try:
            from automobile_matcher import AutomobileMatcher
            logger.info("Lazy-loading Kia Syros intents matcher...")
            KIA_SYROS_MATCHER = AutomobileMatcher("kia_syros_bot/data/kia_syros_intents.json")
            logger.info("Kia Syros intents matcher loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize KIA_SYROS_MATCHER: {e}")
            KIA_SYROS_MATCHER = None
    return KIA_SYROS_MATCHER


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

    # Try intent matching first
    current_phase = state.get("call_phase", "GREETING_REPLY")
    try:
        matcher = get_kia_syros_matcher()
        if matcher:
            match_result = matcher.find_match(raw_message, current_phase=current_phase, threshold=0.70)
            if match_result and match_result.get("match_type") != "NONE":
                next_phase = match_result.get("next_phase")
                if next_phase:
                    state["call_phase"] = next_phase

                mp3_filename = match_result["mp3"]
                raw_filename = mp3_filename.replace(".mp3", ".raw")
                from conversations.consumers import _AUDIO_TRANSCRIPTIONS
                reply = _AUDIO_TRANSCRIPTIONS.get(raw_filename, f"[PLAY_AUDIO:{raw_filename}]")
                if next_phase == "CLOSING":
                    reply += " [END_CALL]"

                state["conversation_history"] = conversation_history
                state["last_bot_message"] = reply
                save_session(session, state)
                return reply
    except Exception as match_err:
        logger.error(f"Error in Kia Syros strategy fast-path match: {match_err}")

    # Fallback to LLM
    history_text = get_db_history_text(session.session_id)
    system_prompt = KIA_SYROS_SYSTEM_PROMPT.format(customer_name=customer_name, history_text=history_text)

    from conversations.services.azure_openai_service import generate_response
    response = generate_response(system_prompt, raw_message)

    conversation_history.append(f"Agent: {response}")
    state["conversation_history"] = conversation_history
    state["last_bot_message"] = response
    save_session(session, state)

    return response


# ─── STREAMING PREPARE / FINALIZE ────────────────────────

def kia_syros_prepare(agent, message, session, detected_language=None, **kwargs):
    state = session.state or {}
    if "conversation_history" not in state:
        state["conversation_history"] = []
    raw_message = _kia_syros_sanitise(message)
    conversation_history = state["conversation_history"]
    detected_lang = detected_language or "hi"

    # STEP 0: INITIAL GREETING (Turn 1)
    raw_cust_name = state.get("customer_name")
    cust_display_name = raw_cust_name if (raw_cust_name and raw_cust_name != "Sir/Ma'am") else "आप"
    if not state.get("intro_shown"):
        reply = f"Hello, क्या मेरी बात {cust_display_name} से हो रही है?"
        state["intro_shown"] = True
        state["call_phase"] = "GREETING_REPLY"
        state["conversation_history"] = [f"Agent: {reply}"]
        save_session(session, state)
        return {
            "static_reply": reply,
            "tts_language": detected_lang
        }

    # UPDATE COUNTER
    exchange_count = state.get("exchange_count", 0)
    exchange_count += 1
    state["exchange_count"] = exchange_count

    # HISTORY BUILD
    conversation_history.append(f"User: {raw_message}")
    if len(conversation_history) > MAX_TURNS:
        conversation_history = conversation_history[-MAX_TURNS:]

    history_text = get_db_history_text(session.session_id)
    system_prompt = KIA_SYROS_SYSTEM_PROMPT.format(customer_name=cust_display_name, history_text=history_text)

    current_phase = state.get("call_phase", "GREETING_REPLY")

    # ─── MP3-FIRST: Try intent matching ──────────────────
    try:
        matcher = get_kia_syros_matcher()
        if matcher:
            match_result = matcher.find_match(raw_message, current_phase=current_phase, threshold=0.70)
            if match_result and match_result.get("match_type") != "NONE":
                next_phase = match_result.get("next_phase")
                if next_phase:
                    state["call_phase"] = next_phase
                    save_session(session, state)

                mp3_filename = match_result["mp3"]
                raw_filename = mp3_filename.replace(".mp3", ".raw")

                is_closing = (next_phase == "CLOSING")
                reply = f"[PLAY_AUDIO:{raw_filename}]"
                if is_closing:
                    reply += " [END_CALL]"

                intent_name = match_result.get("intent", {}).get("intent_name", "")
                logger.info(f"[KIA MP3-FIRST] Phase={current_phase} → Intent={intent_name} → File={raw_filename} → NextPhase={next_phase}")

                res = {
                    "static_reply": reply,
                    "tts_language": detected_lang,
                }
                if is_closing:
                    is_booking = "booking_confirmed" in raw_filename
                    res["auto_disconnect"] = True
                    res["skip_name_collection"] = True
                    if is_booking:
                        reply = reply.replace("[END_CALL]", "[BOOKING_CONFIRMED] [END_CALL]")
                        res["static_reply"] = reply
                return res
    except Exception as match_err:
        logger.error(f"Error in Kia Syros prepare intent match: {match_err}")

    # ─── ALT_NUMBER_REPLY special case: always LLM fallback ──
    # When user gives an alternate number, LLM can naturally confirm it back
    if current_phase == "ALT_NUMBER_REPLY":
        state["call_phase"] = "CLOSING"
        save_session(session, state)

    # ─── FALLBACK: LLM generates response ────────────────
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

def kia_syros_finalize(response, prep_result):
    state = prep_result["state"]
    session = prep_result["session"]
    conversation_history = prep_result["conversation_history"]

    conversation_history.append(f"Agent: {response}")
    state["conversation_history"] = conversation_history
    state["last_bot_message"] = response
    save_session(session, state)
