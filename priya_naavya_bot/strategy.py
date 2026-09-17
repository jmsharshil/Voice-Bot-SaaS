# priya_naavya_bot/strategy.py

import logging
import random
import re
from typing import Dict, Any
from .config import (
    AGENT_NAME,
    COMPANY_NAME,
    MAX_MESSAGE_LENGTH,
    MAX_TURNS,
    STAGE_GREET,
    STAGE_PAIN,
    STAGE_VALUE,
    STAGE_META_PROOF,
    STAGE_TRIAL,
    STAGE_BOOK_DEMO,
    STAGE_CLOSING,
)
from .prompts import PRIYA_NAAVYA_SYSTEM_PROMPT
from conversations.services.core.strategies import save_session, is_farewell

logger = logging.getLogger("PriyaNaavyaBotStrategy")

GREETING_VARIANT_1 = "Namaste sir, main Priya bol rahi hoon, Naavya.ai se... aapka do minute mil sakta hai kya? Ek zaroori baat karni thi, aapke property leads ke baare mein."
LOCKED_GREETING = GREETING_VARIANT_1
OPENING_VARIANTS = [LOCKED_GREETING]

def _priya_sanitise(message: str) -> str:
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
                for t in ["[END_CALL]", "[BOOKING_CONFIRMED]", "[HUMAN_HANDOFF]"]:
                    clean_text = clean_text.replace(t, "")
                clean_text = clean_text.strip()
                if clean_text:
                    history_lines.append(f"{role}: {clean_text}")
            return "\n".join(history_lines)
    except Exception as e:
        logger.error(f"Error building database history for Priya Naavya: {e}")
    return ""


OBJECTION_TARGET_RESPONSES = {
    "AI": "Haan sir, bilkul sahi pakda... main ek AI voice assistant hoon, Naavya.ai ki taraf se. Lekin jo bhi maine bataya, woh sab sach hai... aur yehi toh main prove bhi kar rahi hoon, is call se.",
    "STAFF": "Achha hai sir, team hona zaroori hai bhi... Yeh unki jagah nahi le raha, yeh sirf woh calls pakadta hai, jo raat mein ya busy time mein miss ho jaate hain... jisse aapki team ko bhi, kam bhaagdaud karni pade.",
    "PRICE": "Achha sawaal sir... WhatsApp ya website waala version, das se pachaas hazaar mein shuru hota hai, aur full voice waala jo calls bhi uthaaye, woh pachaas se pachattar hazaar ka hai... Lekin sahi number, aapke business size pe depend karta hai... demo mein Dhruv exact bata denge.",
    "WHATSAPP": "Bilkul sir, abhi bhej deti hoon... Saath mein, ek do minute ka video bhi hai, jo dikhaata hai yeh asal mein kaise kaam karta hai... dekh lijiyega, kal phir baat karte hain.",
    "BUSY": "Koi baat nahi sir, samajh sakti hoon... Bas itna bataiye, agar aapke missed leads waapas milne lagein, toh kya yeh dekhne laayak hoga? Nahi toh main abhi rakhti hoon, aapka din achha rahe."
}


