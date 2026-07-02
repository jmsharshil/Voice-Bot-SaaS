from conversations.models import ConversationSession
import uuid
import re
import time
from conversations.services.core.strategies import (
    ai_voice_bot_strategy,
    insurance_transaction_strategy,
    education_qualification_strategy,
    ai_voice_bot_prepare,
    ai_voice_bot_finalize,
    education_qualification_prepare,
    education_qualification_finalize,
    realestate_inquiry_strategy,        
    realestate_inquiry_prepare,         
    realestate_inquiry_finalize,
    interview_bot_strategy,        
    interview_bot_prepare,         
    interview_bot_finalize,
    insurance_transaction_prepare,
    insurance_transaction_finalize,
    automobile_qualification_strategy,
    automobile_qualification_prepare,
    automobile_qualification_finalize,
    hospital_minimal_strategy,
    hospital_minimal_prepare,
    hospital_minimal_finalize,
)
try:
    from automobile_bot.strategy import (
        automobile_Naavya_strategy,
        automobile_Naavya_prepare,
        automobile_Naavya_finalize,
    )
except ImportError:
    automobile_Naavya_strategy = None
    automobile_Naavya_prepare = None
    automobile_Naavya_finalize = None

try:
    from loan_bot.strategy import (
        loan_bot_strategy,
        loan_bot_prepare,
        loan_bot_finalize,
    )
except ImportError:
    loan_bot_strategy = None
    loan_bot_prepare = None
    loan_bot_finalize = None

try:
    from reminder_bot.strategy import (
        reminder_bot_strategy,
        reminder_bot_prepare,
        reminder_bot_finalize,
    )
except ImportError:
    reminder_bot_strategy = None
    reminder_bot_prepare = None
    reminder_bot_finalize = None

try:
    from temp_real_estate_bot.strategy import (
        temp_real_estate_strategy,
        temp_real_estate_prepare,
        temp_real_estate_finalize,
    )
except ImportError:
    temp_real_estate_strategy = None
    temp_real_estate_prepare = None
    temp_real_estate_finalize = None

try:
    from enogic_bot.strategy import (
        enogic_bot_strategy,
        enogic_bot_prepare,
        enogic_bot_finalize,
    )
except ImportError:
    enogic_bot_strategy = None
    enogic_bot_prepare = None
    enogic_bot_finalize = None

try:
    from samsung_bot.strategy import (
        samsung_store_strategy,
        samsung_store_prepare,
        samsung_store_finalize,
    )
except ImportError:
    samsung_store_strategy = None
    samsung_store_prepare = None
    samsung_store_finalize = None

try:
    from samsung_llm_bot.strategy import (
        samsung_llm_strategy,
        samsung_llm_prepare,
        samsung_llm_finalize,
    )
except ImportError:
    samsung_llm_strategy = None
    samsung_llm_prepare = None
    samsung_llm_finalize = None

from conversations.services.core.behavior_router import get_role_strategy
from agents.models import VoiceAgent
from django.core.cache import cache

STRATEGY_MAP = {
    "ai_voice_bot": ai_voice_bot_strategy,
    "insurance":    insurance_transaction_strategy,
    "education": education_qualification_strategy,
    "real_estate":  realestate_inquiry_strategy,
    "interview_bot": interview_bot_strategy,
    "automobile": automobile_qualification_strategy,
    "hospital_minimal": hospital_minimal_strategy,
}
if automobile_Naavya_strategy:
    STRATEGY_MAP["automobile_Naavya"] = automobile_Naavya_strategy
if loan_bot_strategy:
    STRATEGY_MAP["loan_strategy"] = loan_bot_strategy
if reminder_bot_strategy:
    STRATEGY_MAP["reminder_strategy"] = reminder_bot_strategy
if temp_real_estate_strategy:
    STRATEGY_MAP["temp_real_estate_strategy"] = temp_real_estate_strategy
if enogic_bot_strategy:
    STRATEGY_MAP["enogic_strategy"] = enogic_bot_strategy
if samsung_store_strategy:
    STRATEGY_MAP["samsung_store_strategy"] = samsung_store_strategy
if samsung_llm_strategy:
    STRATEGY_MAP["samsung_llm_strategy"] = samsung_llm_strategy

