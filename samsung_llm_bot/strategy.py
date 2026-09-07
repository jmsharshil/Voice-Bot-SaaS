# samsung_llm_bot/strategy.py

import logging
import re
from typing import Dict, Any
from .prompts import SAMSUNG_LLM_SYSTEM_PROMPT
from conversations.services.core.strategies import save_session, is_farewell

logger = logging.getLogger("SamsungLlmBotStrategy")

MAX_MESSAGE_LENGTH = 1000
MAX_TURNS = 10

def _samsung_llm_sanitise(message: str) -> str:
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
                # Clean up system/phase tags from logged history for LLM readability
                clean_text = re.sub(r'\[\s*PHASE:[^\]]*\]', '', m.text, flags=re.I)
                clean_text = re.sub(r'\[\s*PLAY_AUDIO:[^\]]*\]', '', clean_text, flags=re.I)
                for t in ["[BOOKING_CONFIRMED]", "[NOT_INTERESTED]", "[LEAD_COMPLETE]", "[END_CALL]"]:
                    clean_text = clean_text.replace(t, "")
                clean_text = clean_text.strip()
                if clean_text:
                    history_lines.append(f"{role}: {clean_text}")
            return "\n".join(history_lines)
    except Exception as e:
        logger.error(f"Error building database history for Samsung LLM: {e}")
    return ""

def _get_guj_agent_name(name):
    return "નાવ્યા"

def _get_guj_company_name(company):
    comp_lower = (company or "").lower()
    if "vtech" in comp_lower or "samsung" in comp_lower or "cafe" in comp_lower or "care" in comp_lower or "store" in comp_lower:
        parts = []
        if "vtech" in comp_lower:
            parts.append("વીટેક")
        if "samsung" in comp_lower:
            parts.append("સેમસંગ")
        if "cafe" in comp_lower:
            parts.append("કેફે")
        elif "care" in comp_lower:
            parts.append("કેર")
        elif "store" in comp_lower:
            parts.append("સ્ટોર")
        if parts:
            return " ".join(parts)
    return company or "વીટેક સેમસંગ કેફે"

def samsung_llm_strategy(agent, message, session, **kwargs):
    state: dict = session.state or {}
    raw_message = _samsung_llm_sanitise(message)
    msg = raw_message.lower()
    conversation_history: list = state.get("conversation_history", [])

    if is_farewell(msg):
        save_session(session, {})
        return "આવજો! [END_CALL]"

    agent_name = _get_guj_agent_name(agent.name)
    company_name = _get_guj_company_name(agent.company_name)

    if not state.get("intro_shown"):
        customer_name = state.get("customer_name")
        if customer_name and customer_name != "ગ્રાહક":
            reply = f"નમસ્તે, શું હું {customer_name} સાથે વાત કરી રહી છું?"
        else:
            reply = "નમસ્તે! શું હું તમારી સાથે વાત કરી શકું?"
        state["intro_shown"] = True
        state["call_phase"] = "CONFIRM_IDENTITY"
        state["conversation_history"] = [f"Agent: {reply}"]
        save_session(session, state)
        return reply

    # Step 2: Handle confirmation of identity after initial greeting
    if state.get("call_phase") in ["CONFIRM_IDENTITY", "ASK_CONSENT", "GREETING_REPLY", "interest_confirmation"] and state.get("call_phase") != "ASK_PRODUCT_INTEREST":
        negatives = ["ના", "નથી", "નાજી", "no", "not", "busy", "wrong number"]
        if any(n in msg for n in negatives):
            reply = "કોઈ વાંધો નહીં. તમારો સમય આપવા બદલ આભાર. તમારો દિવસ શુભ રહે. [END_CALL]"
            state["call_phase"] = "CLOSING"
            state["current_phase"] = "CLOSING"
            save_session(session, state)
            return reply
        else:
            pitch_reply = f"અરે વાહ! હું {agent_name}, VTech Samsung Café Ahmedabad તરફથી વાત કરી રહી છું! અત્યારે અમારે ત્યાં ચાલી રહી છે 'VTech Festive Upgrades' ની ધમાકેદાર ઑફર! એમાં તમને Smartphone, Laptop, Tablet અને Wearable પર મળી રહ્યા છે શાનદાર Cashback અને Best EMI Options! અને સાથે ખરીદી પર Loyalty Points પણ! આ Festive Seasonમાં તમે કયું Product ખરીદવાનું વિચારી રહ્યા છો — Smartphone, Laptop, Tablet કે Wearable?"
            state["call_phase"] = "ASK_PRODUCT_INTEREST"
            state["current_phase"] = "ASK_PRODUCT_INTEREST"
            conversation_history.append(f"User: {raw_message}")
            conversation_history.append(f"Agent: {pitch_reply}")
            state["conversation_history"] = conversation_history
            save_session(session, state)
            return pitch_reply

    conversation_history.append(f"User: {raw_message}")
    if len(conversation_history) > MAX_TURNS:
        conversation_history = conversation_history[-MAX_TURNS:]

    # Fallback to LLM
    history_text = get_db_history_text(session.session_id)
    cust_name = state.get("customer_name")
    cust_label = cust_name if cust_name and cust_name != "ગ્રાહક" else "તમે"
    system_prompt = SAMSUNG_LLM_SYSTEM_PROMPT.format(
        agent_name=agent_name,
        company_name=company_name,
        customer_name=cust_label,
        history_text=history_text
    )
    from conversations.services.azure_openai_service import generate_response
    reply = generate_response(system_prompt, raw_message)
    
    # Determine if call ended
    if "[END_CALL]" in reply or "[BOOKING_CONFIRMED]" in reply or "[NOT_INTERESTED]" in reply:
        state["call_phase"] = "CLOSING"
        state["current_phase"] = "CLOSING"
    else:
        state["call_phase"] = "LLM_CONVERSATION"
        state["current_phase"] = "LLM_CONVERSATION"

    conversation_history.append(f"Agent: {reply}")
    state["conversation_history"] = conversation_history
    state["last_bot_message"] = reply
    save_session(session, state)

    return reply


