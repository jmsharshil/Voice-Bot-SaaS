# raahi_iiiem_bot/strategy.py

import logging
import re
from typing import Dict, Any
from .config import (
    AGENT_NAME,
    COMPANY_NAME,
    MAX_MESSAGE_LENGTH,
    MAX_TURNS,
    STAGE_GREET,
    STAGE_NEED,
    STAGE_RECOMMEND,
    STAGE_INFO_PREF,
    STAGE_WHATSAPP_CONFIRM,
    STAGE_SUPPORT_PREF,
    STAGE_PATH_ONLINE,
    STAGE_PATH_CENTRE,
    STAGE_REGISTRATION_PUSH,
    STAGE_CLOSING,
)
from .prompts import RAAHI_IIIEM_SYSTEM_PROMPT
from conversations.services.core.strategies import save_session, is_farewell

logger = logging.getLogger("RaahiIiiemBotStrategy")

def _raahi_sanitise(message: str) -> str:
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
                clean_text = re.sub(r'\[\s*STAGE:[^\]]*\]', '', m.text, flags=re.I)
                clean_text = re.sub(r'\[\s*WHATSAPP_SENT[^\]]*\]', '', clean_text, flags=re.I)
                for t in ["[END_CALL]", "[BOOKING_CONFIRMED]", "[HUMAN_HANDOFF]"]:
                    clean_text = clean_text.replace(t, "")
                clean_text = clean_text.strip()
                if clean_text:
                    history_lines.append(f"{role}: {clean_text}")
            return "\n".join(history_lines)
    except Exception as e:
        logger.error(f"Error building database history for Raahi iiiEM: {e}")
    return ""


def raahi_iiiem_strategy(agent, message, session, **kwargs):
    """Non-streaming / HTTP fallback implementation."""
    state: dict = session.state or {}
    raw_message = _raahi_sanitise(message)
    msg = raw_message.lower()
    conversation_history: list = state.get("conversation_history", [])

    if is_farewell(msg):
        save_session(session, {})
        return "Dhanyavaad, aapka din shubh ho! [END_CALL]"

    current_stage = state.get("stage", STAGE_GREET)
    customer_name = state.get("customer_name", "Ji")

    # Initial Opening Turn (Zero-Latency Instant Greeting)
    if not state.get("intro_shown"):
        customer_name_input = state.get("customer_name")
        if customer_name_input and customer_name_input.lower() != "user":
            reply = f"{customer_name_input}, export start karna hai ya already export kar rahe hain?"
            state["stage"] = STAGE_NEED
        else:
            reply = f"Namaste! Main Raahi, Triple i E M se. Aapka naam?"
            state["stage"] = STAGE_GREET

        state["intro_shown"] = True
        state["conversation_history"] = [f"Agent: {reply}"]
        save_session(session, state)
        return reply

    conversation_history.append(f"User: {raw_message}")
    if len(conversation_history) > MAX_TURNS:
        conversation_history = conversation_history[-MAX_TURNS:]

    history_text = get_db_history_text(session.session_id)

    system_prompt = RAAHI_IIIEM_SYSTEM_PROMPT.format(
        agent_name=agent.name or AGENT_NAME,
        company_name=agent.company_name or COMPANY_NAME,
        history_text=history_text,
        current_stage=current_stage,
        customer_name=customer_name,
        user_message=raw_message
    )

    from conversations.services.azure_openai_service import generate_response
    reply = generate_response(system_prompt, raw_message)

    res_lower = reply.lower()
    if "aapka naam" in res_lower or "may i know your name" in res_lower:
        state["stage"] = STAGE_GREET
    elif "export start karna hai" in res_lower or "looking to start exporting" in res_lower:
        state["stage"] = STAGE_NEED
    elif "product decide hai" in res_lower or "decided on your product" in res_lower:
        state["stage"] = STAGE_RECOMMEND
    elif "pehle process samjhun ya fees" in res_lower or "explain the process first" in res_lower:
        state["stage"] = STAGE_INFO_PREF
    elif "whatsapp par share kar deti hoon" in res_lower or "share complete details on whatsapp" in res_lower:
        state["stage"] = STAGE_WHATSAPP_CONFIRM
    elif "details isi number par share kar doon" in res_lower or "share the details on whatsapp to this number" in res_lower:
        state["stage"] = STAGE_SUPPORT_PREF
    elif "online guidance prefer karenge" in res_lower or "online guidance or centre support" in res_lower:
        state["stage"] = STAGE_PATH_ONLINE
    elif "nearest centre ka guidance doon" in res_lower or "rajkot centre convenient" in res_lower:
        state["stage"] = STAGE_PATH_CENTRE
    elif "step-by-step guide kar doon" in res_lower or "step-by-step through the registration" in res_lower:
        state["stage"] = STAGE_CLOSING
    elif "[END_CALL]" in reply or "dhanyavaad" in res_lower or "thank you" in res_lower:
        state["stage"] = STAGE_CLOSING

    conversation_history.append(f"Agent: {reply}")
    state["conversation_history"] = conversation_history
    state["last_bot_message"] = reply
    save_session(session, state)

    return reply


