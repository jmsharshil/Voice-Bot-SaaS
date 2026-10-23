import logging
import re
import random
from datetime import datetime
from conversations.services.core.strategies import save_session, sanitise
from icemake_v2_bot.pincode_service import lookup_pincode

logger = logging.getLogger(__name__)

STRATEGY_KEY = "icemake_v2"

# ── Dynamic Time of Day Greeting Helper ──
def _get_time_greeting(lang: str = "en") -> str:
    """Returns dynamic time-of-day greeting (Good Morning / Afternoon / Evening)."""
    try:
        from django.utils.timezone import localtime
        import zoneinfo
        ist_now = localtime(datetime.now(), zoneinfo.ZoneInfo("Asia/Kolkata"))
        hour = ist_now.hour
    except Exception:
        hour = datetime.now().hour

    if 5 <= hour < 12:
        if lang == "gu":
            return "નમસ્તે, ગુડ મોર્નિંગ"
        return "Good Morning" if lang == "en" else "नमस्कार, गुड मॉर्निंग"
    elif 12 <= hour < 17:
        if lang == "gu":
            return "નમસ્તે, શુભ બપોર"
        return "Good Afternoon" if lang == "en" else "नमस्कार"
    else:
        if lang == "gu":
            return "નમસ્તે, ગુડ ઇવનિંગ"
        return "Good Evening" if lang == "en" else "नमस्कार, गुड इवनिंग"

def _format_spoken_number(phone_num: str, lang: str = "en") -> str:
    """Formats phone number digit-by-digit into clear English, Hindi or Gujarati spoken words for TTS."""
    clean_digits = "".join(filter(str.isdigit, str(phone_num)))
    if lang == "gu":
        gu_digit_words = {'0': 'ઝીરો', '1': 'એક', '2': 'બે', '3': 'ત્રણ', '4': 'ચાર', '5': 'પાંચ', '6': 'છ', '7': 'સાત', '8': 'આઠ', '9': 'નવ'}
        return " ".join(gu_digit_words.get(d, d) for d in clean_digits)
    elif lang == "hi":
        hi_digit_words = {'0': 'शून्य', '1': 'एक', '2': 'दो', '3': 'तीन', '4': 'चार', '5': 'पांच', '6': 'छह', '7': 'सात', '8': 'आठ', '9': 'नौ'}
        return " ".join(hi_digit_words.get(d, d) for d in clean_digits)
    else:
        en_digit_words = {'0': 'Zero', '1': 'One', '2': 'Two', '3': 'Three', '4': 'Four', '5': 'Five', '6': 'Six', '7': 'Seven', '8': 'Eight', '9': 'Nine'}
        return " ".join(en_digit_words.get(d, d) for d in clean_digits)

def _format_spoken_ticket(ticket_number: str, lang: str = "en") -> str:
    """
    Formats ticket number character-by-character with comma pauses for slow, clear TTS pronunciation.
    E.g. "SR S4533333" -> "S, R, S, 4, 5, 3, 3, 3, 3, 3"
    """
    if not ticket_number:
        return ""
    
    clean_str = ticket_number.replace(" ", "")
    char_map = {
        "gu": ({'0': 'ઝીરો', '1': 'એક', '2': 'બે', '3': 'ત્રણ', '4': 'ચાર', '5': 'પાંચ', '6': 'છ', '7': 'સાત', '8': 'આઠ', '9': 'નવ'}, {'S': 'એસ', 'R': 'આર'}),
        "hi": ({'0': 'शून्य', '1': 'एक', '2': 'दो', '3': 'तीन', '4': 'चार', '5': 'पांच', '6': 'छह', '7': 'सात', '8': 'आठ', '9': 'नौ'}, {'S': 'एस', 'R': 'आर'}),
        "en": ({'0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four', '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine'}, {'S': 'S', 'R': 'R'}),
    }
    digits, letters = char_map.get(lang, char_map["en"])
    parts = [digits.get(ch, letters.get(ch.upper(), ch)) for ch in clean_str]
    return ", ".join(parts)

def _generate_sr_ticket_number() -> str:
    """Generates ticket number matching script format: 'SR S' + 7 digits (e.g. 'SR S4533333')"""
    num = random.randint(1000000, 9999999)
    return f"SR S{num}"

# ── Primary Strategy Entry Points ──

def icemake_v2_strategy(agent, message, session, mode="telephony", **kwargs):
    """Entry point for non-streaming calls."""
    prep = icemake_v2_prepare(agent, message, session, mode=mode, **kwargs)
    response = prep.get("static_reply", "")
    icemake_v2_finalize(response, prep)
    return response

def icemake_v2_finalize(response, prep_result):
    """Finalizes turn state."""
    pass

