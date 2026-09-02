import logging
import re
import random
from datetime import datetime
from conversations.services.core.strategies import save_session, sanitise

logger = logging.getLogger(__name__)

STRATEGY_KEY = "icemake"

# ── Step definitions ──
# 0: Greeting & Language Selection
# 1: Customer Name ("Pls tell me your name")
# 2: State ("From which state")
# 3: Address / City ("Address")
# 4: Phone Number ("Number" with validation: if digits < 10, ask to re-enter)
# 5: Number Confirmation ("Confirm number and confirm it's the registered number")
# 6: Ice Make Product ("Which ice make product you are using")
# 7: Issue Description ("Describe issue in [product]")
# 8: Final Confirmation & Ticket Generation ("Thank you")

QUESTIONS = {
    "en": {
        1: "Thanks, could you please tell me your name?",
        2: "It's a pleasure to connect with you {name}! To assist you best, could you please tell me which state you are calling from?",
        3: "Got it, thank you! And what is your city or area address, along with your pincode if available?",
        4: "Could you please share your phone number?",
        6: "Thank you {name}! Which Ice Make product are you using?",
    },
    "hi": {
        1: "धन्यवाद, कृपया अपना नाम बताइए।",
        2: "{name} जी, आपसे बात करके बहुत ख़ुशी हुई! आपकी बेहतर सहायता के लिए, क्या आप बता सकते हैं कि आप किस राज्य से बोल रहे हैं?",
        3: "जी बिल्कुल, धन्यवाद! और आपका शहर, पता, और अगर उपलब्ध हो तो पिनकोड नंबर कौन सा है?",
        4: "कृपया अपना फ़ोन नंबर बता दीजिए।",
        6: "धन्यवाद {name} जी! आप आइस मेक का कौन सा प्रोडक्ट इस्तेमाल कर रहे हैं?",
    },
    "gu": {
        1: "આભાર, કૃપા કરીને તમારું નામ જણાવો.",
        2: "{name} જી, તમારી સાથે વાત કરીને ખૂબ જ આનંદ થયો! તમને શ્રેષ્ઠ રીતે મદદ કરવા માટે, શું તમે જણાવી શકો છો કે તમે કયા રાજ્યમાંથી બોલી રહ્યા છો?",
        3: "ચોક્કસ, આભાર! અને તમારું શહેર, સરનામું અને જો ઉપલબ્ધ હોય તો પિનકોડ નંબર કયો છે?",
        4: "કૃપા કરીને તમારો ફોન નંબર જણાવો.",
        6: "આભાર {name} જી! તમે આઈસ મેકની કઈ પ્રોડક્ટ વાપરી રહ્યા છો?",
    },
    "te": {
        1: "ధన్యవాదాలు, దయచేసి మీ పేరు చెప్పండి.",
        2: "{name} గారూ, మీతో మాట్లాడటం చాలా సంతోషంగా ఉంది! మీకు ఉత్తమంగా సహాయపడటానికి, మీరు ఏ రాష్ట్రం నుండి కాల్ చేస్తున్నారో చెప్పగలరా?",
        3: "సరేనండీ, ధన్యవాదాలు! మరియు మీ నగరం, చిరునామా మరియు అందుబాటులో ఉంటే మీ పిన్‌కోడ్ సంఖ్య ఏమిటి?",
        4: "దయచేసి మీ ఫోన్ నంబర్ తెలపండి.",
        6: "ధన్యవాదాలు {name} గారూ! మీరు ఏ ఐస్ మేక్ ప్రొడక్ట్ ఉపయోగిస్తున్నారు?",
    }
}

def _format_spoken_number(phone_num: str, lang: str) -> str:
    """Formats phone number digit-by-digit into native language spoken words for TTS."""
    if lang == "gu":
        gu_digit_words = {'0': 'ઝીરો', '1': 'એક', '2': 'બે', '3': 'ત્રણ', '4': 'ચાર', '5': 'પાંચ', '6': 'છ', '7': 'સાત', '8': 'આઠ', '9': 'નવ'}
        return ", ".join(gu_digit_words.get(d, d) for d in phone_num)
    elif lang == "hi":
        hi_digit_words = {'0': 'शून्य', '1': 'एक', '2': 'दो', '3': 'तीन', '4': 'चार', '5': 'पांच', '6': 'छह', '7': 'सात', '8': 'आठ', '9': 'नौ'}
        return ", ".join(hi_digit_words.get(d, d) for d in phone_num)
    elif lang == "te":
        te_digit_words = {'0': 'సున్నా', '1': 'ఒకటి', '2': 'రెండు', '3': 'మూడు', '4': 'నాలుగు', '5': 'ఐదు', '6': 'ఆరు', '7': 'ఏడు', '8': 'ఎనిమిది', '9': 'తొమ్మిది'}
        return ", ".join(te_digit_words.get(d, d) for d in phone_num)
    else:
        en_digit_words = {'0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four', '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine'}
        return ", ".join(en_digit_words.get(d, d) for d in phone_num)

def _format_spoken_ticket(ticket_number: str, lang: str) -> str:
    """
    Formats ticket number digit-by-digit with comma pauses for slow, clear, distinct TTS speech pronunciation.
    E.g. C270826418 -> "C, 2, 7, 0, 8, 2, 6, 4, 1, 8"
    """
    if not ticket_number:
        return ""
    
    if lang == "gu":
        gu_digit_words = {'0': 'ઝીરો', '1': 'એક', '2': 'બે', '3': 'ત્રણ', '4': 'ચાર', '5': 'પાંચ', '6': 'છ', '7': 'સાત', '8': 'આઠ', '9': 'નવ'}
        parts = [gu_digit_words.get(ch, ch) if ch.isdigit() else ('સી' if ch == 'C' else ch) for ch in ticket_number]
        return ", ".join(parts)
    elif lang == "hi":
        hi_digit_words = {'0': 'शून्य', '1': 'एक', '2': 'दो', '3': 'तीन', '4': 'चार', '5': 'पांच', '6': 'छह', '7': 'सात', '8': 'आठ', '9': 'नौ'}
        parts = [hi_digit_words.get(ch, ch) if ch.isdigit() else ('सी' if ch == 'C' else ch) for ch in ticket_number]
        return ", ".join(parts)
    elif lang == "te":
        te_digit_words = {'0': 'సున్నా', '1': 'ఒకటి', '2': 'రెండు', '3': 'మూడు', '4': 'నాలుగు', '5': 'ఐదు', '6': 'ఆరు', '7': 'ఏడు', '8': 'ఎనిమిది', '9': 'తొమ్మిది'}
        parts = [te_digit_words.get(ch, ch) if ch.isdigit() else ('సి' if ch == 'C' else ch) for ch in ticket_number]
        return ", ".join(parts)
    else:
        en_digit_words = {'0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four', '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine'}
        parts = [en_digit_words.get(ch, ch) if ch.isdigit() else ('C' if ch == 'C' else ch) for ch in ticket_number]
        return ", ".join(parts)

