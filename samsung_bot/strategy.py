# samsung_bot/strategy.py

import logging
import re
from typing import Dict, Any
from .prompts import SAMSUNG_SYSTEM_PROMPT
from conversations.services.core.strategies import save_session, is_farewell

logger = logging.getLogger("SamsungBotStrategy")

MAX_MESSAGE_LENGTH = 1000
MAX_TURNS = 10

# Load and embed Samsung intents matcher once at server startup
# This completely eliminates loading latency and terminal progress bars during active calls.
try:
    from automobile_matcher import AutomobileMatcher
    logger.info("Pre-loading Samsung Store intents matcher at server startup...")
    SAMSUNG_MATCHER = AutomobileMatcher("samsung_bot/data/samsung_intents.json")
    logger.info("Samsung Store intents matcher loaded successfully at startup.")
except Exception as e:
    logger.error(f"Failed to initialize global SAMSUNG_MATCHER at startup: {e}")
    SAMSUNG_MATCHER = None

def get_samsung_matcher():
    return SAMSUNG_MATCHER

def _samsung_sanitise(message: str) -> str:
    return message.strip()[:MAX_MESSAGE_LENGTH]

def is_asking_question_or_objection(text: str) -> bool:
    text_lower = text.lower()
    if "?" in text_lower or "？" in text_lower:
        return True
        
    gu_keywords = [
        "શું", "કેમ", "ક્યારે", "કયા", "કયો", "કઈ", "કેવી", "કેવી રીતે", "કેટલા",
        "વિશે", "જણાવો", "માહિતી", "કહો", "કહે", "ભાવ", "કિંમત", "પ્રાઈઝ", "પ્રાઇઝ",
        "મોડેલ", "મોબાઈલ", "મોબાઇલ", "નવો", "નવી", "જણાવશો", "પૂછ", "વાત કરાવ",
        "સાંભળ", "ઓફર", "ડિસ્કાઉન્ટ", "બતાવો"
    ]
    for kw in gu_keywords:
        if kw in text_lower:
            return True
            
    en_keywords = [
        "what", "why", "how", "when", "which", "who", "where", "price", "cost", "detail",
        "query", "question", "info", "about", "latest", "tell", "explain", "model", "phone",
        "mobile", "offer", "discount", "spec", "feature"
    ]
    for kw in en_keywords:
        if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
            return True
            
    return False

def get_db_history_text(session_id: str) -> str:
    from conversations.models import Conversation, Message
    try:
        conv = Conversation.objects.filter(session_id=session_id).first()
        if not conv:
            return ""
        msgs = Message.objects.filter(conversation=conv).order_by("created_at")
        history = []
        for m in msgs:
            role_label = "Agent" if m.role == "bot" else "User"
            history.append(f"{role_label}: {m.text}")
        return "\n".join(history)
    except Exception as e:
        logger.error(f"Error building db history: {e}")
        return ""

def determine_phase_from_reply(reply: str, current_phase: str) -> str:
    reply_lower = reply.lower()
    if "[end_call]" in reply_lower:
        return "CLOSING"
    # Ask for area / address
    if any(kw in reply_lower for kw in ["કયા એરિયા", "એરિયા", "રહો છો", "નજીકના samsung", "store", "સ્ટોર", "સરનામું", "કયા વિસ્તાર", "વિસ્તાર", "રહેશો", "ક્યાં રહો છો"]):
        return "ASK_ADDRESS"
    # Ask about product interest
    if any(kw in reply_lower for kw in ["નવો સ્માર્ટફોન", "ઇન્ટરેસ્ટ", "રસ", "ખરીદવા", "લેવા", "લેવાનું વિચારી", "watch", "tablet", "laptop", "વોચ", "ટેબ્લેટ", "લેપટોપ", "પ્રોડક્ટ"]):
        return "ASK_INTEREST"
    # Ask about current phone
    if any(kw in reply_lower for kw in ["કયો ફોન", "કયો મોબાઇલ", "કયું મોડેલ", "કઈ બ્રાન્ડ", "કયો મોબાઈલ"]):
        return "ASK_PHONE_INFO"
    return current_phase

# ─── NON-STREAMING (text fallback) ───────────────────────