def icemake_v2_prepare(agent, message, session, detected_language=None, mode="telephony", **kwargs):
    """
    Core dialogue processor for Ice Make Refrigeration Limited V2.
    Follows the 11-step script strictly with bilingual support (English & Hindi).
    """
    state = session.state or {}
    raw_message = sanitise(message)
    msg = raw_message.lower().strip()

    if "conversation_history" not in state:
        state["conversation_history"] = []

    current_step = state.get("current_step", 0)
    lang = state.get("selected_language")

    # If language is NOT yet locked, detect and lock it based on caller's choice / speech
    if not state.get("language_locked"):
        # Detect if user requested or spoke in Gujarati, Hindi, or English
        is_gu = (
            detected_language == "gu"
            or bool(re.search(r'[\u0a80-\u0aff]', raw_message))
            or any(w in msg for w in ["gujarati", "ગુજરાતી", "gujrati", "gujarathi", "gujju", "kem cho"])
            or any(w == msg.strip(".?,!") for w in ["gu", "guj"])
        )
        is_hi = (
            detected_language == "hi"
            or bool(re.search(r'[\u0900-\u097f]', raw_message))
            or any(re.search(r'\b' + re.escape(w) + r'\b', msg) for w in ["hindi", "हिंदी", "हिन्दी", "namaste", "नमस्ते", "haan", "shikayat", "madad"])
            or any(w == msg.strip(".?,!") for w in ["hi", "hin"])
        )
        is_en = (
            any(re.search(r'\b' + re.escape(w) + r'\b', msg) for w in ["english", "eng", "angrezi", "angreji"])
            or any(w in msg for w in ["speak in english", "english please", "in english"])
            or any(w == msg.strip(".?,!") for w in ["en"])
        )

        if is_gu:
            lang = "gu"
            state["selected_language"] = "gu"
            state["language_locked"] = True
        elif is_hi:
            lang = "hi"
            state["selected_language"] = "hi"
            state["language_locked"] = True
        elif is_en:
            lang = "en"
            state["selected_language"] = "en"
            state["language_locked"] = True
        elif current_step >= 1:
            # Caller spoke their first utterance (e.g. name or query) without explicitly naming the language:
            # Lock whatever language was detected or default to English
            if detected_language in ["en", "hi", "gu"]:
                lang = detected_language
            else:
                lang = lang or "en"
            state["selected_language"] = lang
            state["language_locked"] = True
        else:
            lang = lang or (detected_language if detected_language in ["en", "hi", "gu"] else "en")
            state["selected_language"] = lang
    else:
        # Language is already locked: strictly maintain the selected language for ALL subsequent turns (NO AUTO SWITCH)
        lang = state.get("selected_language", "en")

    # Pre-process spoken numbers
    raw_message = _convert_all_spoken_numbers_to_digits(raw_message, lang)
    msg = raw_message.lower().strip()

    # ── STEP 0: GREETING ──
    if current_step == 0:
        # If the introductory greeting was already played (by telephony consumer) or caller has already sent input:
        if state.get("intro_shown") or raw_message:
            current_step = 1
            state["current_step"] = 1
        else:
            time_greeting = _get_time_greeting(lang)
            if lang == "gu":
                greeting = f"{time_greeting}! આઈસ મેક રેફ્રિજરેશનમાં આપનું ખૂબ ખૂબ સ્વાગત છે. તમે કઈ ભાષામાં વાત કરવાનું પસંદ કરશો?"
            elif lang == "hi":
                greeting = f"{time_greeting}! आइस मेक रेफ्रिजरेशन में आपका बहुत-बहुत स्वागत है। आप किस भाषा में बात करना पसंद करेंगे?"
            else:
                greeting = f"{time_greeting}. Welcome to Ice Make Refrigeration Limited. Which language would you prefer to speak in?"

            state["intro_shown"] = True
            state["current_step"] = 1
            state["conversation_history"].append(f"Agent: {greeting}")
            save_session(session, state)

            return {
                "static_reply": greeting,
                "tts_language": lang,
                "skip_output_translation": True,
                "strategy_key": STRATEGY_KEY,
                "mode": mode,
                "session": session,
                "state": state,
                "language_locked": state.get("language_locked", False)
            }

    prev_step = current_step

    # ── OUT-OF-FLOW INTERCEPTION (FAQs / company questions) ──
    out_of_flow_res = _check_and_handle_out_of_flow(raw_message, lang, prev_step, session, state, mode=mode)
    if out_of_flow_res:
        return out_of_flow_res

    state["conversation_history"].append(f"User: {raw_message}")

    # ── STEP 1: Process Customer Response to Greeting ──
    if prev_step == 1:
        # In response to the opening greeting (e.g. language selection or complaint), ask for customer name
        explicit_name_match = re.search(r'\b(my\s+name\s+is|mera\s+naam\s+hai|mera\s+naam|maru\s+naam\s+che|maru\s+naam|મારું\s+નામ\s+છે|મારું\s+નામ)\s+([a-zA-Z\u0900-\u097F\u0A80-\u0AFF]+)', raw_message, re.IGNORECASE)
        is_only_lang_choice = any(w == msg.strip(".?,!") for w in ["hindi", "हिंदी", "हिन्दी", "english", "angrezi", "angreji", "gujarati", "gujrati", "ગુજરાતી"]) or (
            any(w in msg for w in ["speak in hindi", "hindi mein", "hindi me", "हिंदी में", "speak in english", "english please", "speak in gujarati", "gujarati ma", "ગુજરાતીમાં"]) and len(msg.split()) <= 4
        )

        if explicit_name_match:
            cust_name = explicit_name_match.group(2).strip().title()
            state["customer_name"] = cust_name
            state["current_step"] = 3
            if lang == "gu":
                reply = f"આભાર {cust_name} જી! કૃપા કરીને આપનું પૂરું સરનામું જણાવી દો, અને જો પિનકોડ યાદ હોય તો એ પણ સાથે જણાવી દેશો."
            elif lang == "hi":
                reply = f"धन्यवाद {cust_name} जी! कृपया अपना पूरा पता बता दीजिए, और अगर पिनकोड याद हो तो वो भी बता दीजिएगा।"
            else:
                reply = "Tell me your address with pincode if available."
        elif is_only_lang_choice:
            state["current_step"] = 2
            if lang == "gu":
                reply = "જી, આભાર! શું હું આપનું શુભ નામ જાણી શકું છું?"
            elif lang == "hi":
                reply = "जी, धन्यवाद! क्या मैं आपका शुभ नाम जान सकती हूँ?"
            else:
                reply = "Thank you! May I know your name, please?"
        else:
            state["current_step"] = 2
            if lang == "gu":
                reply = "જી, શું હું આપનું શુભ નામ જાણી શકું છું?"
            elif lang == "hi":
                reply = "जी, क्या मैं आपका शुभ नाम जान सकती हूँ?"
            else:
                reply = "May I know your name, please?"

    # ── STEP 2: Process Customer Name ──
    elif prev_step == 2:
        clean_name = _extract_person_name(raw_message, lang)
        cust_name = clean_name if clean_name and clean_name != "Not Provided" else raw_message.strip()
        state["customer_name"] = cust_name
        state["current_step"] = 3
        if lang == "gu":
            reply = f"આભાર {cust_name} જી! કૃપા કરીને આપનું પૂરું સરનામું જણાવી દો, અને જો પિનકોડ યાદ હોય તો એ પણ સાથે જણાવી દેશો."
        elif lang == "hi":
            reply = f"धन्यवाद {cust_name} जी! कृपया अपना पूरा पता बता दीजिए, और अगर पिनकोड याद हो तो वो भी बता दीजिएगा।"
        else:
            reply = "Tell me your address with pincode if available."

    # ── STEP 3: Process Address with Pincode (if available) ──
    elif prev_step == 3:
        pincode_extracted = _extract_pincode_ai(raw_message, lang)

        # Check if caller explicitly attempted to provide a pincode that is NOT 6 digits
        pin_kw = re.search(r'\b(?:pincode|pin\s*code|pin|पिनकोड|पिन|પિનકોડ|પિન)\b[^\d]*(\d+)', raw_message, re.IGNORECASE)
        if not pin_kw:
            pin_kw = re.search(r'(\d+)[^\d]*\b(?:pincode|pin\s*code|pin|पिनकोड|पिन|પિનકોડ|પિન)\b', raw_message, re.IGNORECASE)

        digits_only = "".join(filter(str.isdigit, raw_message))
        is_only_digits = digits_only and re.sub(r'[\s\d.,\-]', '', raw_message).strip() == ""

        has_invalid_pin = False
        if pin_kw:
            pin_digits = pin_kw.group(1).strip()
            if len(pin_digits) != 6:
                has_invalid_pin = True
        elif is_only_digits and len(digits_only) not in (6, 10):
            # If user just spoke 3, 4, 5, 7, 8 digits without words, treat as invalid pincode attempt
            has_invalid_pin = True

        if has_invalid_pin and not (pincode_extracted and len(pincode_extracted) == 6):
            if lang == "gu":
                reply = "માફ કરશો, પિનકોડ 6 અંકનો હોય છે. શું તમે 6 અંકના સાચા પિનકોડ સાથે તમારું સરનામું ફરીથી જણાવી શકો છો?"
            elif lang == "hi":
                reply = "माफ़ कीजिएगा, पिनकोड 6 अंकों का होता है। क्या आप 6 अंकों के सही पिनकोड के साथ अपना पता एक बार फिर बता सकते हैं?"
            else:
                reply = "Postal pincode must be exactly 6 digits. Kindly tell me your address with your 6-digit pincode if available."
            state["current_step"] = 3
            state["conversation_history"].append(f"Agent: {reply}")
            save_session(session, state)
            return {
                "static_reply": reply,
                "tts_language": lang,
                "skip_output_translation": True,
                "strategy_key": STRATEGY_KEY,
                "mode": mode,
                "session": session,
                "state": state,
                "language_locked": state.get("language_locked", False)
            }

        # Store pincode and enrich location if valid 6-digit pincode was given
        if pincode_extracted and len(pincode_extracted) == 6:
            state["pin_code"] = pincode_extracted
            lookup_res = lookup_pincode(pincode_extracted)
            formatted_address = lookup_res.get("formatted", "")
            if formatted_address:
                state["pincode_address"] = formatted_address
                state["city_state"] = f"{lookup_res.get('district', '')}, {lookup_res.get('state', '')}".strip(", ")
                state["state_name"] = lookup_res.get("state", "")
                state["city_name"] = lookup_res.get("district", "")
        else:
            state["pin_code"] = "Not Provided"
            state["city_state"] = raw_message.strip()

        state["full_address"] = raw_message.strip()
        state["company_name"] = raw_message.strip()

        # Step 3 completed: Ask for caller's State in the next turn
        state["current_step"] = 4
        if lang == "gu":
            reply = "જી આભાર! કૃપા કરીને આપના રાજ્યનું નામ જણાવી દો."
        elif lang == "hi":
            reply = "जी धन्यवाद! कृपया अपने राज्य का नाम बता दीजिए।"
        else:
            reply = "Could you please tell me which state you are calling from?"

    # ── STEP 4: Process State ──
    elif prev_step == 4:
        clean_state = _clean_state_name(raw_message)
        state["state_name"] = clean_state
        if state.get("city_state") and clean_state.lower() not in state["city_state"].lower():
            state["city_state"] = f"{state['city_state']}, {clean_state}".strip(", ")
        elif not state.get("city_state"):
            state["city_state"] = clean_state

        cust_name = state.get("customer_name", "")
        name_en = f", {cust_name}" if (cust_name and cust_name.lower() not in ["customer", "not provided", "none"]) else ""
        name_hi = f" {cust_name} जी" if (cust_name and cust_name.lower() not in ["customer", "not provided", "none"]) else ""
        name_gu = f" {cust_name} જી" if (cust_name and cust_name.lower() not in ["customer", "not provided", "none"]) else ""
        state["current_step"] = 7
        if lang == "gu":
            reply = f"ખૂબ ખૂબ આભાર{name_gu}! હવે કૃપા કરીને આપના મશીનનો સિરીયલ નંબર જણાવી દો."
        elif lang == "hi":
            reply = f"बहुत-बहुत धन्यवाद{name_hi}! अब कृपया अपनी मशीन का सीरियल नंबर बता दीजिए।"
        else:
            reply = f"Thank you{name_en}. Kindly provide the machine serial number."

    # Legacy step fallback (if any session was suspended on step 5 or 6)
    elif prev_step in [5, 6]:
        cust_name = state.get("customer_name", "")
        name_en = f", {cust_name}" if (cust_name and cust_name.lower() not in ["customer", "not provided", "none"]) else ""
        name_hi = f" {cust_name} जी" if (cust_name and cust_name.lower() not in ["customer", "not provided", "none"]) else ""
        name_gu = f" {cust_name} જી" if (cust_name and cust_name.lower() not in ["customer", "not provided", "none"]) else ""
        state["current_step"] = 7
        if lang == "gu":
            reply = f"ખૂબ ખૂબ આભાર{name_gu}! હવે કૃપા કરીને આપના મશીનનો સિરીયલ નંબર જણાવી દો."
        elif lang == "hi":
            reply = f"बहुत-बहुत धन्यवाद{name_hi}! अब कृपया अपनी मशीन का सीरियल नंबर बता दीजिए।"
        else:
            reply = f"Thank you{name_en}. Kindly provide the machine serial number."

    # ── STEP 7: Machine Serial Number ──
    elif prev_step == 7:
        has_no_serial = any(w in msg for w in [
            "don't have", "dont have", "not available", "no serial", "pata nahi", "maloom nahi",
            "nahi hai", "nhi hai", "invoice nahi hai", "baad me", "later", "nahi pata", "no",
            "નથી", "ખબર નથી", "નથી ખબર", "નથી મળતો", "બિલ નથી", "પછી આપીશ", "ના", "નથી યાદ"
        ])
        
        if has_no_serial:
            # Caller does not have serial number -> Gracefully guide and proceed to mobile number
            state["machine_sr_no"] = "Not Provided"
            state["current_step"] = 9
            if lang == "gu":
                reply = "અરે કોઈ વાંધો નહીં જી! સિરીયલ નંબર સામાન્ય રીતે મશીન પર અથવા તેના બિલ પર લખેલો હોય છે. પણ ચિંતા કરવાની કોઈ જરૂર નથી, અમે તેના વગર જ ફરિયાદ નોંધી લઈએ છીએ. આપ કૃપા કરીને આપનો 10 અંકનો મોબાઈલ નંબર જણાવી દો."
            elif lang == "hi":
                reply = "अरे कोई बात नहीं जी! सीरियल नंबर वैसे मशीन पर या उसके बिल पर लिखा होता है। पर कोई चिंता की बात नहीं, हम इसके बिना ही शिकायत दर्ज कर लेते हैं। आप कृपया अपना मोबाइल नंबर बता दीजिए।"
            else:
                reply = "To assist you further, you can find the serial number on the product or purchase invoice later. No problem at all, we will proceed for now. Kindly provide your mobile number."
        else:
            # Extract serial number string
            clean_sr = _clean_serial_number(raw_message)
            state["temp_serial_no"] = clean_sr
            state["current_step"] = 8
            
            if lang == "gu":
                reply = f"તમે સિરીયલ નંબર {clean_sr} જણાવ્યો છે. શું આ બિલકુલ સાચો છે?"
            elif lang == "hi":
                reply = f"आपने सीरियल नंबर {clean_sr} बताया है। क्या यह बिल्कुल सही है?"
            else:
                reply = f"You said {clean_sr}. Please say 'Yes' to proceed, or 'No' to re-enter the serial number."

    # ── STEP 8: Serial Number Confirmation ──
    elif prev_step == 8:
        is_yes = any(w in msg for w in [
            "yes", "yeah", "yep", "correct", "right", "ok", "haan", "sahi", "ha", "हाँ", "सही", "ठीक", "okay", "बिल्कुल", "हा", "हॉ", "जी",
            "હા", "હાજી", "સાચો", "સાચું", "બરાબર", "ઠીક છે", "બરાબર છે"
        ])
        is_no = any(w in msg for w in [
            "no", "nope", "incorrect", "wrong", "nahi", "na", "गलत", "नहीं", "ना",
            "ના", "નહીં", "ખોટો", "ખોટું"
        ])

        if is_yes or not is_no:
            state["machine_sr_no"] = state.get("temp_serial_no", "Not Provided")
            state["current_step"] = 9
            if lang == "gu":
                reply = "જી, કૃપા કરીને આપનો 10 અંકનો મોબાઈલ નંબર જણાવી દો."
            elif lang == "hi":
                reply = "जी, कृपया अपना 10 अंकों का मोबाइल नंबर बता दीजिए।"
            else:
                reply = "Kindly provide your mobile number."
        else:
            # Caller said "No" -> Re-enter serial number
            state["current_step"] = 7
            if lang == "gu":
                reply = "કોઈ વાંધો નહીં, કૃપા કરીને સાચો સિરીયલ નંબર ફરીથી જણાવી દો."
            elif lang == "hi":
                reply = "कोई बात नहीं, कृपया सही सीरियल नंबर एक बार फिर से बता दीजिए।"
            else:
                reply = "Kindly provide the machine serial number once again."

    # ── STEP 9: Mobile Number (10 Digits Validation) ──
    elif prev_step == 9:
        accumulated = state.get("partial_phone_digits", "")
        extracted_digits = _extract_phone_number_ai(raw_message, lang)
        raw_digits = "".join(filter(str.isdigit, raw_message))

        new_digits = extracted_digits if len(extracted_digits) > 0 else raw_digits
        combined_digits = (accumulated + new_digits).strip()

        valid_phone = ""
        # 1. Did the caller provide all 10 digits in this current utterance? (e.g. caller restarted from beginning)
        if len(raw_digits) == 10:
            valid_phone = raw_digits
        elif len(raw_digits) in (11, 12) and raw_digits.startswith("91"):
            valid_phone = raw_digits[-10:]
        elif len(extracted_digits) == 10:
            valid_phone = extracted_digits
        # 2. Or did the accumulated digits + new digits complete 10 digits?
        elif len(combined_digits) == 10:
            valid_phone = combined_digits
        elif len(combined_digits) in (11, 12) and combined_digits.startswith("91"):
            valid_phone = combined_digits[-10:]

        if not valid_phone:
            # If the user spoke partial digits (< 10), wait silently without cutting off or interrupting
            if 0 < len(combined_digits) < 10:
                state["partial_phone_digits"] = combined_digits
                state["current_step"] = 9
                save_session(session, state)
                return {
                    "static_reply": "",
                    "tts_language": lang,
                    "skip_output_translation": True,
                    "strategy_key": STRATEGY_KEY,
                    "mode": mode,
                    "session": session,
                    "state": state,
                    "language_locked": state.get("language_locked", False)
                }
            elif 0 < len(new_digits) < 10:
                # If combined was distorted by old partial, reset to the new partial digits
                state["partial_phone_digits"] = new_digits
                state["current_step"] = 9
                save_session(session, state)
                return {
                    "static_reply": "",
                    "tts_language": lang,
                    "skip_output_translation": True,
                    "strategy_key": STRATEGY_KEY,
                    "mode": mode,
                    "session": session,
                    "state": state,
                    "language_locked": state.get("language_locked", False)
                }
            
            if lang == "gu":
                reply = "માફ કરશો, આ નંબર સાચો લાગતો નથી. કૃપા કરીને આપનો 10 અંકનો સાચો મોબાઈલ નંબર જણાવો."
            elif lang == "hi":
                reply = "माफ़ कीजिएगा, यह नंबर सही नहीं लग रहा है। कृपया अपना 10 अंकों का सही मोबाइल नंबर बताइए।"
            else:
                reply = "Your mobile number seems invalid. Kindly provide your 10-digit mobile number."
            state["current_step"] = 9
            state["conversation_history"].append(f"Agent: {reply}")
            save_session(session, state)
            return {
                "static_reply": reply,
                "tts_language": lang,
                "skip_output_translation": True,
                "strategy_key": STRATEGY_KEY,
                "mode": mode,
                "session": session,
                "state": state,
                "language_locked": state.get("language_locked", False)
            }
        else:
            phone_num = valid_phone
            state["registered_mobile"] = phone_num
            state.pop("partial_phone_digits", None)
            state["current_step"] = 10
            
            spoken_num = _format_spoken_number(phone_num, lang)
            if lang == "gu":
                reply = f"આપનો નંબર છે — {spoken_num}। શું મેં નંબર બિલકુલ સાચો નોંધ્યો છે?"
            elif lang == "hi":
                reply = f"आपका नंबर है — {spoken_num}। क्या मैंने नंबर बिल्कुल सही नोट किया है?"
            else:
                reply = f"You said your mobile number is {spoken_num}. If this is correct, please say 'Yes' or 'OK.' If it is incorrect, please say 'No.'"

    # ── STEP 10: Number Confirmation ──
    elif prev_step == 10:
        is_yes = any(w in msg for w in [
            "yes", "yeah", "yep", "correct", "right", "ok", "haan", "sahi", "ha", "हाँ", "सही", "ठीक", "okay", "बिल्कुल", "हा", "हॉ", "जी",
            "હા", "હાજી", "સાચો", "સાચું", "બરાબર", "ઠીક છે", "બરાબર છે"
        ])
        is_no = any(w in msg for w in [
            "no", "nope", "incorrect", "wrong", "nahi", "na", "गलत", "नहीं", "ना",
            "ના", "નહીં", "ખોટો", "ખોટું"
        ])

        if is_yes or not is_no:
            # Proceed to Step 10 in Script: Complaint Recording
            state["current_step"] = 11
            if lang == "gu":
                reply = "આભાર! હવે કૃપા કરીને આપના ફ્રીઝર અથવા મશીનમાં આવી રહેલી સમસ્યા વિશે જણાવો. આપ શાંતિથી પૂરી વાત જણાવી શકો છો, આપનો સંદેશ સીધો અમારા સર્વિસ એન્જિનિયર સુધી પહોંચાડવામાં આવશે. જણાવો, શું તકલીફ આવી રહી છે?"
            elif lang == "hi":
                reply = "धन्यवाद! अब कृपया अपने फ्रीज़र या मशीन में आ रही समस्या के बारे में बताइए। आप आराम से पूरी बात बता सकते हैं, आपका संदेश सीधे हमारे सर्विस इंजीनियर तक पहुँचा जाएगा। बताइए, क्या परेशानी आ रही है?"
            else:
                reply = "Thank you. Kindly describe the issue with your Freezer. You may speak for up to 2 minutes. Your message will be recorded and forwarded to our Service Engineer for immediate action. Please begin after the beep."
        else:
            # If Customer says "No"
            state["current_step"] = 9
            if lang == "gu":
                reply = "માફ કરશો! કૃપા કરીને આપનો સાચો મોબાઈલ નંબર ફરીથી જણાવી દો."
            elif lang == "hi":
                reply = "माफ़ कीजिएगा! कृपया अपना सही मोबाइल नंबर एक बार फिर से बता दीजिए।"
            else:
                reply = "I apologize. Kindly repeat your mobile number once again."

    # ── STEP 11: Complaint Recording & Ticket Registration ──
    elif prev_step == 11:
        state["issue_description"] = raw_message.strip()
        state["current_step"] = 12

        # Generate ticket format: "SR S" + 7 digits
        ticket_number = _generate_sr_ticket_number()
        state["ticket_number"] = ticket_number
        
        # Save ticket in database
        from conversations.models import Conversation
        conversation = Conversation.objects.filter(session_id=session.session_id).first()
        if conversation:
            _create_v2_ticket_db_record(conversation, state)
        else:
            logger.warning("Conversation record not found for session_id: %s", session.session_id)

        cust_name = state.get("customer_name", "")
        name_en = f", {cust_name}" if (cust_name and cust_name.lower() not in ["customer", "not provided", "none"]) else ""
        name_hi = f" {cust_name} जी" if (cust_name and cust_name.lower() not in ["customer", "not provided", "none"]) else ""
        name_gu = f" {cust_name} જી" if (cust_name and cust_name.lower() not in ["customer", "not provided", "none"]) else ""
        spoken_ticket = _format_spoken_ticket(ticket_number, lang)

        if lang == "gu":
            reply = (
                f"ખૂબ ખૂબ આભાર{name_gu}! આપની ફરિયાદ નોંધાઈ ગઈ છે. "
                f"કૃપા કરીને આપનો ફરિયાદ નંબર નોંધી લેશો — {ticket_number}, એટલે કે {spoken_ticket}। "
                f"અમારા સર્વિસ એન્જિનિયર ટૂંક સમયમાં જ આપનો સંપર્ક કરશે. આઈસ મેકમાં કોલ કરવા બદલ આભાર, આપનો દિવસ શુભ રહે! [FLOW_COMPLETE]"
            )
        elif lang == "hi":
            reply = (
                f"बहुत-बहुत धन्यवाद{name_hi}! आपकी शिकायत दर्ज कर ली गई है। "
                f"कृपया अपना कंप्लेंट नंबर नोट कर लीजिए — {ticket_number}, यानी {spoken_ticket}। "
                f"हमारे सर्विस इंजीनियर जल्द ही आपसे संपर्क करेंगे। आइस मेक में कॉल करने के लिए धन्यवाद, आपका दिन बहुत शुभ हो! [FLOW_COMPLETE]"
            )
        else:
            reply = (
                f"Thank you{name_en}. Your complaint has been successfully registered with Ice Make Refrigeration Limited. "
                f"Please note your complaint number {ticket_number} for future reference. "
                f"Our service team will contact you shortly. Thank you for choosing Ice Make. Have a wonderful day. [FLOW_COMPLETE]"
            )

        state["conversation_history"].append(f"Agent: {reply}")
        save_session(session, state)

        return {
            "static_reply": reply,
            "tts_language": lang,
            "skip_output_translation": True,
            "strategy_key": STRATEGY_KEY,
            "mode": mode,
            "session": session,
            "state": state,
            "auto_disconnect": True,
            "skip_name_collection": True,
            "language_locked": state.get("language_locked", False)
        }

    state["conversation_history"].append(f"Agent: {reply}")
    save_session(session, state)

    return {
        "static_reply": reply,
        "tts_language": lang,
        "skip_output_translation": True,
        "strategy_key": STRATEGY_KEY,
        "mode": mode,
        "session": session,
        "state": state,
        "language_locked": state.get("language_locked", False)
    }