def _match_priya_objection_category(msg: str):
    """Returns objection type key ('AI', 'STAFF', 'PRICE', 'WHATSAPP', 'BUSY') or None."""
    m = msg.lower()

    if re.search(r'\b(ai|a\.i\.)\b', m):
        return "AI"

    ai_keywords = [
        "एआई", "ऐआई", "bot", "बॉट", "बोट", "robot", "रोबोट", "machine", "मशीन",
        "इंसान", "ऑटोमेटेड", "automated", "human", "real person",
        "कौन बोल", "कौन बात", "कौन है", "यही बात कर", "ai बात", "ai call", "bot call",
        "who is this", "who is speaking", "who are you", "kaun bol", "kaun baat", "kaun ho", "kaun hai", "insan",
        "aap ai ho", "bot ho"
    ]
    if any(k in m for k in ai_keywords):
        return "AI"

    staff_keywords = [
        "staff", "स्टाफ", "स्टाफ़", "team", "टीम", "bande", "बंदे",
        "employee", "employees", "एम्प्लॉई", "कर्मचारी", "पहले से",
        "already staff", "already team", "paas staff", "paas team"
    ]
    if any(k in m for k in staff_keywords):
        return "STAFF"

    price_keywords = [
        "price", "prays", "praye", "प्राइस", "प्राइज", "कीमत", "रेट", "rate", "cost", "कौस्ट", "कोस्ट",
        "खर्चा", "kharcha", "charge", "charges", "charg", "चार्च", "चार्ज", "kitna", "kitne", "कितना", "कितने",
        "paise", "paisa", "पैसा", "पैसे", "rs", "rupee", "rupaye", "रुपये", "रुपया"
    ]
    if any(k in m for k in price_keywords):
        return "PRICE"

    whatsapp_keywords = [
        "whatsapp", "whats app", "watsapp", "whtsapp", "व्हाट्सएप", "व्हाट्सऐप", "वाट्सएप",
        "detail", "details", "डिटेल", "डीटेल", "video", "वीडियो", "विडियो",
        "bhej", "bhejo", "भेज", "भेजो", "send", "सेंड", "share", "शेयर"
    ]
    if any(k in m for k in whatsapp_keywords):
        return "WHATSAPP"

    negative_keywords = [
        "interested nahi", "not interested", "nahi chahiye", "नही चाहिए", "नहीं चाहिए",
        "free nahi", "फ्री नहीं", "busy", "बिजी", "time nahi", "टाइम नहीं", "samay nahi", "समय नहीं",
        "ji nahi", "जी नहीं", "abhi nahi", "अभी नहीं", "no", "nahi", "nahin", "ना", "नही", "नहीं",
        "roko", "रुक", "rok", "baad mein", "baad me", "बाद में"
    ]
    if any(k in m for k in negative_keywords):
        return "BUSY"

    return None


def _is_priya_objection_or_query(msg: str) -> bool:
    """Detects if user is asking an objection (price, whatsapp, staff, AI) or giving negative response."""
    return _match_priya_objection_category(msg) is not None


def _advance_stage_flow(current_stage: str, msg: str) -> str:
    # Detect specific objections or queries
    if _is_priya_objection_or_query(msg):
        return current_stage

    # Sequential stage progression
    if current_stage == STAGE_GREET:
        return STAGE_PAIN
    elif current_stage == STAGE_PAIN:
        return STAGE_VALUE
    elif current_stage == STAGE_VALUE:
        return STAGE_META_PROOF
    elif current_stage == STAGE_META_PROOF:
        return STAGE_TRIAL
    elif current_stage == STAGE_TRIAL:
        return STAGE_BOOK_DEMO
    elif current_stage == STAGE_BOOK_DEMO:
        return STAGE_CLOSING
    elif current_stage == STAGE_CLOSING:
        return STAGE_CLOSING
    return STAGE_PAIN


