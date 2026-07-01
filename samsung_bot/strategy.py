# samsung_bot/strategy.py

import logging
from typing import Dict, Any
from .prompts import SAMSUNG_SYSTEM_PROMPT, get_samsung_lang_instruction
from conversations.services.core.strategies import save_session, build_history_text, is_farewell

logger = logging.getLogger("SamsungBotStrategy")

MAX_MESSAGE_LENGTH = 1000
MAX_TURNS = 10

def _samsung_sanitise(message: str) -> str:
    return message.strip()[:MAX_MESSAGE_LENGTH]

def is_negative(msg: str) -> bool:
    negatives = [
        "no", "na", "naa", "nathi", "not", "busy", "ना", "नहीं", "नही", "व्यस्त", "बिजी", "nahi", "nahin",
        "ના", "નથી", "નાજી", "પછી", "નથી વાત", "નથી લેવો", "રસ નથી",
        "wrong number", "ખોટો નંબર", "busy", "loko", "nakko", "pachi", "badme"
    ]
    return any(neg in msg for neg in negatives)

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
        reply = "નમસ્તે! હું નીલ છું. હું VTech Samsung Cafe તરફથી વાત કરી રહ્યો છું. શું મારી વાત Customer જી સાથે થઈ રહી છે?"
        state["intro_shown"] = True
        state["call_phase"] = "GREETING_REPLY"
        state["conversation_history"] = [f"Agent: {reply}"]
        save_session(session, state)
        return reply

    conversation_history.append(f"User: {raw_message}")
    if len(conversation_history) > MAX_TURNS:
        conversation_history = conversation_history[-MAX_TURNS:]

    current_phase = state.get("call_phase", "GREETING_REPLY")

    if current_phase == "GREETING_REPLY":
        if is_negative(msg):
            reply = "કોઈ વાંધો નહીં. તમારો સમય આપવા બદલ આભાર. તમારો દિવસ શુભ રહે. [END_CALL]"
            state["call_phase"] = "CLOSING"
        else:
            reply = "નમસ્તે Customer જી. તમે થોડા દિવસ પહેલા Samsung Product માટે ઇન્ટરેસ્ટ દર્શાવ્યો હતો એટલે તમને કોલ કર્યો છે. શું તમારી સાથે 2 મિનિટ વાત થઈ શકે?"
            state["call_phase"] = "ASK_CONSENT"
            
    elif current_phase == "ASK_CONSENT":
        if is_negative(msg):
            reply = "કોઈ વાંધો નહીં. તમારો સમય આપવા બદલ આભાર. તમારો દિવસ શુભ રહે. [END_CALL]"
            state["call_phase"] = "CLOSING"
        else:
            reply = "ઓકે. તો શું હું જાણી શકું કે તમે અત્યારે કયો ફોન વાપરી રહ્યા છો?"
            state["call_phase"] = "ASK_PHONE_INFO"
            
    elif current_phase == "ASK_PHONE_INFO":
        reply = "ઓકે. તો શું તમે નવો સ્માર્ટફોન લેવાનું વિચારી રહ્યા છો કે પછી બીજી કોઈ Samsung ની Product માં ઇન્ટરેસ્ટ ધરાવો છો જેમ કે Watch, Tablet કે Laptop?"
        state["phone_info"] = raw_message
        state["call_phase"] = "ASK_INTEREST"
        
    elif current_phase == "ASK_INTEREST":
        if is_negative(msg):
            reply = "કોઈ વાંધો નહીં. તમારો કિંમતી સમય આપવા માટે આભાર. તમારો દિવસ શુભ રહે. [END_CALL]"
            state["call_phase"] = "CLOSING"
        else:
            reply = "ખૂબ સરસ. મને કહો, તમે કયા એરિયામાં રહો છો જેથી ત્યાંના નજીકના Samsung Store ની ટીમ તમારો સંપર્ક કરી શકે."
            state["interest_info"] = raw_message
            state["call_phase"] = "ASK_ADDRESS"
            
    elif current_phase == "ASK_ADDRESS":
        reply = "આભાર. નજીકના Samsung Store ની ટીમ ટૂંક સમયમાં તમારો સંપર્ક કરશે. તમારો કિંમતી સમય આપવા બદલ આભાર. તમારો દિવસ શુભ રહે. [END_CALL]"
        state["address"] = raw_message
        state["call_phase"] = "CLOSING"

    else:
        # Fallback to LLM
        history_text = build_history_text(conversation_history)
        system_prompt = SAMSUNG_SYSTEM_PROMPT.format(history_text=history_text)
        from conversations.services.azure_openai_service import generate_response
        reply = generate_response(system_prompt, raw_message)

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
        reply = "નમસ્તે! હું નીલ છું. હું VTech Samsung Cafe તરફથી વાત કરી રહ્યો છું. શું મારી વાત Customer જી સાથે થઈ રહી છે?"
        state["intro_shown"] = True
        state["call_phase"] = "GREETING_REPLY"
        state["conversation_history"] = [f"Agent: {reply}"]
        save_session(session, state)
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

    history_text = build_history_text(conversation_history)
    detected_lang = state.get("detected_language", "gu")
    system_prompt = SAMSUNG_SYSTEM_PROMPT.format(history_text=history_text)

    current_phase = state.get("call_phase", "GREETING_REPLY")

    if current_phase == "GREETING_REPLY":
        if is_negative(msg):
            state["call_phase"] = "CLOSING"
            save_session(session, state)
            return {
                "static_reply": "[PLAY_AUDIO:samsung_bot/samsung_rejection.raw] [END_CALL]",
                "tts_language": detected_lang,
                "auto_disconnect": True,
                "skip_name_collection": True
            }
        else:
            state["call_phase"] = "ASK_CONSENT"
            save_session(session, state)
            return {
                "static_reply": "[PLAY_AUDIO:samsung_bot/samsung_step2_ask_consent.raw]",
                "tts_language": detected_lang
            }

    elif current_phase == "ASK_CONSENT":
        if is_negative(msg):
            state["call_phase"] = "CLOSING"
            save_session(session, state)
            return {
                "static_reply": "[PLAY_AUDIO:samsung_bot/samsung_rejection.raw] [END_CALL]",
                "tts_language": detected_lang,
                "auto_disconnect": True,
                "skip_name_collection": True
            }
        else:
            state["call_phase"] = "ASK_PHONE_INFO"
            save_session(session, state)
            return {
                "static_reply": "[PLAY_AUDIO:samsung_bot/samsung_step3_ask_phone.raw]",
                "tts_language": detected_lang
            }

    elif current_phase == "ASK_PHONE_INFO":
        state["phone_info"] = raw_message
        state["call_phase"] = "ASK_INTEREST"
        save_session(session, state)
        return {
            "static_reply": "[PLAY_AUDIO:samsung_bot/samsung_step4_ask_interest.raw]",
            "tts_language": detected_lang
        }

    elif current_phase == "ASK_INTEREST":
        if is_negative(msg):
            state["call_phase"] = "CLOSING"
            save_session(session, state)
            return {
                "static_reply": "[PLAY_AUDIO:samsung_bot/samsung_rejection.raw] [END_CALL]",
                "tts_language": detected_lang,
                "auto_disconnect": True,
                "skip_name_collection": True
            }
        else:
            state["interest_info"] = raw_message
            state["call_phase"] = "ASK_ADDRESS"
            save_session(session, state)
            return {
                "static_reply": "[PLAY_AUDIO:samsung_bot/samsung_step5_ask_address.raw]",
                "tts_language": detected_lang
            }

    elif current_phase == "ASK_ADDRESS":
        state["address"] = raw_message
        state["call_phase"] = "CLOSING"
        save_session(session, state)
        return {
            "static_reply": "[PLAY_AUDIO:samsung_bot/samsung_step6_closing.raw] [END_CALL]",
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

    conversation_history.append(f"Agent: {response}")
    state["conversation_history"] = conversation_history
    state["last_bot_message"] = response
    save_session(session, state)