# ⚡ Streaming support — strategies that support prepare/finalize split
PREPARE_MAP = {
    "ai_voice_bot": ai_voice_bot_prepare,
    "education": education_qualification_prepare,
    "real_estate":  realestate_inquiry_prepare,
    "interview_bot": interview_bot_prepare,
    "insurance": insurance_transaction_prepare,
    "automobile": automobile_qualification_prepare,
    "hospital_minimal": hospital_minimal_prepare,
}
if automobile_Naavya_prepare:
    PREPARE_MAP["automobile_Naavya"] = automobile_Naavya_prepare
if loan_bot_prepare:
    PREPARE_MAP["loan_strategy"] = loan_bot_prepare
if reminder_bot_prepare:
    PREPARE_MAP["reminder_strategy"] = reminder_bot_prepare
if temp_real_estate_prepare:
    PREPARE_MAP["temp_real_estate_strategy"] = temp_real_estate_prepare
if enogic_bot_prepare:
    PREPARE_MAP["enogic_strategy"] = enogic_bot_prepare
if samsung_store_prepare:
    PREPARE_MAP["samsung_store_strategy"] = samsung_store_prepare
if samsung_llm_prepare:
    PREPARE_MAP["samsung_llm_strategy"] = samsung_llm_prepare

FINALIZE_MAP = {
    "ai_voice_bot": ai_voice_bot_finalize,
    "education": education_qualification_finalize,
    "real_estate":  realestate_inquiry_finalize,
    "interview_bot": interview_bot_finalize,
    "insurance": insurance_transaction_finalize, 
    "automobile": automobile_qualification_finalize,
    "hospital_minimal": hospital_minimal_finalize,
}
if automobile_Naavya_finalize:
    FINALIZE_MAP["automobile_Naavya"] = automobile_Naavya_finalize
if loan_bot_finalize:
    FINALIZE_MAP["loan_strategy"] = loan_bot_finalize
if reminder_bot_finalize:
    FINALIZE_MAP["reminder_strategy"] = reminder_bot_finalize
if temp_real_estate_finalize:
    FINALIZE_MAP["temp_real_estate_strategy"] = temp_real_estate_finalize
if enogic_bot_finalize:
    FINALIZE_MAP["enogic_strategy"] = enogic_bot_finalize
if samsung_store_finalize:
    FINALIZE_MAP["samsung_store_strategy"] = samsung_store_finalize
if samsung_llm_finalize:
    FINALIZE_MAP["samsung_llm_strategy"] = samsung_llm_finalize


def _resolve_agent(agent):
    if isinstance(agent, VoiceAgent):
        return agent
    elif isinstance(agent, str):
        cache_key = f"agent_{agent}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        try:
            obj = VoiceAgent.objects.select_related('role_template').get(id=agent)
        except VoiceAgent.DoesNotExist:
            try:
                obj = VoiceAgent.objects.select_related('role_template').get(name=agent)
            except VoiceAgent.DoesNotExist:
                raise ValueError(f"VoiceAgent not found for: {agent}")
        cache.set(cache_key, obj, timeout=300)  # cache for 5 minutes
        return obj
    else:
        raise ValueError(f"Invalid agent type: {type(agent)}")


def process_message(agent, message, session_id=None):

    start_time = time.time()

    # =========================================================
    # 1️⃣ SESSION SETUP
    # =========================================================
    if not session_id:
        session_id = str(uuid.uuid4())

    agent = _resolve_agent(agent)

    session, _ = ConversationSession.objects.get_or_create(
        agent=agent,
        session_id=session_id
    )

    # =========================================================
    # 3️⃣ ROUTE TO STRATEGY
    # =========================================================
    role_name = agent.role_template.role_name if agent.role_template else ""
    strategy_key = get_role_strategy(role_name)
    strategy_fn = STRATEGY_MAP.get(strategy_key, ai_voice_bot_strategy)
    reply = strategy_fn(agent, message, session)

    # =========================================================
    # 4️⃣ FALLBACK
    # =========================================================
    if not reply:
        reply = "I'm sorry, I didn't catch that. Could you please rephrase?"

    print("[TIME] Total Message Time:", time.time() - start_time)
    return reply, session_id