def priya_naavya_strategy(agent, message, session, **kwargs):
    """Non-streaming / HTTP fallback implementation."""
    state: dict = session.state or {}
    raw_message = _priya_sanitise(message)
    msg = raw_message.lower()
    conversation_history: list = state.get("conversation_history", [])

    if is_farewell(msg):
        save_session(session, {})
        return {
            "response": "Koi baat nahi sir, samay dene ke liye shukriya. Agar kabhi zaroorat mehsoos ho, number aapke paas hai. Aapka din shubh rahe! [END_CALL]",
            "should_end": True
        }

    # Zero Latency Connection Greeting (Turn 1)
    if not state.get("intro_shown"):
        selected_variant = random.choice(OPENING_VARIANTS)
        state["intro_shown"] = True
        state["stage"] = STAGE_GREET
        state["conversation_history"] = [f"Agent: {selected_variant}"]
        save_session(session, state)
        return {
            "response": selected_variant,
            "should_end": False
        }

    conversation_history.append(f"User: {raw_message}")
    if len(conversation_history) > MAX_TURNS:
        conversation_history = conversation_history[-MAX_TURNS:]

    current_stage = state.get("stage", STAGE_GREET)

    # Check objection fast-path first
    obj_cat = _match_priya_objection_category(msg)
    if obj_cat in OBJECTION_TARGET_RESPONSES:
        reply = OBJECTION_TARGET_RESPONSES[obj_cat]
        conversation_history.append(f"Agent: {reply}")
        state["conversation_history"] = conversation_history
        save_session(session, state)
        return {
            "response": reply,
            "should_end": False
        }

    next_stage = _advance_stage_flow(current_stage, msg)
    state["stage"] = next_stage
    save_session(session, state)

    history_text = get_db_history_text(session.session_id)

    system_prompt = PRIYA_NAAVYA_SYSTEM_PROMPT.format(
        agent_name=agent.name or AGENT_NAME,
        company_name=agent.company_name or COMPANY_NAME,
        user_message=raw_message,
        history_text=history_text,
        current_stage=next_stage
    )

    from conversations.services.azure_openai_service import generate_response
    reply = generate_response(system_prompt, raw_message)

    res_lower = reply.lower()
    should_end = "[END_CALL]" in reply or next_stage == STAGE_CLOSING or "shukriya" in res_lower

    conversation_history.append(f"Agent: {reply}")
    state["conversation_history"] = conversation_history
    save_session(session, state)

    return {
        "response": reply,
        "should_end": should_end
    }


STAGE_TARGET_RESPONSES = {
    STAGE_PAIN: "Achha sir, aap roughly mahine mein, kitni property leads handle karte hain? ...aur kabhi aisa hua hai ki, koi lead sirf isliye nikal gaya, kyunki reply late ho gaya?",
    STAGE_VALUE: "Yehi toh baat hai sir, Naavya.ai aapke saare calls, aur WhatsApp ka jawaab, turant deta hai... din ho ya raat, Sunday ho ya festival. Aur jaise-jaise baatcheet hoti hai, yeh seekhta jaata hai, ek naye employee se, kahin zyada tez.",
    STAGE_META_PROOF: "Waise sir, ek maze ki baat bataun? Yeh call, jo abhi ho rahi hai, yeh bhi Naavya.ai hi kar raha hai... Aapko pata bhi nahi chala, hai na? Yehi cheez, yeh aapke customers ke saath bhi karega.",
    STAGE_TRIAL: "Main aapko, ek teen din ka free trial de sakti hoon, bina kisi commitment ke... bas dekhiye, kaise kaam karta hai, aapke asli leads pe.",
    STAGE_BOOK_DEMO: "Bahut badhiya sir! Toh main aapko, WhatsApp pe demo ka link bhej deti hoon... aur kal 11 baje, hamari team se Dhruv aapko call karke, poora dikhayenge... theek rahega? [BOOKING_CONFIRMED]",
    STAGE_CLOSING: "Theek hai sir! Link abhi, WhatsApp pe bhej deti hoon, aur kal 11 baje, Dhruv aapko call karenge... Shukriya! [END_CALL]"
}


