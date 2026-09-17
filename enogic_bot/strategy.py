import logging
import random
import re
from typing import Dict, Any
from .prompts import ENOGIC_SYSTEM_PROMPT, get_enogic_lang_instruction
from conversations.services.core.strategies import save_session, build_history_text, is_farewell

logger = logging.getLogger("EnogicBotStrategy")

MAX_MESSAGE_LENGTH = 1000
MAX_TURNS = 10

def _enogic_sanitise(message: str) -> str:
    return message.strip()[:MAX_MESSAGE_LENGTH]

# ─── NON-STREAMING (text fallback) ───────────────────────

def enogic_bot_strategy(agent, message, session, **kwargs):
    state: dict = session.state or {}
    raw_message = _enogic_sanitise(message)
    msg = raw_message.lower()
    conversation_history: list = state.get("conversation_history", [])

    if is_farewell(msg):
        save_session(session, {})
        return "Thank you for your time. Have a nice day! [END_CALL]"

    if not state.get("intro_shown"):
        reply = (
            "Hello! Main ENOGIC COMMERCIAL TRADE PRIVATE LIMITED se Shubham bol raha hoon. "
            "Hum MSME businesses ke liye teen type ki ZED Certification provide karte hain — Bronze level, Silver level aur Gold level. "
            "Kya aap certification lene mein interested hain?"
        )
        state["intro_shown"] = True
        state["call_phase"] = "interest_confirmation"
        state["conversation_history"] = [f"Agent: {reply}"]
        save_session(session, state)
        return reply

    conversation_history.append(f"User: {raw_message}")
    if len(conversation_history) > MAX_TURNS:
        conversation_history = conversation_history[-MAX_TURNS:]

    current_phase = state.get("call_phase", "interest_confirmation")
    yes_keywords = ["yes", "haan", "yeah", "ok", "confirm", "sure", "please", "interested", "chahiye", "interested hoon", "bataiye"]
    no_keywords = ["no", "na", "nahi", "cancel", "stop", "not interested", "nahi chahiye", "wrong number"]

    if current_phase == "interest_confirmation":
        if any(no in msg for no in no_keywords):
            save_session(session, {})
            return "Bilkul theek hai, koi baat nahi. Agar aapko aage kabhi bhi ZED Certification ki zaroorat ho, toh Enogic hamesha ready hai. [END_CALL]"
        else:
            state["call_phase"] = "lead_collection_name"
            reply = "Wonderful! ZED Certification se aapke business ki quality behtareen hoti hai aur wastage kam hoti hai. Sath hi MSMEs ko government subsidies aur benefits bhi milte hain. Main is inquiry ko register karne ke liye aapki details note kar leta hoon. Sabse pehle, aapka shubh naam kya hai?"
            state["conversation_history"].append(f"Agent: {reply}")
            save_session(session, state)
            return reply

    elif current_phase == "lead_collection_name":
        state["user_name"] = raw_message
        state["call_phase"] = "lead_collection_business"
        reply = "Aapke business ka naam kya hai?"
        state["conversation_history"].append(f"Agent: {reply}")
        save_session(session, state)
        return reply

    elif current_phase == "lead_collection_business":
        state["business_name"] = raw_message
        state["call_phase"] = "closing"
        reply = "Excellent! Aapki details note ho gayi hain. Hamari expert consulting team bahut jald aapse contact karegi. Thank you so much! [BOOKING_CONFIRMED] [END_CALL]"
        save_session(session, {}) # Clear/complete session
        return reply

    # Final LLM fallback if any state falls out
    history_text = build_history_text(conversation_history)
    detected_lang = state.get("detected_language", "hi")
    lang_instruction = get_enogic_lang_instruction(detected_lang)
    
    try:
        from knowledge.services.retriever import retrieve_relevant_chunks
        knowledge_context = retrieve_relevant_chunks(agent, raw_message) or ""
    except Exception as e:
        logger.error(f"Error retrieving knowledge context: {e}")
        knowledge_context = ""

    system_prompt = ENOGIC_SYSTEM_PROMPT.format(
        language_instruction=lang_instruction,
        history_text=history_text,
        knowledge_context=knowledge_context,
    )
    from conversations.services.azure_openai_service import generate_response
    response = generate_response(system_prompt, raw_message)
    conversation_history.append(f"Agent: {response}")
    state["conversation_history"] = conversation_history
    save_session(session, state)
    return response


