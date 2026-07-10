# fold8_bot/strategy.py

import logging
import re
from typing import Dict, Any
from .prompts import FOLD8_SYSTEM_PROMPT
from conversations.services.core.strategies import save_session, is_farewell

logger = logging.getLogger("Fold8BotStrategy")

MAX_MESSAGE_LENGTH = 1000
MAX_TURNS = 10

def _fold8_sanitise(message: str) -> str:
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
        logger.error(f"Error building database history for Fold8: {e}")
    return ""

def _get_guj_agent_name(name):
    name_lower = (name or "").lower()
    if "neel" in name_lower:
        return "નીલ"
    if "naavya" in name_lower:
        return "નાવ્યા"
    return name or "નાવ્યા"

def _get_guj_company_name(company):
    comp_lower = (company or "").lower()
    if "vtech" in comp_lower or "nxtgen" in comp_lower or "samsung" in comp_lower or "retail" in comp_lower or "store" in comp_lower:
        parts = []
        if "vtech" in comp_lower:
            parts.append("વીટેક")
        if "nxtgen" in comp_lower:
            parts.append("નેક્સ્ટજેન")
        if "retail" in comp_lower:
            parts.append("રીટેલ્સ")
        if "samsung" in comp_lower:
            parts.append("સેમસંગ")
        if "store" in comp_lower or "experience" in comp_lower:
            parts.append("એક્સપિરિયન્સ સ્ટોર")
        if parts:
            return " ".join(parts)
    return company or "વીટેક નેક્સ્ટજેન રીટેલ્સ સેમસંગ એક્સપિરિયન્સ સ્ટોર"

def fold8_prereserve_strategy(agent, message, session, **kwargs):
    state: dict = session.state or {}
    raw_message = _fold8_sanitise(message)
    msg = raw_message.lower()
    conversation_history: list = state.get("conversation_history", [])

    if is_farewell(msg):
        save_session(session, {})
        return "આવજો! [END_CALL]"

    agent_name = _get_guj_agent_name(agent.name)
    company_name = _get_guj_company_name(agent.company_name)

    if not state.get("intro_shown"):
        reply = f"નમસ્તે! હું {agent_name} છું, {company_name}થી બોલું છું. મને થોડો સમય મળશે, સર અથવા મેડમ?"
        state["intro_shown"] = True
        state["call_phase"] = "ASK_CONSENT"
        state["conversation_history"] = [f"Agent: {reply}"]
        save_session(session, state)
        return reply

    conversation_history.append(f"User: {raw_message}")
    if len(conversation_history) > MAX_TURNS:
        conversation_history = conversation_history[-MAX_TURNS:]

    history_text = get_db_history_text(session.session_id)
    system_prompt = FOLD8_SYSTEM_PROMPT.format(
        agent_name=agent.name or "Naavya",
        company_name=agent.company_name or "VTech NxtGen Retails LLP",
        history_text=history_text
    )
    from conversations.services.azure_openai_service import generate_response
    reply = generate_response(system_prompt, raw_message)
    
    if "[END_CALL]" in reply or "[BOOKING_CONFIRMED]" in reply or "[NOT_INTERESTED]" in reply:
        state["call_phase"] = "CLOSING"
    else:
        state["call_phase"] = "LLM_CONVERSATION"

    conversation_history.append(f"Agent: {reply}")
    state["conversation_history"] = conversation_history
    state["last_bot_message"] = reply
    save_session(session, state)

    return reply