# ── Helpers for Entity Extraction, DB Logging & Notifications ──

def _clean_serial_number(text: str) -> str:
    """Cleans machine serial number input."""
    clean = text.strip()
    clean = re.sub(r'^(machine|serial|model|sr|no|number|serial\s+number|सीरियल\s+नंबर|मशीन|મશીન|સિરીયલ\s+નંબર|મશીનનો\s+નંબર|સિરીયલ)\s+', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'[.,!?\s]', '', clean).upper()
    return clean if clean else text.strip()

def _clean_state_name(text: str) -> str:
    """Cleans and extracts Indian state name from spoken text."""
    if not text:
        return ""
    clean = text.strip()
    clean = re.sub(r'^(i\s+am\s+from|from|state\s+is|state|main|hum|mera\s+state|mein|se|હું|મારું\s+રાજ્ય|માંથી|થી)\s+', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'\s+(se\s+bol\s+raha\s+hu|se\s+hai|se|state|માંથી|થી|છે|રાજ્ય)$', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'[.,!?]', '', clean).strip()
    return clean.title() if clean else text.strip().title()

def _create_v2_ticket_db_record(conversation, state):
    """Logs ticket in IcemakeTicket DB model."""
    try:
        from icemake_bot.models import IcemakeTicket
        
        extracted = _extract_clean_ticket_entities(state)
        logger.info("AI Extracted Ticket Data (V2): %s", extracted)

        city_state_str = state.get("city_state", "") or f"{extracted.get('city', '')}, {extracted.get('state', '')}".strip(", ")
        
        ticket, _ = IcemakeTicket.objects.update_or_create(
            conversation=conversation,
            defaults={
                "ticket_number": state.get("ticket_number"),
                "language": state.get("selected_language", "en"),
                "registered_mobile": state.get("registered_mobile", ""),
                "customer_name": extracted.get("customer_name", state.get("customer_name", "")),
                "company_name": state.get("full_address", state.get("company_name", "")),
                "city_state": city_state_str,
                "pin_code": state.get("pin_code", ""),
                "machine_model_no": extracted.get("machine_model_no", "Freezer"),
                "machine_sr_no": state.get("machine_sr_no", "Not Provided"),
                "issue_type": extracted.get("issue_type", "No Cooling / Insufficient Cooling"),
                "issue_description": extracted.get("type_of_complaint", state.get("issue_description", "")),
            }
        )
        print(f"🎫 [ICEMAKE V2] TICKET LOGGED SUCCESSFULLY: {state.get('ticket_number')}")
    except Exception as e:
        logger.error(f"[ICEMAKE V2] Failed to create IcemakeTicket: {e}")