def _log_translator(user_msg, agent_reply, lang):
    """Helper to log terminal translation asynchronously in a background thread."""
    def _do_log():
        try:
            from conversations.services.translator_service import translate_text
            if lang and lang != "en":
                if user_msg:
                    user_en = translate_text(user_msg, from_lang=lang, to_lang="en")
                    print(f"🗣️ [TRANSLATOR LOG] User ({lang}): '{user_msg}' ➔ English: '{user_en}'")
                if agent_reply:
                    reply_en = translate_text(agent_reply, from_lang=lang, to_lang="en")
                    print(f"🤖 [TRANSLATOR LOG] Agent ({lang}): '{agent_reply}' ➔ English: '{reply_en}'")
        except Exception as e_log:
            logger.debug("Translator log failed: %s", e_log)

    import threading
    threading.Thread(target=_do_log, daemon=True).start()

def icemake_strategy(agent, message, session, mode="telephony", **kwargs):
    """
    Standard entry point for non-streaming / fallback.
    Returns the next dialogue turn response.
    """
    prep = icemake_prepare(agent, message, session, mode=mode, **kwargs)
    response = prep.get("static_reply", "")
    icemake_finalize(response, prep)
    return response

def icemake_prepare(agent, message, session, detected_language=None, mode="telephony", **kwargs):
    """
    Core dialogue processor for ICEMAKE Refrigeration Ltd.
    """
    state = session.state or {}
    raw_message = sanitise(message)
    msg = raw_message.lower().strip()
    
    # Initialize state variables
    if "conversation_history" not in state:
        state["conversation_history"] = []
    
    # Check prefilled customer data from Excel/DB if available
    user_num = kwargs.get("user_number", "") or state.get("registered_mobile", "") or getattr(session, "user_number", "")
    if user_num and user_num != "unknown" and not state.get("prefill_checked"):
        try:
            from icemake_bot.services import get_customer_prefill_data
            prefill = get_customer_prefill_data(user_num)
            state["prefill_checked"] = True
            if prefill.get("is_prefilled"):
                state["is_prefilled"] = True
                for pk, pv in prefill.items():
                    if pv and not state.get(pk):
                        state[pk] = pv
        except Exception as e_pf:
            logger.warning("Strategy prefill check notice: %s", e_pf)

    current_step = state.get("current_step", 0)
    lang = state.get("selected_language", None)
    
    # ── STEP 0: LANGUAGE SELECTION ──
    if current_step == 0:
        if not state.get("intro_shown"):
            greeting = "Welcome to Ice Make twenty four by seven service support. आप किस भाषा में बात करना पसंद करेंगे?"
            state["intro_shown"] = True
            state["current_step"] = 0
            state["conversation_history"] = [f"Agent: {greeting}"]
            save_session(session, state)
            return {
                "static_reply": greeting,
                "tts_language": "hi",
                "skip_output_translation": True,
                "strategy_key": STRATEGY_KEY,
                "mode": mode,
                "session": session,
                "state": state
            }
        else:
            unsupported_keywords = [
                "marathi", "marthi", "मराठी", "मराठि",
                "tamil", "tamizh", "தமிழ்", "तमिल", "तमिळ",
                "kannada", "kanada", "కన్నడ", "കന്നഡ", "कन्नड़", "कन्नड",
                "malayalam", "മലയാളം", "मलयालम",
                "bengali", "bangla", "বাংলা", "बंगाली", "बांग्ला",
                "punjabi", "panjabi", "ਪੰਜਾਬੀ", "पंजाबी",
                "urdu", "اردو", "उर्दू",
                "french", "फ़्रेंच", "फ्रेंच",
                "german", "जर्मन",
                "spanish", "स्पैनिश", "स्पेनिश",
                "arabic", "عربي", "अरबी",
                "odia", "oriya", "ଓଡ଼િଆ", "उड़िया", "ओड़िया"
            ]
            
            if any(k in msg for k in [
                "gujarati", "gujrati", "gujrat", "guj", "gujarathi", "gujrathi",
                "ગુજરાતી", "ગુજરાતિ", "ગુજરાત", "ગુજરાતીમાં", "ગુજ", "હા",
                "गुजराती", "गुजराति", "गुजरात", "गिजराती", "गुजरती", "गुजरातीं","गुजराती?"
            ]):
                lang = "gu"
            elif any(k in msg for k in [
                "telugu", "telgu", "telugoo", "tlg", "telegu",
                "తెలుగు", "తెలుగూ", "తెలుగులో", "తెలుగులొ",
                "तेलुगु", "तेलुगू", "तेलगु", "तेलगू", "तेलुगु में",
                "તેલુગૂ", "તેલુગુ"
            ]):
                lang = "te"
            elif any(k in msg for k in [
                "hindi", "hindu", "hnd", "hindhi",
                "हिंदी", "हिन्दी", "हिन्दि", "हिंदी में", "हिन्दी में",
                "હિંદી", "હિન્દી", "હિન્દીમાં", "હિંદીમાં",
                "హిందీ"
            ]):
                lang = "hi"
            elif any(k in msg for k in [
                "english", "inglish", "eng", "angrezi", "angreji",
                "इंग्लिश", "अंग्रेजी", "अंग्रेज़ी", "इंग्लिश में",
                "ઈંગ્લીશ", "અંગ્રેજી", "ઇંગ્લિશ",
                "ఇంగ్లీష్"
            ]):
                lang = "en"
            elif any(k in msg for k in unsupported_keywords):
                lang = None
            else:
                if re.search(r'[\u0a80-\u0aff]', raw_message):
                    lang = "gu"
                elif re.search(r'[\u0c00-\u0c7f]', raw_message):
                    lang = "te"
                elif re.search(r'[\u0900-\u097f]', raw_message):
                    # Check if Devanagari message contains Gujarati phonetic words
                    if any(w in msg for w in ["गुजराती", "गुजरात", "गिजराती", "गुजरती","गुजराती?"]):
                        lang = "gu"
                    else:
                        lang = "hi"
                else:
                    lang = "en"
            
            if not lang:
                if re.search(r'[\u0a80-\u0aff]', raw_message):
                    reply = "હાલમાં અમે માત્ર ઈંગ્લીશ, હિન્દી, ગુજરાતી અને તેલુગુમાં સેવા પૂરી પાડીએ છીએ. તમે કઈ ભાષામાં આગળ વધવા માંગો છો?"
                    tts_lang = "gu"
                elif re.search(r'[\u0c00-\u0c7f]', raw_message):
                    reply = "ప్రస్తుతానికి మేము ఇంగ్లీష్, హిందీ, గుజరాతీ మరియు తెలుగు భాషలలో మాత్రమే సేవలను అందిస్తున్నాము. మీరు ఏ భాషలో కొనసాగాలనుకుంటున్నారు?"
                    tts_lang = "te"
                elif re.search(r'[\u0900-\u097f]', raw_message):
                    reply = "फ़िलहाल हम केवल इंग्लिश, हिंदी, गुजराती और तेलुगु में सेवा प्रदान करते हैं। आप किस भाषा में बात करना चाहेंगे?"
                    tts_lang = "hi"
                else:
                    reply = "Currently, we support English, Hindi, Gujarati, and Telugu. Which language would you like to continue in?"
                    tts_lang = "en"
                
                state["current_step"] = 0
                state["conversation_history"].append(f"User: {raw_message}")
                state["conversation_history"].append(f"Agent: {reply}")
                save_session(session, state)
                _log_translator(raw_message, reply, tts_lang)
                return {
                    "static_reply": reply,
                    "tts_language": tts_lang,
                    "skip_output_translation": True,
                    "strategy_key": STRATEGY_KEY,
                    "mode": mode,
                    "session": session,
                    "state": state
                }
            
            state["selected_language"] = lang
            
            # Check pre-filled customer details if available
            cust_name = state.get("customer_name", "")
            prod_name = state.get("machine_model_no", "") or state.get("product_name", "")

            if state.get("is_prefilled") and (cust_name or prod_name):
                if cust_name and prod_name:
                    state["current_step"] = 7  # Jump directly to Issue Description
                    if lang == "hi":
                        reply = f"धन्यवाद। नमस्ते {cust_name} जी! हम देख सकते हैं कि आप अपने आइस मेक {prod_name} के संबंध में कॉल कर रहे हैं। कृपया अपनी समस्या विस्तार से बताइए।"
                    elif lang == "gu":
                        reply = f"આભાર. નમસ્તે {cust_name} જી! અમે જોઈ શકીએ છીએ કે તમે તમારા આઈસ મેક {prod_name} અંગે કૉલ કરી રહ્યા છો. કૃપા કરીને તમારી સમસ્યા વિગતવાર જણાવો."
                    elif lang == "te":
                        reply = f"ధన్యవాదాలు. నమస్కారం {cust_name} గారు! మీరు మీ ఐస్ మేక్ {prod_name} గురించి కాల్ చేస్తున్నట్లు గమనించాము. దయచేసి మీ సమస్యను వివరించండి."
                    else:
                        reply = f"Thank you. Welcome Mr. {cust_name}! I see you are calling regarding your Ice Make {prod_name}. Could you please describe the issue you are experiencing?"
                elif cust_name:
                    state["current_step"] = 6  # Ask for product directly
                    if lang == "hi":
                        reply = f"धन्यवाद। नमस्ते {cust_name} जी! आप आइस मेक का कौन सा प्रोडक्ट इस्तेमाल कर रहे हैं?"
                    elif lang == "gu":
                        reply = f"આભાર. નમસ્તે {cust_name} જી! તમે આઈસ મેકની કઈ પ્રોડક્ટ વાપરી રહ્યા છો?"
                    elif lang == "te":
                        reply = f"ధన్యవాదాలు. నమస్కారం {cust_name} గారు! మీరు ఏ ఐస్ మేక్ ప్రొడక్ట్ ఉపయోగిస్తున్నారు?"
                    else:
                        reply = f"Thank you. Welcome Mr. {cust_name}! Which Ice Make product are you using?"
                else:
                    state["current_step"] = 1
                    reply = QUESTIONS[lang][1]
            else:
                state["current_step"] = 1
                reply = QUESTIONS[lang][1]

            state["conversation_history"].append(f"User: {raw_message}")
            state["conversation_history"].append(f"Agent: {reply}")
            save_session(session, state)
            _log_translator(raw_message, reply, lang)

            return {
                "static_reply": reply,
                "tts_language": lang,
                "skip_output_translation": True,
                "strategy_key": STRATEGY_KEY,
                "mode": mode,
                "session": session,
                "state": state
            }

    prev_step = current_step
    state["conversation_history"].append(f"User: {raw_message}")
    _log_translator(raw_message, None, lang)

    # ── STEP 1: Process Customer Name ──
    if prev_step == 1:
        clean_name = _clean_conversational_text(raw_message)
        state["customer_name"] = clean_name
        next_step = 2
        name_to_use = clean_name if clean_name and clean_name != "Not Provided" else ""
        
        q2_template = QUESTIONS[lang][2]
        if name_to_use:
            reply = q2_template.format(name=name_to_use)
        else:
            if lang == "hi":
                reply = "आपसे बात करके बहुत ख़ुशी हुई! आपकी बेहतर सहायता के लिए, क्या आप बता सकते हैं कि आप किस राज्य से बोल रहे हैं?"
            elif lang == "gu":
                reply = "તમારી સાથે વાત કરીને ખૂબ જ આનંદ થયો! તમને શ્રેષ્ઠ રીતે મદદ કરવા માટે, શું તમે જણાવી શકો છો કે તમે કયા રાજ્યમાંથી બોલી રહ્યા છો?"
            elif lang == "te":
                reply = "మీతో మాట్లాడటం చాలా సంతోషంగా ఉంది! మీకు ఉత్తమంగా సహాయపడటానికి, మీరు ఏ రాష్ట్రం నుండి కాల్ చేస్తున్నారో చెప్పగలరా?"
            else:
                reply = "It's a pleasure to connect with you! To assist you best, could you please tell me which state you are calling from?"

    # ── STEP 2: Process State ──
    elif prev_step == 2:
        state["state_name"] = raw_message
        state["city_state"] = f"{state.get('city_name', '')}, {raw_message}".strip(", ")
        next_step = 3
        reply = QUESTIONS[lang][3]

    # ── STEP 3: Process Address / City & Validate Pincode (Must be 6 digits if provided) ──
    elif prev_step == 3:
        six_digit_match = re.search(r'\b\d{6}\b', raw_message)
        digit_matches = re.findall(r'\b\d+\b', raw_message)
        has_pin_keyword = bool(re.search(r'\b(pin|pincode|pin code)\b', raw_message, re.IGNORECASE))
        
        invalid_pincode_attempt = False
        if six_digit_match:
            state["pin_code"] = six_digit_match.group(0)
            state["pincode"] = six_digit_match.group(0)
        elif has_pin_keyword:
            invalid_pincode_attempt = True
        elif digit_matches:
            for d in digit_matches:
                if len(d) in (4, 5, 7, 8):
                    invalid_pincode_attempt = True
                    break

        if invalid_pincode_attempt:
            if lang == "hi":
                reply = "आपका पिनकोड अमान्य लग रहा है। पिनकोड 6 अंकों का होना चाहिए। कृपया अपना 6 अंकों का पिनकोड या पता फिर से बताइए।"
            elif lang == "gu":
                reply = "તમારો પિનકોડ અમાન્ય લાગે છે. પિનકોડ છ અંકનો હોવો જોઈએ. કૃપા કરીને તમારો છ અંકનો પિનકોડ અથવા સરનામું ફરીથી જણાવો."
            elif lang == "te":
                reply = "మీ పిన్‌కోడ్ సరిగ్గా లేదు. పిన్‌కోడ్ 6 అంకెలు ఉండాలి. దయచేసి మీ 6 అంకెల పిన్‌కోడ్‌ను మళ్లీ తెలపండి."
            else:
                reply = "Your pincode seems invalid. Pincode must be 6 digits. Please share your 6-digit pincode or area address again."
            
            state["current_step"] = 3
            state["conversation_history"].append(f"Agent: {reply}")
            save_session(session, state)
            _log_translator(None, reply, lang)
            return {
                "static_reply": reply,
                "tts_language": lang,
                "skip_output_translation": True,
                "strategy_key": STRATEGY_KEY,
                "mode": mode,
                "session": session,
                "state": state
            }

        state["city_name"] = raw_message
        state["company_name"] = raw_message  # Used as address
        state["city_state"] = f"{raw_message}, {state.get('state_name', '')}".strip(", ")
        next_step = 4
        reply = QUESTIONS[lang][4]

    # ── STEP 4: Process Phone Number & Validate (Must be EXACTLY 10 Digits) ──
    elif prev_step == 4:
        digits = "".join(filter(str.isdigit, raw_message))
        if len(digits) != 10:
            if lang == "hi":
                reply = "आपका नंबर अमान्य लग रहा है। कृपया अपना 10 अंकों का मोबाइल नंबर फिर से बताइए।"
            elif lang == "gu":
                reply = "તમારો નંબર અમાન્ય લાગે છે. કૃપા કરીને તમારો દસ અંકનો મોબાઈલ નંબર ફરીથી જણાવો."
            elif lang == "te":
                reply = "మీ నంబర్ సరిగ్గా లేదు. దయచేసి మీ 10 అంకెల మొబైల్ నంబర్‌ను మళ్లీ చెప్పండి."
            else:
                reply = "Your number seems inappropriate. Please tell your ten digit mobile number."
            
            state["current_step"] = 4
            state["conversation_history"].append(f"Agent: {reply}")
            save_session(session, state)
            _log_translator(None, reply, lang)
            return {
                "static_reply": reply,
                "tts_language": lang,
                "skip_output_translation": True,
                "strategy_key": STRATEGY_KEY,
                "mode": mode,
                "session": session,
                "state": state
            }
        else:
            phone_num = digits
            state["registered_mobile"] = phone_num
            next_step = 5
            spoken_num = _format_spoken_number(phone_num, lang)
            if lang == "hi":
                reply = f"धन्यवाद, मैंने आपका नंबर {spoken_num} दर्ज किया है। क्या आप पुष्टि कर सकते हैं कि यह आपका रजिस्टर्ड नंबर है?"
            elif lang == "gu":
                reply = f"આભાર, મેં તમારો નંબર {spoken_num} નોંધ્યો છે. શું તમે પુષ્ટિ કરી શકો છો કે આ તમારો રજિસ્ટર્ડ નંબર છે?"
            elif lang == "te":
                reply = f"ధన్యవాదాలు, నేను మీ నంబర్‌ను {spoken_num} గా నమోదు చేసాను. ఇది మీ రిజిస్టర్డ్ నంబర్ అని ధృవీకరిస్తారా?"
            else:
                reply = f"Thank you, I recorded your number as {spoken_num}. Could you please confirm if this is your registered number?"

    # ── STEP 5: Confirm Registered Number ──
    elif prev_step == 5:
        # Move directly to Step 6 (Product selection) regardless of user response (YES or NO)
        state["number_confirmed"] = True
        next_step = 6
        lang_key = lang if lang in QUESTIONS else "en"
        q6_template = QUESTIONS[lang_key][6]
        cust_name = state.get("customer_name", "")
        name_to_use = cust_name if cust_name and cust_name != "Not Provided" else ""
        
        if name_to_use:
            reply = q6_template.format(name=name_to_use)
        else:
            if lang == "hi":
                reply = "धन्यवाद! आप आइस मेक का कौन सा प्रोडक्ट इस्तेमाल कर रहे हैं?"
            elif lang == "gu":
                reply = "આભાર! તમે આઈસ મેકની કઈ પ્રોડક્ટ વાપરી રહ્યા છો?"
            elif lang == "te":
                reply = "ధన్యవాదాలు! మీరు ఏ ఐస్ మేక్ ప్రొడక్ట్ ఉపయోగిస్తున్నారు?"
            else:
                reply = "Thank you! Which Ice Make product are you using?"

    # ── STEP 6: Process Ice Make Product ──
    elif prev_step == 6:
        product_classified = _classify_issue_type(raw_message)
        state["issue_type"] = product_classified
        state["product_name"] = raw_message if product_classified == "Other" else product_classified
        next_step = 7
        
        if lang == "hi":
            reply = "ठीक है। कृपया अपनी समस्या विस्तार से बताइए। आप दो मिनट तक अपनी समस्या बता सकते हैं। यह कॉल रिकॉर्ड की जा रही है और तुरंत कार्रवाई के लिए इंजीनियर को भेजी जाएगी।"
        elif lang == "gu":
            reply = "સારું. કૃપા કરીને તમારી સમસ્યા વિગતવાર જણાવો. તમે બે મિનિટ સુધી તમારી સમસ્યા જણાવી શકો છો. આ કૉલ રેકોર્ડ કરવામાં આવી રહ્યો છે અને ત્વરિત કાર્યવાહી માટે એન્જિનિયરને મોકલવામાં આવશે."
        elif lang == "te":
            reply = "సరే. దయచేసి మీరు ఎదుర్కొంటున్న సమస్యను వివరించండి. మీరు రెండు నిమిషాల వరకు మీ సమస్యను చెప్పవచ్చు. ఈ కాల్ రికార్డ్ చేయబడుతోంది మరియు వెంటనే చర్య కోసం ఇంజనీర్‌కు పంపబడుతుంది."
        else:
            reply = "Got it. Could you please describe the issue you are facing? You can describe your issue for up to two minutes. This call is recorded and sent to an engineer for immediate action."

    # ── STEP 7: Process Issue Description ──
    elif prev_step == 7:
        state["issue_description"] = raw_message
        next_step = 8

    state["current_step"] = next_step

    # ── STEP 8: Ticket Generation & Completion ──
    if next_step == 8:
        ticket_number = _generate_ticket_number()
        state["ticket_number"] = ticket_number
        
        from conversations.models import Conversation
        conversation = Conversation.objects.filter(session_id=session.session_id).first()
        if conversation:
            _create_ticket_db_record(conversation, state)
        else:
            logger.warning("Conversation record not found for session_id: %s", session.session_id)
        
        spoken_ticket = _format_spoken_ticket(ticket_number, lang)

        if lang == "hi":
            reply = (
                f"धन्यवाद, मैंने आपकी समस्या नोट कर ली है। "
                f"आइस मेक 24 बाय 7 सर्विस सपोर्ट में संपर्क करने के लिए धन्यवाद। "
                f"आपकी शिकायत दर्ज कर ली गई है और आपका शिकायत नंबर {spoken_ticket} है। आपको अपने व्हाट्सएप पर जानकारी मिल जाएगी। "
                f"हमारी सर्विस टीम आपकी शिकायत की समीक्षा करेगी और आगे आपकी सहायता करेगी। आपका दिन शुभ हो। [FLOW_COMPLETE]"
            )
        elif lang == "gu":
            reply = (
                f"આભાર, મેં તમારી સમસ્યા નોંધ કરી લીધી છે. "
                f"આઈસ મેક સર્વિસ સપોર્ટનો સંપર્ક કરવા બદલ આભાર. "
                f"તમારી ફરિયાદ નોંધાઈ ગઈ છે અને તમારો ફરિયાદ નંબર {spoken_ticket} છે. તમને તમારા વૉટ્સએપ પર વિગતો મળી જશે. "
                f"અમારી સર્વિસ ટીમ તમારી ફરિયાદની સમીક્ષા કરશે અને આગળ તમને મદદ કરશે. તમારો દિવસ શુભ રહે. [FLOW_COMPLETE]"
            )
        elif lang == "te":
            reply = (
                f"ధన్యవాదాలు, నేను మీ సమస్యను నమోదు చేసుకున్నాను. "
                f"ఐస్ మేక్ సర్వీస్ సపోర్ట్‌ను సంప్రదించినందుకు ధన్యవాదాలు. "
                f"మీ ఫిర్యాదు నమోదు చేయబడింది మరియు మీ ఫిర్యాదు సంఖ్య {spoken_ticket}. మీరు మీ వాట్సాప్‌లో వివరాలను అందుకుంటారు. "
                f"మా సర్వీస్ టీమ్ మీ ఫిర్యాదును సమీక్షించి మీకు మరింత సహాయం చేస్తుంది. హావ్ ఎ గుడ్ డే. [FLOW_COMPLETE]"
            )
        else:
            reply = (
                f"Thank you, I have noted your issue. "
                f"Thank you for contacting Ice Make twenty four seven Service Support. "
                f"Your complaint has been registered and your complaint number is {spoken_ticket}. You will receive details on your WhatsApp. "
                f"Our service team will review your complaint and assist you further. Have a good day. [FLOW_COMPLETE]"
            )
            
        state["conversation_history"].append(f"Agent: {reply}")
        save_session(session, state)
        _log_translator(None, reply, lang)

        return {
            "static_reply": reply,
            "tts_language": lang,
            "skip_output_translation": True,
            "strategy_key": STRATEGY_KEY,
            "mode": mode,
            "session": session,
            "state": state,
            "auto_disconnect": True,
            "skip_name_collection": True
        }

    state["conversation_history"].append(f"Agent: {reply}")
    save_session(session, state)
    _log_translator(None, reply, lang)

    return {
        "static_reply": reply,
        "tts_language": lang,
        "skip_output_translation": True,
        "strategy_key": STRATEGY_KEY,
        "mode": mode,
        "session": session,
        "state": state
    }