# ─── SMART FILLERS SELECTION ─────────────────────────────

ENOGIC_FILLER_TEXTS = {
    # Category 1: Confirmation / Positive
    "enogic_bot/enogic_filler_1a.raw": "Ji bilkul, ek second...",
    "enogic_bot/enogic_filler_1b.raw": "Haan ji, main check karta hoon...",
    "enogic_bot/enogic_filler_1c.raw": "Sure, main abhi dekhta hoon...",

    # Category 2: Inquiry / Question
    "enogic_bot/enogic_filler_2a.raw": "Achha, main aapko batata hoon...",
    "enogic_bot/enogic_filler_2b.raw": "Ji, iski details ke liye ek second...",
    "enogic_bot/enogic_filler_2c.raw": "Hmm, main check karta hoon...",

    # Category 3: Neutral / Default
    "enogic_bot/enogic_filler_3a.raw": "Theek hai, main samajh gaya...",
    "enogic_bot/enogic_filler_3b.raw": "Ji, ek moment please...",
    "enogic_bot/enogic_filler_3c.raw": "Acha, dekhta hoon...",
}

def select_enogic_filler(user_msg: str, state: dict) -> str:
    """Select a contextually-appropriate filler audio based on user message keywords.
    Uses no-repeat logic to avoid playing the same filler consecutively."""
    msg = user_msg.lower()

    # 1. Inquiry keywords → Category 2 fillers
    inquiry_keywords = [
        "kya", "kaisa", "kaise", "kitna", "kitni", "kab", "kyun", "why", "how",
        "what", "which", "when", "zed", "certification", "subsidy", "benefit",
        "price", "cost", "fees", "process", "apply", "bronze", "silver", "gold",
        "details", "batao", "samjhao", "explain", "information"
    ]
    if any(re.search(r'\b' + re.escape(k) + r'\b', msg) for k in inquiry_keywords):
        files = [
            "enogic_bot/enogic_filler_2a.raw",
            "enogic_bot/enogic_filler_2b.raw",
            "enogic_bot/enogic_filler_2c.raw",
        ]
    # 2. Positive / confirmation keywords → Category 1 fillers
    elif any(re.search(r'\b' + re.escape(k) + r'\b', msg) for k in [
        "yes", "haan", "sure", "ok", "okay", "thik", "theek", "bilkul",
        "sahi", "agree", "confirm", "chahiye", "interested"
    ]):
        files = [
            "enogic_bot/enogic_filler_1a.raw",
            "enogic_bot/enogic_filler_1b.raw",
            "enogic_bot/enogic_filler_1c.raw",
        ]
    # 3. Default / fallback → Category 3 fillers
    else:
        files = [
            "enogic_bot/enogic_filler_3a.raw",
            "enogic_bot/enogic_filler_3b.raw",
            "enogic_bot/enogic_filler_3c.raw",
        ]

    # No-repetition logic: filter out already played fillers in this session
    played = state.get("played_fillers", [])
    available = [f for f in files if f not in played]
    if not available:
        # All in this category played — reset category and pick again
        available = files
        state["played_fillers"] = [p for p in played if p not in files]
        played = state["played_fillers"]

    chosen = random.choice(available)
    played.append(chosen)
    state["played_fillers"] = played
    return chosen


# ─── STREAMING PREPARE / FINALIZE ────────────────────────