def prepare_streaming(agent, message, session_id=None, **kwargs):
    """
    ⚡ Phase 1 of streaming pipeline.
    Returns dict with either:
    - {"static_reply": "..."} for strategies that don't support streaming (insurance)
      or for static responses (farewell, intro)
    - {"system_prompt": "...", "state": ..., ...} for streaming LLM call
    """
    start_time = time.time()

    if not session_id:
        session_id = str(uuid.uuid4())

    agent = _resolve_agent(agent)

    session, _ = ConversationSession.objects.get_or_create(
        agent=agent,
        session_id=session_id
    )

    role_name = agent.role_template.role_name if agent.role_template else ""
    strategy_key = get_role_strategy(role_name)

    prepare_fn = PREPARE_MAP.get(strategy_key)
    if not prepare_fn:
        # Non-streaming fallback (e.g. insurance — has complex multi-LLM logic)
        strategy_fn = STRATEGY_MAP.get(strategy_key, ai_voice_bot_strategy)
        reply = strategy_fn(agent, message, session, **kwargs)
        if not reply:
            reply = "I'm sorry, I didn't catch that. Could you please rephrase?"
        print("[TIME] Prepare Time (fallback):", round(time.time() - start_time, 3), "s")
        return {"static_reply": reply, "session_id": session_id}

    # ⚡ NAME COLLECTION: If we asked for the user's name last turn, capture it and disconnect
    state = session.state or {}
    if state.get("name_collection_pending"):
        user_name = message.strip()
        print(f"[NAME] USER NAME COLLECTED: {user_name}")
        
        # Save name to session state
        state["user_name"] = user_name
        state.pop("name_collection_pending", None)
        from conversations.services.core.strategies import save_session
        save_session(session, state)

        company = agent.company_name or agent.name
        # Prioritize live detected_language from consumer
        detected_lang = kwargs.get("detected_language") or state.get("detected_language", "hi")
        
        # Multi-lingual farewells (respecting "no name repetition" rule)
        farewells = {
            "hi": f"Bahut achha! Aapki booking note ho gayi hai. {company} ki team aapko jaldi contact karegi. Thank you!",
            "en": f"Perfect! Your booking has been noted. The team from {company} will contact you shortly. Thank you!",
            "gu": f"ખૂબ સરસ! તમારી બુકિંગ નોંધી લેવામાં આવી છે. {company} ની ટીમ તમારો જલ્દી સંપર્ક કરશે. આભાર!"
        }
        farewell = farewells.get(detected_lang, farewells["hi"])

        print("[TIME] Prepare Time:", round(time.time() - start_time, 3), "s")
        return {
            "static_reply": farewell,
            "auto_disconnect": True,
            "session_id": session_id,
            "strategy_key": strategy_key,
            "skip_input_translation": True,
            "skip_output_translation": True,
            "translate_input_to": "original",
            "tts_language": detected_lang,
        }

    # ⚡ LLM-based booking detection: If booking was offered last turn,
    # inject instruction into the system prompt so LLM adds [BOOKING_CONFIRMED] tag
    # NOTE: education strategy uses "visit_invited", others use "booking_offered"
    booking_offered = state.get("booking_offered", False) or state.get("visit_invited", False)

    result = prepare_fn(agent, message, session, **kwargs)
    result["session_id"] = session_id
    result["strategy_key"] = strategy_key

    # If booking was offered AND this is a streaming LLM call (has system_prompt),
    # inject the booking detection instruction
    if booking_offered and "system_prompt" in result:
        result["system_prompt"] += (
            "\n\n⚠️ IMPORTANT INSTRUCTION: "
            "In the previous message, you offered the user a visit/appointment/booking. "
            "If the user is now ACCEPTING or CONFIRMING that offer (saying yes, ok, theek hai, "
            "haan, kal aata hu, sure, etc. in ANY language), you MUST: "
            "1) Confirm their visit/booking in ONE short line (e.g. 'Perfect, aapka visit note ho gaya!') "
            "2) Then IMMEDIATELY ask: 'Aapka shubh naam bata dijiye taaki hum record rakh sake.' "
            "3) Do NOT ask any other questions — no timing, no program info, nothing else. "
            "4) Add the exact tag [BOOKING_CONFIRMED] at the very end of your response. "
            "If the user is NOT confirming (asking a different question, declining, etc.), "
            "do NOT add the tag — just respond normally."
        )
        print(f"[BOOKING] Booking was offered last turn — LLM will detect confirmation")
        # Clear the flag (one-shot check)
        state.pop("booking_offered", None)
        from conversations.services.core.strategies import save_session
        save_session(session, state)

    print("[TIME] Prepare Time:", round(time.time() - start_time, 3), "s")
    return result