def _extract_clean_ticket_entities(state: dict) -> dict:
    """Uses Azure OpenAI to normalize complaint and fault category."""
    import json
    from conversations.services.azure_openai_service import client
    from django.conf import settings

    raw_name = state.get("customer_name", "")
    raw_state = state.get("state_name", "")
    raw_city = state.get("city_name", "")
    raw_address = state.get("full_address", "")
    raw_issue = state.get("issue_description", "")

    prompt = f"""
Analyze the refrigeration breakdown complaint for Ice Make Refrigeration Ltd.
Raw Inputs:
- Customer Name: "{raw_name}"
- State: "{raw_state}"
- City: "{raw_city}"
- Full Address: "{raw_address}"
- Issue Description: "{raw_issue}"

Rules:
1. "customer_name": Person name in Title Case English (e.g., "Ram").
2. "state": Indian state in English (e.g., "Gujarat", "Andhra Pradesh").
3. "city": City/District name in Title Case (e.g., "Ahmedabad", "Cuddapah").
4. "machine_model_no": Product name (e.g. "Freezer", "Chiller", "Blast Freezer").
5. "issue_type": EXACTLY ONE of: "No Cooling / Insufficient Cooling", "Abnormal Noise & Vibration", "Gas Leakage / Low Pressure", "Electrical / Tripping Fault", "Water Leakage / Defrost Fault", "Temperature Sensor Error", "General Maintenance / Service".
6. "type_of_complaint": One professional English sentence describing the problem.

Return JSON: {{"customer_name": "...", "state": "...", "city": "...", "machine_model_no": "...", "issue_type": "...", "type_of_complaint": "..."}}
"""
    try:
        response = client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are an expert CRM refrigeration entity extraction assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"V2 Entity extraction error: {e}")
        return {
            "customer_name": raw_name,
            "state": raw_state,
            "city": raw_city,
            "machine_model_no": "Freezer",
            "issue_type": "No Cooling / Insufficient Cooling",
            "type_of_complaint": raw_issue
        }