def icemake_finalize(response, prep_result):
    """
    Finalizes turn state. Programmatic strategy handles history in prepare.
    """
    pass

def _generate_ticket_number() -> str:
    """
    Generates ticket format: C + MMDDYY + 3 digit random code.
    E.g. C030726001
    """
    now = datetime.now()
    date_str = now.strftime("%d%m%y")
    seq = random.randint(100, 999)
    return f"C{date_str}{seq}"

def _extract_clean_ticket_entities(state: dict) -> dict:
    """
    Uses AI/LLM entity extraction to parse raw conversational user answers
    (in Hindi, Hinglish, Gujarati, Telugu, or English) into clean, proper English string values for the Google Sheet.
    """
    import json
    from conversations.services.azure_openai_service import client
    from django.conf import settings

    raw_name = state.get("customer_name", "")
    raw_state = state.get("state_name", "")
    raw_city = state.get("city_name", "")
    raw_address = state.get("company_name", "")
    raw_product = state.get("product_name", "")
    raw_issue = state.get("issue_description", "")

    prompt = f"""
Extract and normalize the following customer support ticket entity values into clean, proper English string values for a CRM spreadsheet.
The original input might contain conversational filler in Hindi, Hinglish, Gujarati, Telugu, or English (e.g. "Mera naam Harshil hai", "Maru naam Yash chhe", "Main Gujarat se hu", "Ji main Ahmedabad me rehta hu", "Meri company Ice Make hai", "Ji usme cooling nahi ho raha hai").

Raw Inputs:
- Customer Name Raw: "{raw_name}"
- State Raw: "{raw_state}"
- City Raw: "{raw_city}"
- Address/Company Raw: "{raw_address}"
- Product Name Raw: "{raw_product}"
- Issue Description Raw: "{raw_issue}"

Rules:
1. "customer_name": Extract ONLY the person's name in Title Case English (e.g., "Mera naam Harshil Mehta hai" -> "Harshil Mehta", "Maru naam Yash chhe" -> "Yash", "Naku peru Jiggar" -> "Jigar", "Hello" -> "Not Provided").
2. "state": Extract ONLY the Indian state name in English (e.g., "Gujarat se hu" -> "Gujarat", "Main UP se hu" -> "Uttar Pradesh", "Rajasthan" -> "Rajasthan").
3. "city": Extract ONLY the city/area name in English Title Case (e.g., "Main Ahmedabad me job करता हूँ" -> "Ahmedabad", "Banswara" -> "Banswara").
4. "address": Extract ONLY the company or address name (including 6-digit pincode if provided by user) in English Title Case (e.g., "Meri company ka naam Ice Make hai, pincode 380015" -> "Ice Make 380015", "XYZ Diary" -> "XYZ Diary").
5. "machine_model_no": Extract ONLY the clean product/machine name in English Title Case (e.g., "Blast Freezer", "Chiller", "Freezer", "Cold Storage Room").
6. "type_of_complaint": Translate and summarize the issue description into 1 short, clean English sentence (e.g., "Freezer is not cooling properly").

Return ONLY a valid JSON object with keys:
{{"customer_name": "...", "state": "...", "city": "...", "address": "...", "machine_model_no": "...", "type_of_complaint": "..."}}
"""

    try:
        response = client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are a precise JSON entity extraction assistant for CRM data entry."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        return data
    except Exception as e:
        logger.error("AI Entity Extraction failed: %s", e)
        return {
            "customer_name": _clean_conversational_text(raw_name),
            "state": _clean_conversational_text(raw_state),
            "city": _clean_conversational_text(raw_city),
            "address": _clean_conversational_text(raw_address),
            "machine_model_no": _clean_conversational_text(raw_product),
            "type_of_complaint": _clean_conversational_text(raw_issue)
        }