def finalize_streaming(response, prep_result):
    """
    ⚡ Phase 2 of streaming pipeline.
    Saves the completed LLM response to session state.
    Checks for [BOOKING_CONFIRMED] tag and booking offer patterns.
    """
    strategy_key = prep_result.get("strategy_key")
    if not strategy_key:
        return  # static reply — nothing to finalize

    finalize_fn = FINALIZE_MAP.get(strategy_key)
    if finalize_fn:
        finalize_fn(response, prep_result)

    # ⚡ Check 1: LLM added auto-disconnect tags
    # [BOOKING_CONFIRMED] = education/realestate visit confirmed
    # [NOT_INTERESTED]    = insurance user not interested
    # [LEAD_COMPLETE]     = insurance lead details fully collected
    for tag in ["[BOOKING_CONFIRMED]", "[NOT_INTERESTED]", "[LEAD_COMPLETE]", "[END_CALL]"]:
        if tag in response:
            # SAFETY CHECK: If the bot response contains a question mark '?', it is asking a question.
            # We must NOT auto-disconnect because the user needs to answer the question!
            if "?" in response:
                print(f"[WARN] Ignored {tag} because the reply contains a question mark '?' and expects an answer from the user.")
                continue
            print(f"[DISCONNECT] {tag} found (strategy={strategy_key}) — auto_disconnect")
            prep_result["auto_disconnect"] = True
            # Skip name collection only for explicit non-interest
            if tag in ["[NOT_INTERESTED]", "[END_CALL]"]:
                prep_result["skip_name_collection"] = True
            return

    # ⚡ Check 2: Bot is OFFERING a visit/booking → mark session for next turn
    from conversations.services.core.strategies import _is_booking_offered
    if _is_booking_offered(response):
        state = prep_result.get("state", {})
        session = prep_result.get("session")
        if state is not None and session:
            state["booking_offered"] = True
            from conversations.services.core.strategies import save_session
            save_session(session, state)
            print(f"[BOOKING] BOOKING OFFERED detected (strategy={strategy_key}) — waiting for user confirmation")










#a extra code chhe je gujrati mate mukyo chhe je banne azure and swram mate kam kare chhe.



# def get_agent_tts_language(agent_id):
#     """
#     Returns tts_language for an agent.
#     Only interview bot returns 'gu' — all others return 'en'.
#     """
#     try:
#         from agents.models import VoiceAgent
#         agent = VoiceAgent.objects.get(id=agent_id)
#         role_name = agent.role_template.role_name if agent.role_template else ""
#         print(f"🔍 Agent role_name: {role_name}")

#         # Only interview bot gets Gujarati
#         if "real_estate" in role_name.lower():
#             return "gu"
#         return "en"
#     except Exception as e:
#         print(f"❌ get_agent_tts_language error: {e}")
#         return "en"

















# REPLACE WITH:
def get_agent_tts_language(agent_id):
    try:
        from agents.models import VoiceAgent
        from conversations.services.core.behavior_router import get_role_strategy
        agent = VoiceAgent.objects.get(id=agent_id)
        role_name = agent.role_template.role_name if agent.role_template else ""
        strategy_key = get_role_strategy(role_name)
        print(f"[LOOKUP] Agent role_name: {role_name} | strategy_key: {strategy_key}")

        if strategy_key in ["real_estate", "reminder_strategy", "temp_real_estate_strategy", "samsung_store_strategy", "samsung_llm_strategy"]:
            return "gu"           # Gujarati, Dhwani voice
        elif strategy_key == "interview_bot":
            return "interview_en" # English only, no translation
        return "en"               # All others — Hinglish
    except Exception as e:
        print(f"[ERROR] get_agent_tts_language error: {e}")
        return "en"