def _extract_person_name(raw_message: str, lang: str = "en") -> str:
    """Cleans person name removing conversational fillers."""
    if not raw_message or not raw_message.strip():
        return "Not Provided"
    
    clean = raw_message.strip()
    clean = re.sub(r'^(my\s+name\s+is|i\s+am|iam|this\s+is|name\s+is|मेरा\s+नाम|नाम|मैं|મારું\s+નામ\s+છે|મારું\s+નામ|નામ|હું)\s+', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'\s+(is\s+my\s+name|speaking|here|है|हूं|છે|બોલું\s+છું)$', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'[।!?,.\-]', '', clean).strip()

    words = clean.split()
    excluded = ["complaint", "issue", "problem", "freezer", "chiller", "hindi", "हिंदी", "हिन्दी", "english", "अंग्रेज़ी", "अंग्रेजी", "gujarati", "ગુજરાતી", "gujrati", "ફરિયાદ", "તકલીફ", "સમસ્યા"]
    if 1 <= len(words) <= 3 and len(clean) <= 30 and not any(w in clean.lower() for w in excluded):
        return clean.title()

    try:
        from conversations.services.azure_openai_service import client
        from django.conf import settings

        prompt = f"""Extract ONLY the caller's actual person name from this user utterance.
User Utterance: "{raw_message}"
Name:"""
        res = client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "Extract person name only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=15
        )
        ai_name = res.choices[0].message.content.strip().strip('"').strip("'")
        if ai_name and ai_name.lower() not in ["not provided", "none", "unknown"]:
            return ai_name
    except Exception:
        pass

    return clean if clean else "Not Provided"