def samsung_store_strategy(agent, message, session, **kwargs):
    state: dict = session.state or {}
    raw_message = _samsung_sanitise(message)
    msg = raw_message.lower()
    conversation_history: list = state.get("conversation_history", [])

    if is_farewell(msg):
        save_session(session, {})
        return "આવજો! [END_CALL]"

    if not state.get("intro_shown"):
        customer_name = state.get("customer_name")
        if customer_name:
            reply = f"નમસ્તે {customer_name} જી! હું નાવ્યા છું. હું VTech Samsung Cafe તરફથી વાત કરી રહી છું."
        else:
            reply = "નમસ્તે! હું નાવ્યા છું. હું VTech Samsung Cafe તરફથી વાત કરી રહી છું."
        state["intro_shown"] = True
        state["call_phase"] = "GREETING_REPLY"
        state["conversation_history"] = [f"Agent: {reply}"]
        save_session(session, state)
        return reply

    conversation_history.append(f"User: {raw_message}")
    if len(conversation_history) > MAX_TURNS:
        conversation_history = conversation_history[-MAX_TURNS:]

    current_phase = state.get("call_phase", "GREETING_REPLY")
    
    # Try to match semantic triggers first (for test compatibility and fast path)
    try:
        matcher = get_samsung_matcher()
        if matcher:
            match_result = matcher.find_match(raw_message, current_phase=current_phase, threshold=0.70)
            if match_result and match_result.get("match_type") != "NONE":
                next_phase = match_result.get("next_phase")
                if next_phase:
                    state["call_phase"] = next_phase
                
                # Map mp3 file to Gujarati transcription text
                mp3_filename = match_result["mp3"]
                raw_filename = mp3_filename.replace(".mp3", ".raw")
                from conversations.consumers import _AUDIO_TRANSCRIPTIONS
                reply = _AUDIO_TRANSCRIPTIONS.get(raw_filename, f"[PLAY_AUDIO:{raw_filename}]")
                if next_phase == "CLOSING" or match_result.get("intent", {}).get("intent_name", "").endswith("closing"):
                    reply += " [END_CALL]"
                    
                state["conversation_history"] = conversation_history
                state["last_bot_message"] = reply
                save_session(session, state)
                return reply
    except Exception as match_err:
        logger.error(f"Error in strategy fast-path match: {match_err}")

    # Fallback to LLM
    history_text = get_db_history_text(session.session_id)
    system_prompt = SAMSUNG_SYSTEM_PROMPT.format(history_text=history_text)
    from conversations.services.azure_openai_service import generate_response
    reply = generate_response(system_prompt, raw_message)
    
    # Determine next phase dynamically from tag or content
    phase_match = re.search(r"\[PHASE:(\w+)\]", reply)
    if phase_match:
        next_phase = phase_match.group(1)
        state["call_phase"] = next_phase
        reply = re.sub(r"\[PHASE:\w+\]", "", reply).strip()
    else:
        state["call_phase"] = determine_phase_from_reply(reply, current_phase)

    conversation_history.append(f"Agent: {reply}")
    state["conversation_history"] = conversation_history
    state["last_bot_message"] = reply
    save_session(session, state)

    return reply


# ─── STREAMING PREPARE / FINALIZE ────────────────────────

def samsung_store_prepare(agent, message, session, detected_language=None, **kwargs):
    state = session.state or {}
    raw_message = _samsung_sanitise(message)
    msg = raw_message.lower()
    conversation_history = state.get("conversation_history", [])

    if detected_language:
        state["detected_language"] = detected_language

    # FAREWELL
    if is_farewell(msg):
        save_session(session, {})
        return {
            "static_reply": "કોઈ વાંધો નહીં. તમારો સમય આપવા બદલ આભાર. તમારો દિવસ શુભ રહે. [END_CALL]",
            "tts_language": detected_language or "gu"
        }

    # INTRO
    if not state.get("intro_shown"):
        customer_name = state.get("customer_name")
        if customer_name:
            reply = f"નમસ્તે {customer_name} જી! હું નાવ્યા છું. હું VTech Samsung Cafe તરફથી વાત કરી રહી છું."
        else:
            reply = "નમસ્તે! હું નાવ્યા છું. હું VTech Samsung Cafe તરફથી વાત કરી રહી છું."
        state["intro_shown"] = True
        state["call_phase"] = "GREETING_REPLY"
        state["conversation_history"] = [f"Agent: {reply}"]
        save_session(session, state)
        if customer_name:
            return {
                "static_reply": reply,
                "tts_language": detected_language or "gu"
            }
        else:
            return {
                "static_reply": "[PLAY_AUDIO:samsung_bot/samsung_step1_greeting.raw]",
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

    history_text = get_db_history_text(session.session_id)
    detected_lang = state.get("detected_language", "gu")
    system_prompt = SAMSUNG_SYSTEM_PROMPT.format(history_text=history_text)

    current_phase = state.get("call_phase", "GREETING_REPLY")

    # Try to match semantic triggers first (essential for automated test suites)
    try:
        matcher = get_samsung_matcher()
        if matcher:
            match_result = matcher.find_match(raw_message, current_phase=current_phase, threshold=0.70)
            if match_result and match_result.get("match_type") != "NONE":
                next_phase = match_result.get("next_phase")
                if next_phase:
                    state["call_phase"] = next_phase
                    save_session(session, state)
                
                mp3_filename = match_result["mp3"]
                raw_filename = mp3_filename.replace(".mp3", ".raw")
                
                auto_disconnect = (next_phase == "CLOSING" or match_result.get("intent", {}).get("intent_name", "").endswith("closing"))
                reply = f"[PLAY_AUDIO:{raw_filename}]"
                if auto_disconnect:
                    reply += " [END_CALL]"
                res = {
                    "static_reply": reply,
                    "tts_language": detected_lang
                }
                if auto_disconnect:
                    res["auto_disconnect"] = True
                    res["skip_name_collection"] = True
                return res
    except Exception as match_err:
        logger.error(f"Error in prepare fast-path match: {match_err}")

    # Fallback logic for ASK_ADDRESS (Dynamic location acknowledgement)
    if current_phase == "ASK_ADDRESS" and not is_asking_question_or_objection(raw_message):
        state["address"] = raw_message
        state["call_phase"] = "CLOSING"
        save_session(session, state)
        
        reply = "[PLAY_AUDIO:samsung_bot/samsung_step6_closing.raw] [END_CALL]"
        return {
            "static_reply": reply,
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

def samsung_store_finalize(response, prep_result):
    state = prep_result["state"]
    session = prep_result["session"]
    conversation_history = prep_result["conversation_history"]

    current_phase = state.get("call_phase", "GREETING_REPLY")
    
    # Extract phase from LLM response tag
    phase_match = re.search(r"\[PHASE:(\w+)\]", response)
    if phase_match:
        next_phase = phase_match.group(1)
        state["call_phase"] = next_phase
        response = re.sub(r"\[PHASE:\w+\]", "", response).strip()
    else:
        next_phase = determine_phase_from_reply(response, current_phase)
        state["call_phase"] = next_phase

    conversation_history.append(f"Agent: {response}")
    state["conversation_history"] = conversation_history
    state["last_bot_message"] = response
    save_session(session, state)