def lookup_store_by_area(text):
    text_lower = text.lower().strip()
    
    # Vijay Cross Road
    vijay_keywords = [
        "navrangpura", "cg road", "c.g. road", "ellisbridge", "law garden", "ashram road", "vijay cross", 
        "naranpura", "usmanpura", "memnagar", "panjrapol", "gurukul", 
        "નવરંગપુરા", "સીજી રોડ", "એલિસબ્રિજ", "લો ગાર્ડન", "આશ્રમ રોડ", "વિજય ક્રોસ", "નારણપુરા", "ઉસ્માનપુરા", "મેમનગર", "પાંજરાપોળ", "ગુરુકુલ"
    ]
    # Bodakdev
    bodakdev_keywords = [
        "bodakdev", "iscon", "satellite", "prahladnagar", "sg highway", "s.g. highway", "jodhpur", "vejalpur", "south bopal", "vastrapur", "makarba", "sarkhej", 
        "બોડકદેવ", "ઈસકોન", "ઇસ્કોન", "સેટેલાઈટ", "સેટેલાઇટ", "પ્રહલાદનગર", "એસજી હાઈવે", "જોધપુર", "વેજલપુર", "વસ્ત્રાપુર", "મકરબા", "સરખેજ"
    ]
    # Palladium Mall
    palladium_keywords = [
        "thaltej", "bopal", "ambli", "palladium", "sola", "science city", "gota", "jagatpur", "ghatlodia", "chandlodia", "ranip", 
        "થલતેજ", "બોપલ", "આંબલી", "પેલેડિયમ", "સોલા", "સાયન્સ સીટી", "સાયન્સ સિટી", "ગોતા", "જગતપુર", "ઘાટલોડિયા", "ઘાટલોડીયા", "ચાંદલોડિયા", "ચાંદલોડીયા", "રાણીપ"
    ]
    # Paldi
    paldi_keywords = [
        "paldi", "vasna", "jivraj park", "ambawadi", "ambedkar", "nehru nagar", "kalupur", "lal darwaja", "astodia", 
        "પાલડી", "વાસણા", "જીવરાજ પાર્ક", "આંબાવાડી", "આંબેડકર", "નેહરુ નગર", "નેહરૂ નગર", "કાલુપુર", "લાલ દરવાજા", "આસ્ટોડિયા", "આસ્ટોડીયા"
    ]
    # Isanpur
    isanpur_keywords = [
        "isanpur", "maninagar", "vatva", "narol", "ghodasar", "ctm", "ramol", "amraiwadi", "khokhra", 
        "ઈસનપુર", "ઇસનપુર", "મણિનગર", "વાટવા", "વટવા", "નારોલ", "ઘોડાસર", "સીટીએમ", "રામોલ", "અમરાઈવાડી", "ખોખરા"
    ]
    # New Naroda
    naroda_keywords = [
        "naroda", "nava naroda", "kathwada", "nikol", "vastral", "bapunagar", "odhav", "thakkarbapanagar", "krishnanagar", "singarwa", 
        "નરોડા", "નવા નરોડા", "કઠવાડા", "નિકોલ", "વસ્ત્રાલ", "બાપુનગર", "ઓઢવ", "ઠક્કરબાપાનગર", "કૃષ્ણનગર", "સિંગરવા"
    ]
    
    for k in vijay_keywords:
        if k in text_lower:
            return "વિજય ક્રોસ રોડ"
    for k in bodakdev_keywords:
        if k in text_lower:
            return "બોડકદેવ"
    for k in palladium_keywords:
        if k in text_lower:
            return "પેલેડિયમ મોલ"
    for k in paldi_keywords:
        if k in text_lower:
            return "પાલડી"
    for k in isanpur_keywords:
        if k in text_lower:
            return "ઈસનપુર"
    for k in naroda_keywords:
        if k in text_lower:
            return "ન્યૂ નરોડા"
    return None