def _extract_pincode_ai(raw_message: str, lang: str = "en") -> str:
    """Extracts 6 ASCII digits for Indian pincode."""
    if not raw_message:
        return ""
    
    mapped = _map_regional_digits_to_ascii(raw_message)
    m = re.search(r'\b\d{6}\b', mapped)
    if m:
        return m.group(0)

    try:
        from conversations.services.azure_openai_service import client
        from django.conf import settings
        prompt = f"""Extract spoken 6-digit Indian postal pincode into EXACTLY 6 ASCII digits.
Input: "{raw_message}"
6-Digit Pincode:"""
        res = client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=10
        )
        digits = "".join(filter(str.isdigit, res.choices[0].message.content))
        if len(digits) == 6:
            return digits
    except Exception:
        pass

    return ""

def _extract_phone_number_ai(raw_message: str, lang: str = "en") -> str:
    """Extracts 10-digit Indian phone number."""
    if not raw_message:
        return ""
    
    mapped = _map_regional_digits_to_ascii(raw_message)
    digits = "".join(filter(str.isdigit, mapped))
    if len(digits) == 10:
        return digits

    try:
        from conversations.services.azure_openai_service import client
        from django.conf import settings
        prompt = f"""Extract spoken 10-digit Indian phone number into EXACTLY 10 ASCII digits.
Input: "{raw_message}"
10-Digit Number:"""
        res = client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=15
        )
        ai_digits = "".join(filter(str.isdigit, res.choices[0].message.content))
        if len(ai_digits) == 10:
            return ai_digits
    except Exception:
        pass

    return digits