def _clean_conversational_text(text: str) -> str:
    if not text:
        return "Not Provided"
    clean = text.strip()
    
    # 1. Strip Devanagari full stops (।), punctuation, and extra symbols first
    clean = re.sub(r'[।॥!?,.\-]', ' ', clean).strip()
    
    # 2. Layered prefix and suffix filler patterns (supporting Devanagari, English, Gujarati, Telugu, Hinglish, and STT phonetic errors)
    remove_patterns = [
        # Unspaced concatenated STT fillers (e.g. मारुनाम, मारुનામ, મારુંનામ, मेरानाम, मायनेम)
        r'^(मारुनाम|मारुनाम्|मारूनाम|मेरानाम|ममेरानाम|मैरानाम|મારુનામ|મારૂનામ|મારુંનામ|મારુનામે|મારુના|મારુનાએમ|मायनेमइज|मायनेम|आईएम|आइएम)\s*',

        # Gujarati & Phonetic Gujarati fillers
        r'^(મારું\s+નામ|મારૂ\s+નામ|નામ|મારુ\s+નામ|મારુ\s+નામે|હું|હૂં|નમસ્તે|હેલો|મારુના\s+એમ\s+ટોક|મારુના\s+એમ|મારુના\s+એમ\s+ટોક|આઈ\s+એમ|આઇ\s+એમ)\s+',
        r'\s+(છે|છુ|છું|બોલું\s+છું|બોલું\s+છુ|નામ\s+છે|બોલી\s+રહ્યા\s+છે|બોલી\s+રહ્યો\s+છું)$',
        
        # Devanagari Hindi & STT Phonetic fillers (e.g. हमारा नाम, मारुना ऐम टॉक, मेरा नाम)
        r'^(हमारा\s+नाम|अमारा\s+नाम|मारुना\s+ऐम\s+टॉक|मारुना\s+ऐम|मारुना\s+एम|मेरा\s+नाम|ममेरा\s+नाम|मेरा\s+नाम\s+है|मेरा\s+नाम्|जी\s+मेरा\s+नाम|जी|मैं|मै|हेलो|हाय|नमस्ते|मारु\s+नाम|मारू\s+नाम|मैरा\s+नाम|माय\s+नेम\s+इज|माय\s+नेम|आई\s+एम|आइ\s+एम)\s+',
        r'\s+(है|हूँ|हूं|बोल\s+रहा\s+हूँ|बोल\s+रही\s+हूँ|बोल\s+रहा\s+हु|बोल\s+रही\s+हु|नाम\s+है|बोल\s+रहा\s+है|बोल\s+रही\s+है|जी|जी।)$',
        r'^(है|हूँ|हूं|टॉक|talk|talking|speaking|जी)\s+|\s+(है|हूँ|हूं|टॉक|talk|talking|speaking|जी)$',
        
        # English / Hinglish fillers
        r'^(hello|hi|hey|namaste|my\s+name\s+is|my\s+name|i\s+am|iam|this\s+is|myself|mera\s+naam|mera\s+nam|mera\s+name|me\s+hu|main\s+hu|mai\s+hu)\s+',
        r'\s+(is\s+my\s+name|speaking|here|talking|bol\s+raha\s+hu|bol\s+rahi\s+hu|baat\s+kar\s+raha\s+hu|baat\s+kar\s+rahi\s+hu)$',
        
        # Telugu fillers
        r'^(naku\s+peru|naa\s+peru|na\s+peru|peru)\s+',
        r'\s+(vachesi|andi|garu)$'
    ]
    
    # Apply 3 iterations to strip multi-layered fillers like "હેલો મારું નામ તક્ષ પટેલ છે" or "मारुना ऐम टॉक झे"
    for _ in range(3):
        for pattern in remove_patterns:
            clean = re.sub(pattern, '', clean, flags=re.IGNORECASE).strip()
    
    # Final cleanup of trailing single verbs, conversational words, or punctuation
    clean = re.sub(r'^(है|हूँ|हूं|hai|hu|છે|છુ|છું|टॉक|talk|speaking|talking)\s+|\s+(है|हूँ|हूं|hai|hu|છે|છુ|છું|टॉक|talk|speaking|talking)$', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'^[^\w\u0900-\u097F\u0A80-\u0AFF\u0C00-\u0C7F]+|[^\w\u0900-\u097F\u0A80-\u0AFF\u0C00-\u0C7F]+$', '', clean).strip()
    
    return clean if clean else text