def fold8_prereserve_prepare(agent, message, session, detected_language=None, **kwargs):
    state = session.state or {}
    raw_message = _fold8_sanitise(message)
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
        reply = f"નમસ્તે! હું {agent_name} છું, {company_name}થી બોલું છું. મને થોડો સમય મળશે, સર અથવા મેડમ?"
        state["intro_shown"] = True
        state["call_phase"] = "ASK_CONSENT"
        state["conversation_history"] = [f"Agent: {reply}"]
        save_session(session, state)
        return {
            "static_reply": reply,
            "tts_language": detected_lang,
            "state": state,
            "session": session,
            "skip_input_translation": True,
            "skip_output_translation": True,
            "translate_input_to": "original"
        }

    current_phase = state.get("call_phase", "ASK_CONSENT")

    # Zero Latency State Machine
    if current_phase == "ASK_AREA":
        store_name = lookup_store_by_area(raw_message)
        if store_name:
            state["nearest_store"] = store_name
            state["call_phase"] = "STORE_CONFIRMED"
            save_session(session, state)
            
            store_file_map = {
                "વિજય ક્રોસ રોડ": "fold8_store_vijay.raw",
                "બોડકદેવ": "fold8_store_bodakdev.raw",
                "પેલેડિયમ મોલ": "fold8_store_palladium.raw",
                "પાલડી": "fold8_store_paldi.raw",
                "ઈસનપુર": "fold8_store_isanpur.raw",
                "ન્યૂ નરોડા": "fold8_store_naroda.raw"
            }
            raw_file = store_file_map.get(store_name, "fold8_store_naroda.raw")
            return {
                "static_reply": f"[PLAY_AUDIO:fold8_bot/{raw_file}]",
                "tts_language": detected_lang
            }
        else:
            state["call_phase"] = "ASK_NAME"
            save_session(session, state)
            return {
                "static_reply": "[PLAY_AUDIO:fold8_bot/fold8_area_not_found.raw]",
                "tts_language": detected_lang
            }

    elif current_phase == "ASK_NAME":
        state["user_name"] = raw_message
        state["call_phase"] = "ASK_PHONE"
        save_session(session, state)
        return {
            "static_reply": "[PLAY_AUDIO:fold8_bot/fold8_step7_ask_phone.raw]",
            "tts_language": detected_lang
        }

    elif current_phase == "ASK_PHONE":
        state["phone_preference"] = raw_message
        state["call_phase"] = "ASK_TIME"
        save_session(session, state)
        return {
            "static_reply": "[PLAY_AUDIO:fold8_bot/fold8_step8_ask_time.raw]",
            "tts_language": detected_lang
        }

    elif current_phase == "ASK_TIME":
        state["callback_time"] = raw_message
        state["call_phase"] = "CLOSING"
        save_session(session, state)
        return {
            "static_reply": "[PLAY_AUDIO:fold8_bot/fold8_step9_closing.raw] [BOOKING_CONFIRMED] [END_CALL]",
            "tts_language": detected_lang,
            "auto_disconnect": True
        }

    # Fallback to LLM for other turns (handling custom queries)
    conversation_history.append(f"User: {raw_message}")
    if len(conversation_history) > MAX_TURNS:
        conversation_history = conversation_history[-MAX_TURNS:]

    history_text = get_db_history_text(session.session_id)
    system_prompt = FOLD8_SYSTEM_PROMPT.format(
        agent_name=agent.name or "Naavya",
        company_name=agent.company_name or "VTech NxtGen Retails LLP",
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

def fold8_prereserve_finalize(response, prep_result):
    state = prep_result["state"]
    session = prep_result["session"]
    conversation_history = prep_result["conversation_history"]

    if "[END_CALL]" in response or "[BOOKING_CONFIRMED]" in response or "[NOT_INTERESTED]" in response:
        state["call_phase"] = "CLOSING"
    else:
        # Detect phase transition from LLM output content
        resp_lower = response.lower()
        if any(kw in resp_lower for kw in ["નવસો નવાણું", "નવસો નવાણુ", "વાઉચર", "બુક કરીએ", "સ્લોટ બુક"]):
            state["call_phase"] = "RESERVATION_PITCHED"
        elif any(kw in resp_lower for kw in ["એરિયા", "વિસ્તાર", "રહો છો", "નજીકનો સ્ટોર"]):
            state["call_phase"] = "ASK_AREA"
        elif any(kw in resp_lower for kw in ["નામ", "શુભ નામ", "પૂરું નામ"]):
            state["call_phase"] = "ASK_NAME"
        elif any(kw in resp_lower for kw in ["નંબર", "સંપર્ક", "બીજો"]):
            state["call_phase"] = "ASK_PHONE"
        elif any(kw in resp_lower for kw in ["સમયે", "સવારે", "બપોરે", "સાંજે"]):
            state["call_phase"] = "ASK_TIME"

    conversation_history.append(f"Agent: {response}")
    state["conversation_history"] = conversation_history
    state["last_bot_message"] = response
    save_session(session, state)