# ─── STREAMING PREPARE / FINALIZE ────────────────────────

def raahi_iiiem_prepare(agent, message, session, detected_language=None, **kwargs):
    """Streaming prepare method called before starting OpenAI LLM streaming."""
    state = session.state or {}
    raw_message = _raahi_sanitise(message)
    msg = raw_message.lower()
    conversation_history = state.get("conversation_history", [])

    if is_farewell(msg):
        save_session(session, {})
        return {
            "static_reply": "Dhanyavaad, aapka din shubh ho! [END_CALL]",
            "tts_language": "hi",
            "auto_disconnect": True
        }

    # Zero Latency Connection Greeting
    if not state.get("intro_shown"):
        customer_name_input = state.get("customer_name")
        if customer_name_input and customer_name_input.lower() != "user":
            reply = f"{customer_name_input}, export start karna hai ya already export kar rahe hain?"
            state["stage"] = STAGE_NEED
        else:
            reply = f"Namaste! Main Raahi, Triple i E M se. Aapka naam?"
            state["stage"] = STAGE_GREET

        state["intro_shown"] = True
        state["conversation_history"] = [f"Agent: {reply}"]
        save_session(session, state)
        return {
            "static_reply": reply,
            "tts_language": "hi"
        }

    conversation_history.append(f"User: {raw_message}")
    if len(conversation_history) > MAX_TURNS:
        conversation_history = conversation_history[-MAX_TURNS:]

    current_stage = state.get("stage", STAGE_GREET)
    customer_name = state.get("customer_name", "Ji")
    history_text = get_db_history_text(session.session_id)

    system_prompt = RAAHI_IIIEM_SYSTEM_PROMPT.format(
        agent_name=agent.name or AGENT_NAME,
        company_name=agent.company_name or COMPANY_NAME,
        history_text=history_text,
        current_stage=current_stage,
        customer_name=customer_name,
        user_message=raw_message
    )

    return {
        "system_prompt": system_prompt,
        "user_message": raw_message,
        "tts_language": "hi",
        "skip_input_translation": True,
        "skip_output_translation": True,
        "translate_input_to": "original",
        "state": state,
        "session": session,
        "conversation_history": conversation_history,
        "strategy_key": "raahi_iiiem_strategy"
    }


def raahi_iiiem_finalize(response, prep_result):
    """Post-processing callback after OpenAI response stream finishes."""
    state = prep_result.get("state") or {}
    session = prep_result.get("session")
    conversation_history = prep_result.get("conversation_history") or []

    res_lower = response.lower()
    if "aapka naam" in res_lower or "may i know your name" in res_lower:
        state["stage"] = STAGE_NEED
    elif "export start karna hai" in res_lower or "looking to start exporting" in res_lower:
        state["stage"] = STAGE_NEED
    elif "product decide hai" in res_lower or "decided on your product" in res_lower:
        state["stage"] = STAGE_RECOMMEND
    elif "pehle process samjhun ya fees" in res_lower or "explain the process first" in res_lower:
        state["stage"] = STAGE_INFO_PREF
    elif "whatsapp par share kar deti hoon" in res_lower or "share complete details on whatsapp" in res_lower:
        state["stage"] = STAGE_WHATSAPP_CONFIRM
    elif "details isi number par share kar doon" in res_lower or "share the details on whatsapp to this number" in res_lower:
        state["stage"] = STAGE_SUPPORT_PREF
    elif "online guidance prefer karenge" in res_lower or "online guidance or centre support" in res_lower:
        state["stage"] = STAGE_PATH_ONLINE
    elif "nearest centre ka guidance doon" in res_lower or "rajkot centre convenient" in res_lower:
        state["stage"] = STAGE_PATH_CENTRE
    elif "step-by-step guide kar doon" in res_lower or "step-by-step through the registration" in res_lower:
        state["stage"] = STAGE_CLOSING
    elif "[END_CALL]" in response or "dhanyavaad" in res_lower or "thank you" in res_lower:
        state["stage"] = STAGE_CLOSING

    conversation_history.append(f"Agent: {response}")
    state["conversation_history"] = conversation_history
    state["last_bot_message"] = response
    if session:
        save_session(session, state)
    return response


def get_raahi_reprompt(session_state: dict, language: str = "hi") -> str:
    """Generate a language-aware re-prompt after 15s silence."""
    last_msg = session_state.get("last_bot_message", "")
    clean_q = re.sub(r'\[\s*[^\]]*\]', '', last_msg).strip()

    is_english = (language == "en" or any(clean_q.lower().startswith(w) for w in ["hello", "thank", "great", "alright", "perfect", "in short", "should i", "would you", "shall i", "have you"]))

    if is_english:
        prefix = "Are you there? I am waiting for your response."
        if clean_q:
            return f"{prefix} {clean_q}"
        return f"{prefix} Could you please let me know your response?"
    else:
        prefix = "Kya aap sun rahe hain? Main aapke jawab ka wait kar rahi hoon."
        if clean_q:
            return f"{prefix} {clean_q}"
        return f"{prefix} Aap bata sakte hain?"

