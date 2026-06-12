import logging
import re
from typing import Dict, Any
from .prompts import Naavya_SYSTEM_PROMPT, get_Naavya_lang_instruction
from .config import AutomobileBotConfig

logger = logging.getLogger("NaavyaStrategy")

# Constants
MAX_MESSAGE_LENGTH = 1000
MAX_TURNS = 10

def _Naavya_sanitise(message: str) -> str:
    return message.strip()[:MAX_MESSAGE_LENGTH]

def build_history_text(history: list) -> str:
    return "\n".join(history)

def is_farewell(msg: str) -> bool:
    msg = msg.lower()
    return any(w in msg for w in ["bye", "goodbye", "alvida", "chalo bye", "see you", "milte hain"])

def save_session(session, state: dict):
    session.state = state
    session.save()

# ─── NON-STREAMING (text fallback) ───────────────────────

def automobile_Naavya_strategy(agent, message, session, **kwargs):
    state: dict = session.state or {}
    raw_message = _Naavya_sanitise(message)
    msg = raw_message.lower()
    conversation_history: list = state.get("conversation_history", [])

    if is_farewell(msg):
        save_session(session, {})
        return "Aapse baat karke achha laga! Hum jaldi hi showroom mein milenge. Take care! Bye!"

    if not state.get("intro_shown"):
        reply = (
            f"Hi there! This is Naavya — so lovely to connect with you! "
            f"Are you exploring a new car today, or is there a specific model you have your eye on? "
            f"I'm here to help make this fun!"
        )
        state["intro_shown"] = True
        state["conversation_history"] = [f"Agent: {reply}"]
        save_session(session, state)
        return reply

    conversation_history.append(f"User: {raw_message}")
    if len(conversation_history) > MAX_TURNS:
        conversation_history = conversation_history[-MAX_TURNS:]

    history_text = build_history_text(conversation_history)

    try:
        from knowledge.services.retriever import retrieve_relevant_chunks
        knowledge_context = retrieve_relevant_chunks(agent, raw_message) or ""
    except Exception:
        knowledge_context = ""

    detected_lang = state.get("detected_language", "hi")
    lang_instruction = get_Naavya_lang_instruction(detected_lang)

    system_prompt = Naavya_SYSTEM_PROMPT.format(
        language_instruction=lang_instruction,
        knowledge_context=knowledge_context,
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

def automobile_Naavya_prepare(agent, message, session, detected_language=None, **kwargs):
    state = session.state or {}
    raw_message = _Naavya_sanitise(message)
    msg = raw_message.lower()
    conversation_history = state.get("conversation_history", [])

    if detected_language:
        state["detected_language"] = detected_language

    # FAREWELL
    if is_farewell(msg):
        save_session(session, {})
        lang = kwargs.get("detected_language") or state.get("detected_language", "hi")
        farewells = {
            "hi": "Aapse baat karke achha laga! Showroom mein aane ka yaad rakhna. Take care. Bye!",
            "en": "It was great talking to you! Looking forward to welcoming you to our showroom. Have a nice day! Bye!",
            "gu": "તમારી સાથે વાત કરીને ખૂબ આનંદ થયો! શોરૂમની મુલાકાત લેવાનું ભૂલતા નહીં. આવજો!"
        }
        return {
            "static_reply": farewells.get(lang, farewells["hi"]),
            "tts_language": lang
        }

    # INTRO
    if not state.get("intro_shown"):
        reply = (
            f"Hi there! This is Naavya — so lovely to connect with you! "
            f"Are you exploring a new car today, or is there a specific model you have your eye on? "
            f"I'm here to help make this fun!"
        )
        state["intro_shown"] = True
        state["conversation_history"] = [f"Agent: {reply}"]
        save_session(session, state)
        return {"static_reply": reply}

    # UPDATE COUNTER
    exchange_count = state.get("exchange_count", 0)
    exchange_count += 1
    state["exchange_count"] = exchange_count

    # HISTORY BUILD
    conversation_history.append(f"User: {raw_message}")
    if len(conversation_history) > MAX_TURNS:
        conversation_history = conversation_history[-MAX_TURNS:]

    history_text = build_history_text(conversation_history)

    try:
        from knowledge.services.retriever import retrieve_relevant_chunks
        knowledge_context = retrieve_relevant_chunks(agent, raw_message) or ""
    except Exception:
        knowledge_context = ""

    detected_lang = state.get("detected_language", "hi")
    lang_instruction = get_Naavya_lang_instruction(detected_lang)

    system_prompt = Naavya_SYSTEM_PROMPT.format(
        language_instruction=lang_instruction,
        knowledge_context=knowledge_context,
        history_text=history_text,
    )

    # CHECK FOR NOT INTERESTED / BUSY OVERRIDES IN THE CONVERSATION FLOW
    not_interested_keywords = [
        "nahi chahiye", "not interested", "no thanks", "nahi", "wrong number", "already bought", "khareed li", "le li",
        "नहीं", "नहीं चाहिए", "ना", "बात नहीं करनी", "गलत नंबर", "નથી લેવી", "નથી જોઈતી", "ના", "નથી"
    ]
    busy_keywords = [
        "busy", "baad mein", "later", "meeting", "driving", "office", "kaam", "postpone",
        "बाद में", "व्यस्त", "काम में हूँ", "પછી વાત કરીએ", "કામમાં છું", "વ્યસ્ત"
    ]

    current_phase = state.get("current_phase", "GREETING_REPLY")

    if any(kw in msg for kw in not_interested_keywords) and current_phase == "GREETING_REPLY":
        system_prompt += (
            f"\n\n"
            f"🚨 OVERRIDE — USER IS NOT INTERESTED 🚨\n"
            f"The user has indicated they are NOT interested or want to end the call.\n"
            f"YOUR TASK:\n"
            f"  1. Politely/warmly apologize for the disturbance and say goodbye in ONE short sentence.\n"
            f"  2. You MUST append the exact tag '[NOT_INTERESTED]' at the very end of your response!\n"
            f"  3. Do NOT ask any follow-up question.\n"
        )
    elif any(kw in msg for kw in busy_keywords) and current_phase == "GREETING_REPLY":
        system_prompt += (
            f"\n\n"
            f"🚨 OVERRIDE — USER IS BUSY 🚨\n"
            f"The user has indicated they are busy.\n"
            f"YOUR TASK:\n"
            f"  1. Politely acknowledge and say you will call back later in ONE short sentence.\n"
            f"  2. You MUST append the exact tag '[END_CALL]' at the very end of your response!\n"
        )

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

def automobile_Naavya_finalize(response, prep_result):
    state = prep_result["state"]
    session = prep_result["session"]
    conversation_history = prep_result["conversation_history"]

    conversation_history.append(f"Agent: {response}")
    state["conversation_history"] = conversation_history
    state["last_bot_message"] = response
    save_session(session, state)
