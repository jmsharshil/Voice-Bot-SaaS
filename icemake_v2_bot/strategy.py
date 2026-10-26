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
        return "Good Morning" if lang == "en" else "शुभ प्रभात"
    elif 12 <= hour < 17:
        return "Good Afternoon" if lang == "en" else "नमस्कार"
    else:
        return "Good Evening" if lang == "en" else "शुभ संध्या"

def _format_spoken_number(phone_num: str, lang: str = "en") -> str:
    """Formats phone number digit-by-digit into clear English or Hindi spoken words for TTS."""
    clean_digits = "".join(filter(str.isdigit, str(phone_num)))
    if lang == "hi":
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
    lang = state.get("selected_language", "en")

    # Detect language if user switches or communicates in Hindi
    if detected_language == "hi" or re.search(r'[\u0900-\u097f]', raw_message) or any(w in msg for w in ["hindi", "हिंदी", "हिन्दी", "नमस्ते", "हाँ", "हा", "ना", "नहीं", "नाम", "शिकायत"]):
        lang = "hi"
        state["selected_language"] = "hi"

    # Pre-process spoken numbers
    raw_message = _convert_all_spoken_numbers_to_digits(raw_message, lang)
    msg = raw_message.lower().strip()

    # ── STEP 0: GREETING ──
    if current_step == 0:
        time_greeting = _get_time_greeting(lang)
        if lang == "hi":
            greeting = f"{time_greeting}। आइस मेक रेफ्रिजरेशन लिमिटेड में आपका स्वागत है। कृपया बताइए आज मैं आपकी क्या सहायता कर सकती हूँ?"
        else:
            greeting = f"{time_greeting}. Welcome to Ice Make Refrigeration Limited. Please let me know how I can help you today."

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
            "state": state
        }

    prev_step = current_step

    # ── OUT-OF-FLOW INTERCEPTION (FAQs / company questions) ──
    out_of_flow_res = _check_and_handle_out_of_flow(raw_message, lang, prev_step, session, state, mode=mode)
    if out_of_flow_res:
        return out_of_flow_res

    state["conversation_history"].append(f"User: {raw_message}")

    # ── STEP 1: Process Customer Response to Greeting ──
    if prev_step == 1:
        # In response to the opening greeting (e.g. "I have a complaint"), ask for customer name
        explicit_name_match = re.search(r'\b(my\s+name\s+is|mera\s+naam\s+hai|mera\s+naam)\s+([a-zA-Z\u0900-\u097F]+)', raw_message, re.IGNORECASE)
        if explicit_name_match:
            state["customer_name"] = explicit_name_match.group(2).strip().title()
            state["current_step"] = 3
            reply = "Please provide your postal pincode." if lang == "en" else "कृपया अपना पोस्टल पिनकोड बताइए।"
        else:
            state["current_step"] = 2
            reply = "May I know your name, please?" if lang == "en" else "क्या मैं आपका नाम जान सकती हूँ?"

    # ── STEP 2: Process Customer Name ──
    elif prev_step == 2:
        clean_name = _extract_person_name(raw_message, lang)
        state["customer_name"] = clean_name if clean_name and clean_name != "Not Provided" else raw_message.strip()
        state["current_step"] = 3
        reply = "Please provide your postal pincode." if lang == "en" else "कृपया अपना पोस्टल पिनकोड बताइए।"

    # ── STEP 3: Process Postal Pincode (6 Digits Mandatory) ──
    elif prev_step == 3:
        pincode_extracted = _extract_pincode_ai(raw_message, lang)
        
        # Validation: 6 digits mandatory
        if not pincode_extracted or len(pincode_extracted) != 6:
            reply = "Postal pincode must be exactly 6 digits. Please provide your postal pincode." if lang == "en" else "पोस्टल पिनकोड 6 अंकों का होना अनिवार्य है। कृपया अपना 6 अंकों का पिनकोड फिर से बताइए।"
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
                "state": state
            }

        state["pin_code"] = pincode_extracted
        
        # Step 5 in script: Address Confirmation as per Pincode
        lookup_res = lookup_pincode(pincode_extracted)
        formatted_address = lookup_res.get("formatted", "")
        
        if formatted_address:
            state["pincode_address"] = formatted_address
            state["city_state"] = f"{lookup_res.get('district', '')}, {lookup_res.get('state', '')}".strip(", ")
            state["state_name"] = lookup_res.get("state", "")
            state["city_name"] = lookup_res.get("district", "")
            state["current_step"] = 4
            
            if lang == "hi":
                reply = f"प्रदान किए गए पिनकोड के अनुसार, आपका पता {formatted_address} है। कृपया पुष्टि करें कि क्या यह सही है?"
            else:
                reply = f"As per the pincode provided, your address is {formatted_address}. Kindly confirm if this is correct."
        else:
            # Fallback if pincode address could not be resolved
            state["current_step"] = 5
            reply = "Kindly tell me your state." if lang == "en" else "कृपया अपना राज्य बताइए।"

    # ── STEP 4: Address Confirmation (As per Pincode) ──
    elif prev_step == 4:
        cust_name = state.get("customer_name", "Customer")
        is_yes = any(w in msg for w in ["yes", "yeah", "yep", "correct", "right", "ok", "haan", "sahi", "ha", "ji", "हाँ", "सही", "ठीक"])
        is_no = any(w in msg for w in ["no", "nope", "incorrect", "wrong", "nahi", "na", "गलत", "नहीं", "ना"])

        if is_yes or not is_no:
            # If Customer says "Yes": Proceed to full address with landmark
            state["current_step"] = 6
            if lang == "hi":
                reply = f"धन्यवाद, {cust_name} जी। कृपया लैंडमार्क के साथ अपना पूरा पता बताइए।"
            else:
                reply = f"Thank you, Mr. {cust_name}. Kindly provide your address with a landmark."
        else:
            # If Customer says "No": Ask for their state
            state["current_step"] = 5
            reply = "Kindly tell me your state." if lang == "en" else "कृपया अपना राज्य बताइए।"

    # ── STEP 5: Manual State Collection (Fallback when pincode is not confirmed) ──
    elif prev_step == 5:
        cust_name = state.get("customer_name", "Customer")
        state["state_name"] = raw_message.strip()
        state["city_state"] = raw_message.strip()
        state["current_step"] = 6
        if lang == "hi":
            reply = f"धन्यवाद, {cust_name} जी। कृपया लैंडमार्क के साथ अपना पूरा पता बताइए।"
        else:
            reply = f"Thank you, Mr. {cust_name}. Kindly provide your address with a landmark."

    # ── STEP 6: Full Address with Landmark ──
    elif prev_step == 6:
        state["company_name"] = raw_message.strip()  # Full address
        state["full_address"] = raw_message.strip()
        state["current_step"] = 7
        
        reply = "Kindly provide the machine serial number." if lang == "en" else "कृपया मशीन का सीरियल नंबर बताइए।"

    # ── STEP 7: Machine Serial Number ──
    elif prev_step == 7:
        has_no_serial = any(w in msg for w in [
            "don't have", "dont have", "not available", "no serial", "pata nahi", "maloom nahi",
            "nahi hai", "nhi hai", "invoice nahi hai", "baad me", "later", "nahi pata", "no"
        ])
        
        if has_no_serial:
            # Caller does not have serial number -> Gracefully guide and proceed to mobile number
            state["machine_sr_no"] = "Not Provided"
            state["current_step"] = 9
            if lang == "hi":
                reply = "सर/मैडम, उत्पाद का सीरियल नंबर उत्पाद पर या खरीद चालान पर मिल सकता है। कोई बात नहीं, हम अभी इसके बिना आगे बढ़ते हैं। कृपया अपना मोबाइल नंबर बताइए।"
            else:
                reply = "Sir/Ma'am, to assist you further, you can find the serial number on the product or in your purchase invoice. No problem at all, we will proceed for now. Kindly provide your mobile number."
        else:
            # Extract serial number string
            clean_sr = _clean_serial_number(raw_message)
            state["temp_serial_no"] = clean_sr
            state["current_step"] = 8
            
            if lang == "hi":
                reply = f"आपने बताया {clean_sr}। आगे बढ़ने के लिए कृपया 'हाँ' कहें, या सीरियल नंबर फिर से दर्ज करने के लिए 'ना' कहें।"
            else:
                reply = f"You said {clean_sr}. Please say 'Yes' to proceed, or 'No' to re-enter the serial number."

    # ── STEP 8: Serial Number Confirmation ──
    elif prev_step == 8:
        is_yes = any(w in msg for w in ["yes", "yeah", "yep", "correct", "right", "ok", "haan", "sahi", "ha", "हाँ", "सही", "ठीक"])
        is_no = any(w in msg for w in ["no", "nope", "incorrect", "wrong", "nahi", "na", "गलत", "नहीं", "ना"])

        if is_yes or not is_no:
            state["machine_sr_no"] = state.get("temp_serial_no", "Not Provided")
            state["current_step"] = 9
            reply = "Kindly provide your mobile number." if lang == "en" else "कृपया अपना मोबाइल नंबर बताइए।"
        else:
            # Caller said "No" -> Re-enter serial number
            state["current_step"] = 7
            reply = "Kindly provide the machine serial number once again." if lang == "en" else "कृपया मशीन का सीरियल नंबर एक बार फिर बताइए।"

    # ── STEP 9: Mobile Number (10 Digits Validation) ──
    elif prev_step == 9:
        accumulated = state.get("partial_phone_digits", "")
        extracted_digits = _extract_phone_number_ai(raw_message, lang)
        raw_digits = "".join(filter(str.isdigit, raw_message))

        new_digits = extracted_digits if len(extracted_digits) > 0 else raw_digits
        combined_digits = (accumulated + new_digits).strip()

        valid_phone = ""
        if len(combined_digits) == 10:
            valid_phone = combined_digits
        elif len(combined_digits) in (11, 12) and combined_digits.startswith("91"):
            valid_phone = combined_digits[-10:]
        elif len(extracted_digits) == 10:
            valid_phone = extracted_digits

        if not valid_phone:
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
                    "state": state
                }
            
            reply = "Your mobile number seems invalid. Kindly provide your 10-digit mobile number." if lang == "en" else "आपका मोबाइल नंबर अमान्य लग रहा है। कृपया अपना 10 अंकों का मोबाइल नंबर बताइए।"
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
                "state": state
            }
        else:
            phone_num = valid_phone
            state["registered_mobile"] = phone_num
            state.pop("partial_phone_digits", None)
            state["current_step"] = 10
            
            spoken_num = _format_spoken_number(phone_num, lang)
            if lang == "hi":
                reply = f"आपने बताया कि आपका मोबाइल नंबर {spoken_num} है। यदि यह सही है, तो कृपया 'हाँ' या 'ठीक है' कहें। यदि यह गलत है, तो 'नहीं' कहें।"
            else:
                reply = f"You said your mobile number is {spoken_num}. If this is correct, please say 'Yes' or 'OK.' If it is incorrect, please say 'No.'"

    # ── STEP 10: Number Confirmation ──
    elif prev_step == 10:
        is_yes = any(w in msg for w in ["yes", "yeah", "yep", "correct", "right", "ok", "haan", "sahi", "ha", "हाँ", "सही", "ठीक", "okay"])
        is_no = any(w in msg for w in ["no", "nope", "incorrect", "wrong", "nahi", "na", "गलत", "नहीं", "ना"])

        if is_yes or not is_no:
            # Proceed to Step 10 in Script: Complaint Recording
            state["current_step"] = 11
            if lang == "hi":
                reply = "धन्यवाद। कृपया अपने फ्रीजर या मशीन की समस्या विस्तार से बताइए। आप दो मिनट तक अपनी समस्या बता सकते हैं। आपका संदेश रिकॉर्ड किया जाएगा और तुरंत कार्रवाई के लिए हमारे सर्विस इंजीनियर को भेजा जाएगा। कृपया शुरू करें।"
            else:
                reply = "Thank you. Kindly describe the issue with your Freezer. You may speak for up to 2 minutes. Your message will be recorded and forwarded to our Service Engineer for immediate action. Please begin after the beep."
        else:
            # If Customer says "No"
            state["current_step"] = 9
            if lang == "hi":
                reply = "क्षमा करें। कृपया अपना मोबाइल नंबर एक बार फिर दोहराएं।"
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

        cust_name = state.get("customer_name", "Customer")
        spoken_ticket = _format_spoken_ticket(ticket_number, lang)

        if lang == "hi":
            reply = (
                f"धन्यवाद {cust_name} जी। आपकी शिकायत आइस मेक रेफ्रिजरेशन लिमिटेड में सफलतापूर्वक दर्ज कर ली गई है। "
                f"कृपया भविष्य के संदर्भ के लिए अपना शिकायत नंबर {ticket_number} (नोट: {spoken_ticket}) लिख लें। "
                f"हमारी सर्विस टीम जल्द ही आपसे संपर्क करेगी। आइस मेक चुनने के लिए धन्यवाद। आपका दिन शुभ हो। [FLOW_COMPLETE]"
            )
        else:
            reply = (
                f"Thank you, Mr. {cust_name}. Your complaint has been successfully registered with Ice Make Refrigeration Limited. "
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
            "skip_name_collection": True
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
        "state": state
    }