def _create_ticket_db_record(conversation, state):
    """
    Creates and logs the IcemakeTicket record inside DB with AI entity extraction.
    """
    try:
        from icemake_bot.models import IcemakeTicket
        
        extracted = _extract_clean_ticket_entities(state)
        logger.info("AI Extracted Ticket Data: %s", extracted)

        city_state_str = f"{extracted.get('city', 'Not Provided')}, {extracted.get('state', 'Not Provided')}".strip(", ")
        ticket, _ = IcemakeTicket.objects.update_or_create(
            conversation=conversation,
            defaults={
                "ticket_number": state.get("ticket_number"),
                "language": state.get("selected_language", "en"),
                "registered_mobile": state.get("registered_mobile", ""),
                "customer_name": extracted.get("customer_name", state.get("customer_name", "")),
                "company_name": extracted.get("address", state.get("company_name", "")),
                "city_state": city_state_str,
                "pin_code": state.get("pin_code", ""),
                "machine_model_no": extracted.get("machine_model_no", state.get("product_name", "Not Provided")),
                "machine_sr_no": state.get("machine_sr_no", "Not Provided"),
                "issue_type": state.get("issue_type", "Other"),
                "issue_description": extracted.get("type_of_complaint", state.get("issue_description", "")),
            }
        )
        print(f"🎫 TICKET LOGGED SUCCESSFULLY: {state.get('ticket_number')}")
    except Exception as e:
        logger.error("Failed to create IcemakeTicket: %s", e)