def _map_regional_digits_to_ascii(text: str) -> str:
    regional_digit_map = {
        '०': '0', '१': '1', '२': '2', '३': '3', '४': '4', '५': '5', '६': '6', '७': '7', '८': '8', '९': '9',
        '૦': '0', '૧': '1', '૨': '2', '૩': '3', '૪': '4', '૫': '5', '૬': '6', '૭': '7', '૮': '8', '૯': '9',
    }
    return "".join(regional_digit_map.get(ch, ch) for ch in text)

def _convert_all_spoken_numbers_to_digits(text: str, lang: str = "en") -> str:
    if not text:
        return ""
    text = _map_regional_digits_to_ascii(text)
    num_map = {
        "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
        "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
        "ten": "10", "शून्य": "0", "एक": "1", "दो": "2", "तीन": "3", "चार": "4",
        "पांच": "5", "पाँच": "5", "छह": "6", "सात": "7", "आठ": "8", "नौ": "9", "दस": "10",
        "ઝીરો": "0", "મીંડું": "0", "એક": "1", "બે": "2", "ત્રણ": "3", "ચાર": "4",
        "પાંચ": "5", "છ": "6", "સાત": "7", "આઠ": "8", "નવ": "9", "દસ": "10"
    }
    sorted_words = sorted(num_map.keys(), key=lambda x: len(x), reverse=True)
    result = text
    for w in sorted_words:
        pattern = r'(^|\s)' + re.escape(w) + r'(?=\s|[.,!?।]|$)'
        result = re.sub(pattern, r'\g<1>' + num_map[w], result, flags=re.IGNORECASE)
    return result