def priya_naavya_prepare(agent, message, session, detected_language=None, **kwargs):
    """Streaming prepare method called before starting OpenAI LLM streaming."""
    state = session.state or {}
    raw_message = _priya_sanitise(message)
    msg = raw_message.lower()
    conversation_history = state.get("conversation_history", [])

    if is_farewell(msg):
        return {
            "static_reply": "Koi baat nahi sir, samay dene ke liye shukriya. Agar kabhi zaroorat mehsoos ho, number aapke paas hai. Aapka din shubh rahe! [END_CALL]",
            "tts_language": "hi",
            "skip_input_translation": True,
            "skip_output_translation": True,
            "auto_disconnect": True
        }

    # Zero Latency Connection Greeting (Turn 1)
    if not state.get("intro_shown"):
        selected_variant = random.choice(OPENING_VARIANTS)
        state["intro_shown"] = True
        state["stage"] = STAGE_GREET
        state["conversation_history"] = [f"Agent: {selected_variant}"]
        save_session(session, state)
        return {
            "static_reply": selected_variant,
            "tts_language": "hi",
            "skip_input_translation": True,
            "skip_output_translation": True,
            "auto_disconnect": False
        }

    conversation_history.append(f"User: {raw_message}")
    if len(conversation_history) > MAX_TURNS:
        conversation_history = conversation_history[-MAX_TURNS:]

    current_stage = state.get("stage", STAGE_GREET)
    
    # ⚡ OBJECTION / CUSTOM QUERY FAST-PATH (Instant ~150ms response for AI, Staff, Price, WhatsApp, Busy)
    obj_cat = _match_priya_objection_category(msg)
    if obj_cat in OBJECTION_TARGET_RESPONSES:
        static_reply = OBJECTION_TARGET_RESPONSES[obj_cat]
        conversation_history.append(f"Agent: {static_reply}")
        state["conversation_history"] = conversation_history
        save_session(session, state)
        print(f"⚡ [PRIYA ZERO-LATENCY OBJECTION]: Instant reply for Objection '{obj_cat}' -> '{static_reply[:40]}...'")
        return {
            "static_reply": static_reply,
            "tts_language": "hi",
            "skip_input_translation": True,
            "skip_output_translation": True,
            "auto_disconnect": False
        }

    next_stage = _advance_stage_flow(current_stage, msg)
    state["stage"] = next_stage
    save_session(session, state)

    # ⚡ STAGE PROGRESSION FAST-PATH: If user is on happy-path flow without objections, dispatch target response instantly!
    if next_stage in STAGE_TARGET_RESPONSES:
        static_reply = STAGE_TARGET_RESPONSES[next_stage]
        conversation_history.append(f"Agent: {static_reply}")
        state["conversation_history"] = conversation_history
        save_session(session, state)
        print(f"⚡ [PRIYA ZERO-LATENCY]: Instant reply for Stage {next_stage} -> '{static_reply[:40]}...'")
        return {
            "static_reply": static_reply,
            "tts_language": "hi",
            "skip_input_translation": True,
            "skip_output_translation": True,
            "auto_disconnect": (next_stage == STAGE_CLOSING)
        }

    # 🧠 OBJECTION/CUSTOM QUERY: Fallback to LLM streaming with skipped translation
    history_text = get_db_history_text(session.session_id)

    system_prompt = PRIYA_NAAVYA_SYSTEM_PROMPT.format(
        agent_name=agent.name or AGENT_NAME,
        company_name=agent.company_name or COMPANY_NAME,
        user_message=raw_message,
        history_text=history_text,
        current_stage=next_stage
    )

    auto_disconnect = (next_stage == STAGE_CLOSING)

    return {
        "system_prompt": system_prompt,
        "user_message": raw_message,
        "state": state,
        "session": session,
        "conversation_history": conversation_history,
        "strategy_key": "priya_naavya_strategy",
        "tts_language": "hi",
        "skip_input_translation": True,
        "skip_output_translation": True,
        "auto_disconnect": auto_disconnect
    }


def priya_naavya_finalize(response, prep_result):
    """Post-processing callback after OpenAI response stream finishes."""
    state = prep_result.get("state") or {}
    session = prep_result.get("session")
    conversation_history = prep_result.get("conversation_history") or []

    res_lower = response.lower()
    if "[end_call]" in res_lower or "shukriya" in res_lower or "dhanyavaad" in res_lower or state.get("stage") == STAGE_CLOSING:
        state["stage"] = STAGE_CLOSING

    conversation_history.append(f"Agent: {response}")
    state["conversation_history"] = conversation_history
    state["last_bot_message"] = response
    if session:
        save_session(session, state)
    return response


def get_priya_naavya_reprompt(session_state: dict, language: str = "hi") -> str:
    """Generate a language-aware re-prompt after 3s/15s silence."""
    return "Sir, aap sun rahe hain?"