def _append_to_google_sheet(ticket, extracted: dict = None, force=False):
    """
    Appends the logged ticket details to Google Sheets Web App matching new Apps Script schema:
    [complain_id, name, state, address, number, product_name, issue_description, created_at]
    """
    import requests
    import os
    from django.utils.timezone import localtime

    url = os.getenv("GOOGLE_SHEET_WEBAPP_URL") or "https://script.google.com/macros/s/AKfycbypSXeANMEDKfTsT4OtqKD9D8GcYzhH-8dFIf8-afJNC84apPnNWsKSMbPbuYsJXriY8w/exec"
    
    if ticket.google_sheet_synced and not force:
        print(f"[GOOGLE SHEET ALREADY SYNCED]: Ticket #{ticket.ticket_number} already exported to Google Sheet. Skipping.")
        return

    if not extracted:
        extracted = {}

    clean_state = extracted.get("state") or ticket.city_state or "Not Provided"
    clean_city = extracted.get("city") or "Not Provided"
    clean_name = extracted.get("customer_name") or ticket.customer_name or "Not Provided"
    clean_address = extracted.get("address") or ticket.company_name or "Not Provided"
    clean_model = extracted.get("machine_model_no") or ticket.machine_model_no or "Not Provided"
    clean_issue = extracted.get("type_of_complaint") or ticket.issue_description or "Not Provided"

    created_at_str = localtime(ticket.created_at).strftime("%Y-%m-%d %H:%M:%S")

    calling_number = "Not Provided"
    try:
        from conversations.models import CallDetailRecord
        from datetime import timedelta
        
        bot_numbers = [
            "919484959435", "9484959435",
            "8758007011", "918758007011",
            "7971019486", "917971019486",
            "7971017251", "917971017251",
            "7969016753", "917969016753",
            "100259134222", "91100259134222",
            "unknown"
        ]

        def is_bot_did(num_str):
            if not num_str:
                return True
            digits = "".join(filter(str.isdigit, str(num_str)))
            return not digits or any(b in digits for b in bot_numbers)

        raw_c = str(ticket.conversation.user_number or "").strip() if ticket.conversation else ""

        # 1. Direct CDR linked to conversation (received from Ice Make POST API)
        cdr = None
        if ticket.conversation:
            cdr = CallDetailRecord.objects.filter(conversation=ticket.conversation).exclude(phone_number="unknown").order_by("-received_at").first()
        
        # 2. Wait up to 8 seconds for IVRManager POST API CDR to land if not in DB yet
        has_real_cdr_number = cdr and cdr.phone_number and cdr.phone_number != "unknown" and not is_bot_did(cdr.phone_number)
        if not has_real_cdr_number:
            import time
            ice_dids = ["7971019486", "917971019486", "+917971019486"]
            for _ in range(4):
                time.sleep(2)
                if ticket.conversation:
                    ticket.conversation.refresh_from_db()
                    cdr = CallDetailRecord.objects.filter(conversation=ticket.conversation).exclude(phone_number="unknown").order_by("-received_at").first()
                    if cdr and cdr.phone_number and not is_bot_did(cdr.phone_number):
                        print(f"🎯 [GOOGLE SHEET RESOLVED REAL CALLER FROM LINKED CDR]: {cdr.phone_number}")
                        break
                
                t_time = ticket.created_at
                for candidate in CallDetailRecord.objects.filter(
                    did__in=ice_dids,
                    received_at__gte=t_time - timedelta(minutes=15),
                    received_at__lte=t_time + timedelta(minutes=15)
                ).exclude(phone_number="unknown").order_by("-received_at"):
                    if candidate.phone_number and not is_bot_did(candidate.phone_number):
                        cdr = candidate
                        print(f"🎯 [GOOGLE SHEET RESOLVED REAL CALLER FROM CDR CANDIDATE]: {cdr.phone_number}")
                        break
                if cdr and cdr.phone_number and not is_bot_did(cdr.phone_number):
                    break

        def get_clean_caller_number():
            if cdr and cdr.phone_number and cdr.phone_number != "unknown" and not is_bot_did(cdr.phone_number):
                return str(cdr.phone_number).strip()
            if cdr and getattr(cdr, "did", None) and cdr.did != "unknown" and not is_bot_did(cdr.did):
                return str(cdr.did).strip()
            reg_mob = str(ticket.registered_mobile or "").strip()
            if raw_c and raw_c != "unknown" and not is_bot_did(raw_c) and raw_c != reg_mob:
                return str(raw_c).strip()
            if reg_mob and reg_mob.lower() not in ["", "unknown", "not provided"]:
                return reg_mob
            return "Not Provided"

        calling_number = get_clean_caller_number()

    except Exception as e_call:
        logger.warning("Could not fetch calling number: %s", e_call)

    registered_number = ticket.registered_mobile or "Not Provided"

    payload = {
        "complain_id": ticket.ticket_number,
        "customer_name": clean_name,
        "name": clean_name,
        "state": clean_state,
        "city": clean_city,
        "address": clean_address,
        "registered_number": registered_number,
        "number": registered_number,
        "calling_number": calling_number,
        "caller_number": calling_number,
        "product_name": clean_model,
        "machine_model_no": clean_model,
        "issue_description": clean_issue,
        "issue": clean_issue,
        "created_at": created_at_str,
        "date": created_at_str
    }
    
    if ticket.google_sheet_synced:
        print(f"[GOOGLE SHEET ALREADY SYNCED]: Ticket #{ticket.ticket_number} already exported to Google Sheet. Skipping.")
        return

    try:
        response = requests.post(url, json=payload, timeout=25, allow_redirects=True)
        print(f"[Google Sheet Webhook Status]: {response.status_code}, response: {response.text}")
        if response.status_code == 200:
            ticket.google_sheet_synced = True
            ticket.save(update_fields=["google_sheet_synced"])
    except Exception as e:
        logger.error("Failed to append ticket to Google Sheet: %s", e)