def _check_and_handle_out_of_flow(raw_message: str, lang: str, current_step: int, session, state: dict, mode: str = "telephony"):
    """Handles FAQs and general questions without losing flow context."""
    if not raw_message or len(raw_message.strip()) < 3 or current_step in (0, 11, 12):
        return None

    # Steps 3 & 4 are actively collecting customer location/address & state.
    # Never treat an address, city, or state name as an out-of-flow query.
    if current_step in (3, 4):
        has_explicit_company_question = bool(re.search(
            r'\b(?:where\s+is\s+(?:your|the)\s+(?:office|factory|plant|company)|aapka\s+office|aapki\s+factory|company\s+kahan|tamari\s+office|tamari\s+factory)\b',
            raw_message, re.IGNORECASE
        ))
        if not has_explicit_company_question:
            return None

    digits = _extract_phone_number_ai(raw_message, lang)
    if len(digits) == 10:
        return None

    # Handle polite repeats
    repeat_patterns = [
        r'\b(?:can\s+you\s+)?repeat\b',
        r'\bpardon\b',
        r'\b(?:fir\s+se|dobara|ek\s+baar\s+fir|wapas)\s+(?:boli(?:ye)?|bata(?:iye)?|kaho)\b',
        r'\b(?:फिर\s+से|दोबारा)\b',
        r'\b(?:ફરીથી|ફરી\s+બોલો|ફરી\s+કહો|પાછું\s+બોલો|એક\s+વાર\s+ફરી)\b'
    ]
    if any(re.search(pat, raw_message, re.IGNORECASE) for pat in repeat_patterns):
        cust_name = state.get("customer_name", "")
        name_en = f", {cust_name}" if (cust_name and cust_name.lower() not in ["customer", "not provided", "none"]) else ""
        name_hi = f" {cust_name} जी" if (cust_name and cust_name.lower() not in ["customer", "not provided", "none"]) else ""
        name_gu = f" {cust_name} જી" if (cust_name and cust_name.lower() not in ["customer", "not provided", "none"]) else ""
        if current_step == 2:
            if lang == "gu":
                reply = "જી, શું હું આપનું શુભ નામ જાણી શકું છું?"
            elif lang == "hi":
                reply = "जी, क्या मैं आपका शुभ नाम जान सकती हूँ?"
            else:
                reply = "May I know your name, please?"
        elif current_step == 3:
            if lang == "gu":
                reply = f"આભાર{name_gu}! કૃપા કરીને આપનું પૂરું સરનામું જણાવી દો, અને જો પિનકોડ યાદ હોય તો એ પણ સાથે જણાવી દેશો."
            elif lang == "hi":
                reply = f"धन्यवाद{name_hi}! कृपया अपना पूरा पता बता दीजिए, और अगर पिनकोड याद हो तो वो भी साथ में बता दीजिएगा।"
            else:
                reply = "Tell me your address with pincode if available."
        elif current_step == 4:
            if lang == "gu":
                reply = "જી આભાર! કૃપા કરીને આપના રાજ્યનું નામ જણાવી દો."
            elif lang == "hi":
                reply = "जी धन्यवाद! कृपया अपने राज्य का नाम बता दीजिए।"
            else:
                reply = "Could you please tell me which state you are calling from?"
        elif current_step == 7:
            if lang == "gu":
                reply = f"ખૂબ ખૂબ આભાર{name_gu}! હવે કૃપા કરીને આપના મશીનનો સિરીયલ નંબર જણાવી દો."
            elif lang == "hi":
                reply = f"बहुत-बहुत धन्यवाद{name_hi}! अब कृपया अपनी मशीन का सीरियल नंबर बता दीजिए।"
            else:
                reply = f"Thank you{name_en}. Kindly provide the machine serial number."
        elif current_step == 8:
            clean_sr = state.get("temp_serial_no", "")
            if lang == "gu":
                reply = f"તમે સિરીયલ નંબર {clean_sr} જણાવ્યો છે. શું આ બિલકુલ સાચો છે?"
            elif lang == "hi":
                reply = f"आपने सीरियल नंबर {clean_sr} बताया है। क्या यह बिल्कुल सही है?"
            else:
                reply = f"You said {clean_sr}. Please say 'Yes' to proceed, or 'No' to re-enter the serial number."
        elif current_step == 9:
            if lang == "gu":
                reply = "જી, કૃપા કરીને આપનો 10 અંકનો મોબાઈલ નંબર જણાવી દો."
            elif lang == "hi":
                reply = "जी, कृपया अपना 10 अंकों का मोबाइल नंबर बता दीजिए।"
            else:
                reply = "Kindly provide your mobile number."
        elif current_step == 10:
            phone_num = state.get("registered_mobile", "")
            spoken_num = _format_spoken_number(phone_num, lang)
            if lang == "gu":
                reply = f"આપનો નંબર છે — {spoken_num}। શું મેં નંબર બિલકુલ સાચો નોંધ્યો છે?"
            elif lang == "hi":
                reply = f"आपका नंबर है — {spoken_num}। क्या मैंने नंबर बिल्कुल सही नोट किया है?"
            else:
                reply = f"You said your mobile number is {spoken_num}. If this is correct, please say 'Yes' or 'OK.' If it is incorrect, please say 'No.'"
        elif current_step == 11:
            if lang == "gu":
                reply = "આભાર! હવે કૃપા કરીને આપના ફ્રીઝર અથવા મશીનમાં આવી રહેલી સમસ્યા વિશે જણાવો. આપ શાંતિથી પૂરી વાત જણાવી શકો છો, આપનો સંદેશ સીધો અમારા સર્વિસ એન્જિનિયર સુધી પહોંચાડવામાં આવશે. જણાવો, શું તકલીફ આવી રહી છે?"
            elif lang == "hi":
                reply = "धन्यवाद! अब कृपया अपने फ्रीज़र या मशीन में आ रही समस्या के बारे में बताइए। आप आराम से पूरी बात बता सकते हैं, आपका संदेश सीधे हमारे सर्विस इंजीनियर तक पहुँचा दिया जाएगा। बताइए, क्या परेशानी आ रही है?"
            else:
                reply = "Thank you. Kindly describe the issue with your Freezer. You may speak for up to 2 minutes. Your message will be recorded and forwarded to our Service Engineer for immediate action. Please begin after the beep."
        else:
            return None

        state["conversation_history"].append(f"Agent: {reply}")
        save_session(session, state)
        return {
            "static_reply": reply,
            "tts_language": lang,
            "skip_output_translation": True,
            "strategy_key": STRATEGY_KEY,
            "mode": mode,
            "session": session,
            "state": state,
            "language_locked": state.get("language_locked", False)
        }

    company_query_patterns = [
        r'\b(?:where\s+is|where\s+are)\b.*\b(?:your|ice\s*make|office|factory|plant|company)\b',
        r'\b(?:aapka|aapki|tumhara|company\s+ka|tamari)\b.*\b(?:office|factory|plant|kahan|kaha|kidhar|kyan)\b',
        r'\b(?:head\s+office|factory|plant)\s+(?:kahan|kaha|kidhar|kyan)\b',
        r'\b(?:what\s+is\s+the|kya\s+hai|su\s+che)\b.*\b(?:warranty|guarantee|price|cost)\b',
    ]
    if not any(re.search(pat, raw_message, re.IGNORECASE) for pat in company_query_patterns):
        return None

    try:
        from conversations.services.azure_openai_service import client
        from django.conf import settings

        prompt = f"""You are the female AI Voice Customer Service Assistant for Ice Make Refrigeration Ltd.
The caller asked a question: "{raw_message}".
Ice Make Info: Head office & factory at Dantali, Gandhinagar - Ahmedabad Highway, Gujarat. Manufactures Cold Storage, Blast Freezers, Chillers.
Instructions:
1. Always maintain a warm, polite, courteous female customer care persona. In Gujarati or Hindi, strictly use feminine verb forms and self-references.
2. In Gujarati or Hindi, speak in very warm, natural, human conversational tone (જેમ કે એક સાચી કસ્ટમર કેર એક્ઝિક્યુટિવ આદરપૂર્વક વાત કરે છે).
3. Answer their question concisely and politely in language '{lang}'.
4. Then smoothly transition back to asking them for their complaint detail.
Response:"""
        res = client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=60
        )
        reply = res.choices[0].message.content.strip().strip('"')
        if reply:
            state["conversation_history"].append(f"User: {raw_message}")
            state["conversation_history"].append(f"Agent: {reply}")
            save_session(session, state)
            return {
                "static_reply": reply,
                "tts_language": lang,
                "skip_output_translation": True,
                "strategy_key": STRATEGY_KEY,
                "mode": mode,
                "session": session,
                "state": state,
                "language_locked": state.get("language_locked", False)
            }
    except Exception:
        pass

    return None