# ─── STREAMING PREPARE / FINALIZE ────────────────────────

def samsung_llm_prepare(agent, message, session, detected_language=None, **kwargs):
    state = session.state or {}
    raw_message = _samsung_llm_sanitise(message)
    msg = raw_message.lower()
    conversation_history = state.get("conversation_history", [])
    detected_lang = detected_language or "gu"

    if is_farewell(msg):
        save_session(session, {})
        return {
            "static_reply": "આવજો! [END_CALL]",
            "tts_language": detected_lang,
            "auto_disconnect": True
        }

    agent_name = _get_guj_agent_name(agent.name)
    company_name = _get_guj_company_name(agent.company_name)

    # Low-latency Greeting (Zero LLM Delay on Connection)
    if not state.get("intro_shown"):
        customer_name = state.get("customer_name")
        if customer_name and customer_name != "ગ્રાહક":
            reply = f"નમસ્તે, શું હું {customer_name} સાથે વાત કરી રહી છું?"
        else:
            reply = "નમસ્તે! શું હું તમારી સાથે વાત કરી શકું?"
        state["intro_shown"] = True
        state["call_phase"] = "CONFIRM_IDENTITY"
        state["current_phase"] = "CONFIRM_IDENTITY"
        state["conversation_history"] = [f"Agent: {reply}"]
        save_session(session, state)
        return {
            "static_reply": reply,
            "tts_language": detected_lang
        }

    # Step 2: Handle confirmation of identity after initial greeting ONLY ONCE
    if state.get("call_phase") in ["CONFIRM_IDENTITY", "ASK_CONSENT", "GREETING_REPLY", "interest_confirmation"] and state.get("call_phase") != "ASK_PRODUCT_INTEREST":
        negatives = ["ના", "નથી", "નાજી", "no", "not", "busy", "wrong number"]
        if any(n in msg for n in negatives):
            reply = "કોઈ વાંધો નહીં. તમારો સમય આપવા બદલ આભાર. તમારો દિવસ શુભ રહે. [END_CALL]"
            state["call_phase"] = "CLOSING"
            state["current_phase"] = "CLOSING"
            save_session(session, state)
            return {
                "static_reply": reply,
                "tts_language": detected_lang,
                "auto_disconnect": True
            }
        else:
            pitch_reply = f"અરે વાહ! હું {agent_name}, VTech Samsung Café Ahmedabad તરફથી વાત કરી રહી છું! અત્યારે અમારે ત્યાં ચાલી રહી છે 'VTech Festive Upgrades' ની ધમાકેદાર ઑફર! એમાં તમને Smartphone, Laptop, Tablet અને Wearable પર મળી રહ્યા છે શાનદાર Cashback અને Best EMI Options! અને સાથે ખરીદી પર Loyalty Points પણ! આ Festive Seasonમાં તમે કયું Product ખરીદવાનું વિચારી રહ્યા છો — Smartphone, Laptop, Tablet કે Wearable?"
            state["call_phase"] = "ASK_PRODUCT_INTEREST"
            state["current_phase"] = "ASK_PRODUCT_INTEREST"
            conversation_history.append(f"User: {raw_message}")
            conversation_history.append(f"Agent: {pitch_reply}")
            state["conversation_history"] = conversation_history
            save_session(session, state)
            return {
                "static_reply": pitch_reply,
                "tts_language": detected_lang
            }

    conversation_history.append(f"User: {raw_message}")
    if len(conversation_history) > MAX_TURNS:
        conversation_history = conversation_history[-MAX_TURNS:]

    history_text = get_db_history_text(session.session_id)
    cust_name = state.get("customer_name")
    cust_label = cust_name if cust_name and cust_name != "ગ્રાહક" else "તમે"
    system_prompt = SAMSUNG_LLM_SYSTEM_PROMPT.format(
        agent_name=agent_name,
        company_name=company_name,
        customer_name=cust_label,
        history_text=history_text
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

def samsung_llm_finalize(response, prep_result):
    state = prep_result["state"]
    session = prep_result["session"]
    conversation_history = prep_result["conversation_history"]

    closing_keywords = ["સંપર્ક કરશે", "આભાર", "હેપ્પી ફેસ્ટિવ શોપિંગ", "happy festive shopping", "દિવસ શુભ રહે", "ચોક્કસ સ્ટોર જણાવશે"]
    if "[END_CALL]" in response or "[BOOKING_CONFIRMED]" in response or "[NOT_INTERESTED]" in response or any(k in response.lower() for k in closing_keywords):
        state["call_phase"] = "CLOSING"
        state["auto_disconnect"] = True
        if "[END_CALL]" not in response:
            response = response.strip() + " [END_CALL]"
    else:
        state["call_phase"] = "LLM_CONVERSATION"

    conversation_history.append(f"Agent: {response}")
    state["conversation_history"] = conversation_history
    state["last_bot_message"] = response
    save_session(session, state)
    return response