def enogic_bot_prepare(agent, message, session, detected_language=None, **kwargs):
    state = session.state or {}
    raw_message = _enogic_sanitise(message)
    msg = raw_message.lower()
    conversation_history = state.get("conversation_history", [])

    if detected_language:
        state["detected_language"] = detected_language

    # FAREWELL
    if is_farewell(msg):
        save_session(session, {})
        return {
            "static_reply": "Apna samay dene ke liye shukriya. Have a nice day! [END_CALL]",
            "tts_language": detected_language or "hi"
        }

    # INTRO (Greeting)
    if not state.get("intro_shown"):
        reply = "Hello! Main ENOGIC COMMERCIAL TRADE PRIVATE LIMITED se Shubham bol raha hoon. Hum MSME businesses ke liye teen type ki ZED Certification provide karte hain — Bronze level, Silver level aur Gold level. Kya aap certification lene mein interested hain?"
        state["intro_shown"] = True
        state["call_phase"] = "interest_confirmation"
        state["conversation_history"] = [f"Agent: {reply}"]
        save_session(session, state)
        return {
            "static_reply": "[PLAY_AUDIO:enogic_bot/enogic_step1_greeting.raw]",
            "tts_language": detected_language or "hi"
        }

    # UPDATE COUNTER
    exchange_count = state.get("exchange_count", 0)
    exchange_count += 1
    state["exchange_count"] = exchange_count

    conversation_history.append(f"User: {raw_message}")
    if len(conversation_history) > MAX_TURNS:
        conversation_history = conversation_history[-MAX_TURNS:]

    current_phase = state.get("call_phase", "interest_confirmation")
    yes_keywords = ["yes", "haan", "yeah", "ok", "confirm", "sure", "please", "interested", "chahiye", "interested hoon", "bataiye", "batao"]
    no_keywords = ["no", "na", "nahi", "cancel", "stop", "not interested", "nahi chahiye", "wrong number", "busy"]

    if current_phase == "interest_confirmation":
        if any(no in msg for no in no_keywords):
            save_session(session, {})
            return {
                "static_reply": "[PLAY_AUDIO:enogic_bot/enogic_step9_graceful_exit.raw] [END_CALL]",
                "tts_language": state.get("detected_language", "hi"),
                "auto_disconnect": True,
                "skip_name_collection": True
            }
        elif any(yes in msg for yes in yes_keywords):
            state["call_phase"] = "lead_collection_name"
            save_session(session, state)
            return {
                "static_reply": "[PLAY_AUDIO:enogic_bot/enogic_step3_cert_intro.raw]",
                "tts_language": state.get("detected_language", "hi")
            }
        else:
            # Fallback to LLM if ambiguous
            pass

    elif current_phase == "lead_collection_name":
        state["user_name"] = raw_message
        state["call_phase"] = "lead_collection_business"
        save_session(session, state)
        return {
            "static_reply": "[PLAY_AUDIO:enogic_bot/enogic_step6_ask_business.raw]",
            "tts_language": state.get("detected_language", "hi")
        }

    elif current_phase == "lead_collection_business":
        state["business_name"] = raw_message
        state["call_phase"] = "closing"
        save_session(session, state)
        return {
            "static_reply": "[PLAY_AUDIO:enogic_bot/enogic_step8_closing.raw] [BOOKING_CONFIRMED] [END_CALL]",
            "tts_language": state.get("detected_language", "hi"),
            "auto_disconnect": True,
            "skip_name_collection": True
        }

    # Final LLM Fallback (if state falls out or ambiguous inputs occur)
    history_text = build_history_text(conversation_history)
    detected_lang = state.get("detected_language", "hi")
    lang_instruction = get_enogic_lang_instruction(detected_lang)

    try:
        from knowledge.services.retriever import retrieve_relevant_chunks
        knowledge_context = retrieve_relevant_chunks(agent, raw_message) or ""
    except Exception as e:
        logger.error(f"Error retrieving knowledge context: {e}")
        knowledge_context = ""

    system_prompt = ENOGIC_SYSTEM_PROMPT.format(
        language_instruction=lang_instruction,
        history_text=history_text,
        knowledge_context=knowledge_context,
    )

    # ⚡ Select a filler audio to play while LLM generates the response
    filler_file = select_enogic_filler(raw_message, state)
    filler_text = ENOGIC_FILLER_TEXTS.get(filler_file, "")

    # Instruct LLM to continue naturally after the filler phrase
    if filler_text:
        system_prompt += (
            f"\n\n⚠️ IMPORTANT INSTRUCTION FOR CONTINUATION:\n"
            f"The user has already heard you speak this filler phrase: '{filler_text}'.\n"
            f"You MUST write your response so it continues directly and naturally after this phrase, "
            f"acting as a single coherent statement. Do not repeat the filler, do not use any greetings "
            f"or introductory phrases (like 'Haan', 'Ji', 'Sure', 'Acha'), and do not start a brand new "
            f"sentence if you can connect it with a conjunction (like 'aur', 'toh', 'isliye'). "
            f"Start directly with the next word after the filler."
        )

    save_session(session, state)
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

def enogic_bot_finalize(response, prep_result):
    state = prep_result["state"]
    session = prep_result["session"]
    conversation_history = prep_result["conversation_history"]

    conversation_history.append(f"Agent: {response}")
    state["conversation_history"] = conversation_history
    state["last_bot_message"] = response
    save_session(session, state)