# ── Helpers for Entity Extraction, DB Logging & Notifications ──

def _clean_serial_number(text: str) -> str:
    """Cleans machine serial number input."""
    clean = text.strip()
    clean = re.sub(r'^(machine|serial|model|sr|no|number|serial\s+number|सीरियल\s+नंबर|मशीन)\s+', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'[.,!?\s]', '', clean).upper()
    return clean if clean else text.strip()

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
    clean = re.sub(r'^(my\s+name\s+is|i\s+am|iam|this\s+is|name\s+is|मेरा\s+नाम|नाम|मैं)\s+', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'\s+(is\s+my\s+name|speaking|here|है|हूं)$', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'[।!?,.\-]', '', clean).strip()

    words = clean.split()
    if 1 <= len(words) <= 3 and len(clean) <= 30 and not any(w in clean.lower() for w in ["complaint", "issue", "problem", "freezer", "chiller"]):
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
        "पांच": "5", "पाँच": "5", "छह": "6", "सात": "7", "आठ": "8", "नौ": "9", "दस": "10"
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

    digits = _extract_phone_number_ai(raw_message, lang)
    if len(digits) == 10:
        return None

    query_triggers = [
        "where", "office", "head office", "location", "factory", "ahmedabad", "gandhinagar",
        "kahan", "kaha", "price", "cost", "warranty", "repeat", "फिर से"
    ]
    if not any(t in raw_message.lower() for t in query_triggers):
        return None

    try:
        from conversations.services.azure_openai_service import client
        from django.conf import settings

        prompt = f"""You are the female AI Voice Customer Service Assistant for Ice Make Refrigeration Ltd.
The caller asked a question: "{raw_message}".
Ice Make Info: Head office & factory at Dantali, Gandhinagar - Ahmedabad Highway, Gujarat. Manufactures Cold Storage, Blast Freezers, Chillers.
Instructions:
1. Always maintain a polite, courteous female persona. In Hindi, strictly use feminine verb forms and self-references (e.g., 'सकती हूँ', 'करती हूँ', 'बताती हूँ', 'समझ गई').
2. Answer their question concisely and politely in language '{lang}'.
3. Then smoothly transition back to asking them for their complaint detail.
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
                "state": state
            }
    except Exception:
        pass

    return None