def _send_whatsapp_ticket_confirmation(ticket):
    """
    Sends WhatsApp confirmation message with Ice Make ticket details.
    """
    try:
        from bot.services.whatsapp_service import send_whatsapp_message
        
        target_phone = ticket.registered_mobile or (ticket.conversation.user_number if ticket.conversation else None)
        if not target_phone or str(target_phone).strip() in ["unknown", "None", ""]:
            logger.warning("[ICEMAKE WA] No valid phone number to send WhatsApp message.")
            return

        clean_phone = "".join(filter(str.isdigit, str(target_phone)))
        if len(clean_phone) == 10:
            clean_phone = "91" + clean_phone

        wa_text = (
            f"❄️ *Ice Make Refrigeration Ltd. - Service Ticket Confirmation*\n\n"
            f"Dear Customer,\n"
            f"Thank you for contacting Ice Make 24x7 Support. Your complaint has been registered successfully.\n\n"
            f"📋 *Complaint ID:* {ticket.ticket_number}\n"
            f"👤 *Name:* {ticket.customer_name or 'Customer'}\n"
            f"📞 *Registered Phone:* {ticket.registered_mobile or 'N/A'}\n"
            f"⚙️ *Machine Model:* {ticket.machine_model_no or 'N/A'}\n"
            f"🛠️ *Issue Type:* {ticket.issue_type or 'Other'}\n"
            f"📝 *Description:* {ticket.issue_description or 'N/A'}\n\n"
            f"Our technical service team will review your complaint and contact you shortly.\n\n"
            f"Have a great day!\n"
            f"*Ice Make Refrigeration Ltd.*"
        )

        res = send_whatsapp_message(clean_phone, wa_text)
        print(f"📲 [ICEMAKE WA SUCCESS]: WhatsApp confirmation sent to {clean_phone} for Ticket #{ticket.ticket_number}. Response: {res}")
    except Exception as e:
        logger.error("[ICEMAKE WA ERROR] Failed to send WhatsApp confirmation: %s", e)

def _send_whatsapp_engineer_notification(ticket):
    """
    Sends WhatsApp alert to the Service Engineer using ENGINEER_WHATSAPP_NUMBER from .env.
    """
    try:
        import os
        from bot.services.whatsapp_service import send_whatsapp_message
        
        engineer_number = os.getenv("ENGINEER_WHATSAPP_NUMBER") or "919913381306"
        clean_eng = "".join(filter(str.isdigit, str(engineer_number)))
        if len(clean_eng) == 10:
            clean_eng = "91" + clean_eng

        cust_phone = ticket.registered_mobile or (ticket.conversation.user_number if ticket.conversation else "N/A")

        wa_text = (
            f"🚨 *NEW ICEMAKE SERVICE TICKET ALERT*\n\n"
            f"A new complaint ticket has been logged by customer:\n\n"
            f"📋 *Ticket #:* {ticket.ticket_number}\n"
            f"👤 *Customer Name:* {ticket.customer_name or 'N/A'}\n"
            f"📞 *Customer Mobile:* {cust_phone}\n"
            f"📍 *City / State:* {ticket.city_state or 'N/A'}\n"
            f"🏠 *Address:* {ticket.company_name or 'N/A'}\n"
            f"⚙️ *Machine Model:* {ticket.machine_model_no or 'N/A'}\n"
            f"🛠️ *Issue Type:* {ticket.issue_type or 'Other'}\n"
            f"📝 *Description:* {ticket.issue_description or 'N/A'}\n\n"
            f"Please attend to this issue immediately.\n"
            f"*Ice Make Refrigeration Ltd.*"
        )

        res = send_whatsapp_message(clean_eng, wa_text)
        # Check if rate-limited by WASender Account Protection (429)
        if isinstance(res, dict) and (res.get("retry_after") or "Account Protection enabled" in str(res)):
            retry_sec = int(res.get("retry_after", 5)) + 1
            print(f"⏳ [ENGINEER WA RATE LIMIT]: WASender 429 rate limit hit. Pausing {retry_sec}s before retry...")
            import time
            time.sleep(retry_sec)
            res = send_whatsapp_message(clean_eng, wa_text)

        print(f"🚨 [ENGINEER WA ALERT SUCCESS]: Alert sent to Engineer {clean_eng} for Ticket #{ticket.ticket_number}. Response: {res}")
    except Exception as e:
        logger.error("[ENGINEER WA ERROR] Failed to send WhatsApp alert to engineer: %s", e)



def _clean_model_or_serial(text: str) -> str:
    clean = text.strip()
    pattern = r'^(machine|model|serial|number|no|is|of|the|my|this|मशीन|मॉडल|સીરીયલ|સીરિયલ|સીરીયલ\s+નંબર|નંબર|सीरियल|नंबर|नम्बर|का|की|को|है|हो)\s+'
    while True:
        prev = clean
        clean = re.sub(pattern, '', clean, flags=re.IGNORECASE).strip()
        if clean == prev:
            break
            
    clean = re.sub(r'^(है|is|नंबर|नम्बर|નંબર)\s*', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'\s*(है|हैं|is|છે)$', '', clean, flags=re.IGNORECASE).strip()
    
    return clean if clean else text

def _classify_issue_type(text: str) -> str:
    msg = text.lower().strip()
    
    # 1. BLAST FREEZER variations (English, Hindi, Gujarati)
    blast_keywords = [
        "blast", "ब्लास्ट", "બ્લાસ્ટ", "લાસ્ટ", "ફાસ્ટ", "ગ્લાસ", "પ્લસ", "પ્લાસ્ટ", "મસ્ત", "ક્લાસ",
        "last freezer", "fast freezer", "glass freezer", "plus freezer", "plast freezer", 
        "must freezer", "class freezer", "lost freezer", "blast", "blst"
    ]
    if any(kw in msg for kw in blast_keywords):
        return "Blast Freezer"
        
    # 2. CHILLER variations (English, Hindi, Gujarati)
    chiller_keywords = [
        "chiller", "ચિલર", "ચિલર", "ચિલર", "ચિલર", "ચિલર", "चिलर", "चिल्लर", "cheeler", "chiler", "chila", "chillar"
    ]
    if any(kw in msg for kw in chiller_keywords):
        return "Chiller"
        
    # 3. FREEZER variations (English, Hindi, Gujarati)
    freezer_keywords = [
        "freezer", "ફ્રીઝર", "ફ્રિઝર", "ફ્રીજર", "ફ્રિજર", "फ्रीजर", "फ्रीज़र", "फ़्रीज़र", "फ्रेशर", "frez", "frezer", "frizer"
    ]
    if any(kw in msg for kw in freezer_keywords):
        return "Freezer"
        
    return "Other"
