import os
import re

file_path = "icemake_v2_bot/strategy.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add ICEMAKE_V2_SERIAL_INVALID_ALPHANUMERIC after ICEMAKE_V2_SERIAL_REASK
target_reask = '''ICEMAKE_V2_SERIAL_REASK = {
    "en": "My apologies! Could you please share your correct machine serial number again?",
    "hi": "माफ़ कीजिए! कृपया अपनी मशीन का सही सीरियल नंबर दोबारा बताइए।",
    "gu": "માફ કરશો! કૃપા કરીને તમારો સાચો મશીન સીરીયલ નંબર ફરીથી જણાવો.",
    "te": "క్షమించండి! దయచేసి మీ సరైన మెషిన్ సీరియల్ నంబర్‌ను మళ్లీ చెప్పండి.",
    "pa": "ਮਾਫ਼ ਕਰਨਾ ਜੀ! ਕਿਰਪਾ ਕਰਕੇ ਆਪਣੀ ਮਸ਼ੀਨ ਦਾ ਸਹੀ ਸੀਰੀਅਲ ਨੰਬਰ ਦੁਬਾਰਾ ਦੱਸੋ।",
    "bn": "দুঃখিত! দয়া করে আপনার মেশিনের সঠিক সিরিয়াল নম্বরটি আবার বলুন।",
    "mr": "क्षमस्व! कृपया तुमच्या मशीनचा अचूक सिरीयल नंबर पुन्हा सांगा.",
    "ta": "மன்னிக்கவும்! தயவுசெய்து உங்கள் சரியான மெஷின் சீரியல் எண்ணை மீண்டும் சொல்லுங்கள்.",
    "kn": "ಕ್ಷಮಿಸಿ! ದಯವಿಟ್ಟು ನಿಮ್ಮ ಸರಿಯಾದ ಯಂತ್ರದ ಸೀರಿಯಲ್ ಸಂಖ್ಯೆಯನ್ನು ಮತ್ತೆ ತಿಳಿಸಿ.",
    "ml": "ക്ഷമിക്കണം! ദയവായി നിങ്ങളുടെ മെഷീന്റെ ശരിയായ സീരിയൽ നമ്പർ വീണ്ടും പറയൂ."
}'''

replacement_reask = '''ICEMAKE_V2_SERIAL_REASK = {
    "en": "My apologies! Could you please share your correct machine serial number again?",
    "hi": "माफ़ कीजिए! कृपया अपनी मशीन का सही सीरियल नंबर दोबारा बताइए।",
    "gu": "માફ કરશો! કૃપા કરીને તમારો સાચો મશીન સીરીયલ નંબર ફરીથી જણાવો.",
    "te": "క్షమించండి! దయచేసి మీ సరైన మెషిన్ సీరియల్ నంబర్‌ను మళ్లీ చెప్పండి.",
    "pa": "ਮਾਫ਼ ਕਰਨਾ ਜੀ! ਕਿਰਪਾ ਕਰਕੇ ਆਪਣੀ ਮਸ਼ੀਨ ਦਾ ਸਹੀ ਸੀਰੀਅਲ ਨੰਬਰ ਦੁਬਾਰਾ ਦੱਸੋ।",
    "bn": "দুঃখিত! দয়া করে আপনার মেশিনের সঠিক সিরিয়াল নম্বরটি আবার বলুন।",
    "mr": "क्षमस्व! कृपया तुमच्या मशीनचा अचूक सिरीयल नंबर पुन्हा सांगा.",
    "ta": "மன்னிக்கவும்! தயவுசெய்து உங்கள் சரியான மெஷின் சீரியல் எண்ணை மீண்டும் சொல்லுங்கள்.",
    "kn": "ಕ್ಷಮಿಸಿ! ದಯವಿಟ್ಟು ನಿಮ್ಮ ಸರಿಯಾದ ಯಂತ್ರದ ಸೀರಿಯಲ್ ಸಂಖ್ಯೆಯನ್ನು ಮತ್ತೆ ತಿಳಿಸಿ.",
    "ml": "ക്ഷമിക്കണം! ദയവായി നിങ്ങളുടെ മെഷീന്റെ ശരിയായ സീരിയൽ നമ്പർ വീണ്ടും പറയൂ."
}

ICEMAKE_V2_SERIAL_INVALID_ALPHANUMERIC = {
    "en": "Ice Make machine serial numbers are alphanumeric and must contain both letters and numbers, like VCB2502116 or DF25008959. Could you please share the complete serial number?",
    "hi": "आइस मेक मशीन का सीरियल नंबर अल्फ़ान्यूमेरिक होता है, जिसमें अक्षर और नंबर दोनों होने चाहिए, जैसे VCB 2502116 या DF 25008959। कृपया अपनी मशीन का पूरा सीरियल नंबर बताइए।",
    "gu": "આઈસ મેક મશીનનો સીરીયલ નંબર આલ્ફાન્યુમેરિક હોય છે, જેમાં અક્ષર અને નંબર બંને હોવા જોઈએ, જેમ કે VCB 2502116 અથવા DF 25008959. કૃપા કરીને તમારી મશીનનો પૂરો સીરીયલ નંબર જણાવો.",
    "te": "ఐస్ మేక్ మెషీన్ సీరియల్ నంబర్ ఆల్ఫాన్యూమరిక్ అయి ఉండాలి, అక్షరాలు మరియు నంబర్లు రెండూ ఉండాలి (ఉదాహరణకు VCB 2502116). దయచేసి పూర్తి సీరియల్ నంబర్ చెప్పండి.",
    "pa": "ਆਈਸ ਮੇਕ ਮਸ਼ੀਨ ਦਾ ਸੀਰੀਅਲ ਨੰਬਰ ਅਲਫਾਨਿਊਮੇਰਿਕ ਹੁੰਦਾ ਹੈ, ਜਿਸ ਵਿੱਚ ਅੱਖਰ ਅਤੇ ਨੰਬਰ ਦੋਵੇਂ ਹੁੰਦੇ ਹਨ (ਜਿਵੇਂ VCB 2502116)। ਕਿਰਪਾ ਕਰਕੇ ਪੂਰਾ ਸੀਰੀਅਲ ਨੰਬਰ ਦੱਸੋ।",
    "bn": "আইস মেক মেশিনের সিরিয়াল নম্বরটিতে অক্ষর এবং সংখ্যা উভয়ই থাকতে হবে (যেমন VCB 2502116)। অনুগ্রহ করে সম্পূর্ণ সিরিয়াল নম্বরটি বলুন।",
    "mr": "आइस मेक मशीनचा सिरीयल नंबर अल्फान्युमेरिक असतो, ज्यामध्ये अक्षर आणि नंबर दोन्ही असावे लागतात (उदा. VCB 2502116). कृपया पूर्ण सिरीयल नंबर सांगा.",
    "ta": "ஐஸ் மேக் மெஷின் சீரியல் எண்ணில் எழுத்துக்கள் மற்றும் எண்கள் இரண்டும் இருக்க வேண்டும் (எ.கா. VCB 2502116). தயவுசெய்து முழு சீரியல் எண்ணையும் பகிரவும்.",
    "kn": "ಐಸ್ ಮೇಕ್ ಯಂತ್ರದ ಸೀರಿಯಲ್ ಸಂಖ್ಯೆಯಲ್ಲಿ ಅಕ್ಷರಗಳು ಮತ್ತು ಸಂಖ್ಯೆಗಳು ಎರಡೂ ಇರಬೇಕು (ಉದಾ. VCB 2502116). ದಯವಿಟ್ಟು ಸಂಪೂರ್ಣ ಸೀರಿಯಲ್ ಸಂಖ್ಯೆಯನ್ನು ತಿಳಿಸಿ.",
    "ml": "ഐസ് മേക്ക് മെഷീൻ സീരിയൽ നമ്പറിൽ അക്ഷരങ്ങളും അക്കങ്ങളും ഉണ്ടായിരിക്കണം (ഉദാ. VCB 2502116). ദയവായി പൂർണ്ണമായ സീരിയൽ നമ്പർ നൽകുക."
}'''

if target_reask in content:
    content = content.replace(target_reask, replacement_reask)
    print("1. Added ICEMAKE_V2_SERIAL_INVALID_ALPHANUMERIC successfully.")
else:
    print("1. Warning: target_reask not found.")

# 2. Add is_valid_alphanumeric_serial function before _normalize_alphanumeric_serial
target_norm_func = 'def _normalize_alphanumeric_serial(serial_str: str) -> str:'
replacement_norm_func = '''def is_valid_alphanumeric_serial(serial_str: str) -> bool:
    """
    Validates that the machine serial number strictly contains BOTH:
    - At least one alphabet character (A-Z)
    - At least one digit (0-9)
    - Total alphanumeric length >= 3
    """
    if not serial_str:
        return False
    clean = re.sub(r'[^a-zA-Z0-9]', '', str(serial_str)).upper()
    has_alpha = any(c.isalpha() for c in clean)
    has_digit = any(c.isdigit() for c in clean)
    return has_alpha and has_digit and len(clean) >= 3

def _normalize_alphanumeric_serial(serial_str: str) -> str:'''

if target_norm_func in content:
    content = content.replace(target_norm_func, replacement_norm_func)
    print("2. Added is_valid_alphanumeric_serial successfully.")
else:
    print("2. Warning: target_norm_func not found.")

# 3. Update priority sorting in _normalize_alphanumeric_serial to favor tokens with both letters and numbers
target_sort = 'valid.sort(key=lambda x: (any(x.startswith(p) for p in known_prefixes), len(x)), reverse=True)'
replacement_sort = 'valid.sort(key=lambda x: (is_valid_alphanumeric_serial(x), any(x.startswith(p) for p in known_prefixes), len(x)), reverse=True)'
if target_sort in content:
    content = content.replace(target_sort, replacement_sort)
    print("3. Updated _normalize_alphanumeric_serial sort priority.")
else:
    print("3. Warning: target_sort not found.")

# 4. Update system prompt Rule 3 in _handle_smart_serial_step
old_rule3 = '''3. PINPOINT SERIAL EXTRACTION FROM LONG SENTENCES (NO CHARACTER LIMIT):
   - NO CHARACTER LIMIT: Machine serial numbers can be of ANY LENGTH (short, medium, or very long, e.g. 5, 8, 10, 18, 19, 25+ characters). NEVER truncate, drop characters, or refuse due to length!
   - EMBEDDED IN SENTENCES: Callers almost never state just the serial number. They give long explanations, complaints, or sentences with the serial number embedded anywhere (in the beginning, middle, or end).
   - EXAMPLES OF PINPOINT EXTRACTION:
     * "हाँ भैया मेरा फ्रीजर चालू नहीं हो रहा है और उसका सीरियल नंबर VCB2502116 है तो कब तक इंजीनियर आएगा?" -> extracted_serial: "VCB2502116"
     * "હું દુકાન પરથી બોલું છું, અમારું ડીપ ફ્રીઝર બગડી ગયું છે અને મશીન પર DF25008959 લખેલું છે જલ્દી માણસ મોકલો" -> extracted_serial: "DF25008959"
     * "Sir we bought this unit last year and I checked the invoice it is CIM305B501-25030653 please register complaint" -> extracted_serial: "CIM305B501-25030653"
     * "अरे भाई वो मशीन पे लिखा है सी आई एम 305 बी 501 डैश 25030653 यही नंबर है ना?" -> extracted_serial: "CIM305B501-25030653"
     * "હા ભાઈ અમારે આઈસ ફેક્ટરી છે અને મશીન પર ડીઆઈએમ 405 બીએક્સ 01 - 260500067 લખ્યું છે તો જલ્દીથી કમ્પ્લેન નોંધી લો" -> extracted_serial: "DIM405BX01-260500067"
     * "मेरा फ्रीजर ठंडा नहीं कर रहा सीरियल नंबर है 94285123456789 जल्दी इंजीनियर भेजो" -> extracted_serial: "94285123456789"
     * "हमारा मशीन का नंबर है जी आई एम 268 ई 404 - 261000012 इसको नोट कर लो" -> extracted_serial: "GIM268E404-261000012"
   - ALWAYS capture the complete alphanumeric sequence including prefix letters ("VCB", "DF", "CIM", "DIM", "GIM"), internal letters ('B', 'BX', 'E'), digits, and hyphens ('-').
   - Convert all spoken regional phonetics to uppercase Latin characters.
   - Discard all conversational dialogue, complaints, and filler words. Return ONLY the clean uppercase machine serial string in "extracted_serial".'''

new_rule3 = '''3. PINPOINT SERIAL EXTRACTION & STRICT ALPHANUMERIC VALIDATION:
   - MANDATORY ALPHANUMERIC REQUIREMENT: A valid machine serial number MUST contain BOTH letters (A-Z) AND digits (0-9) (e.g. VCB2502116, DF25008959, CIM305B501-25030653).
   - If caller provides ONLY numbers without letters (e.g. "2502116", "9428512345"), or ONLY letters without numbers (e.g. "VCB", "DF"), it is INVALID. Set intent to "INVALID_SERIAL" and politely instruct them in "reply" that the serial number must contain both letters and numbers (give an example like VCB 2502116 or DF 25008959).
   - NO CHARACTER LIMIT: Machine serial numbers can be of ANY LENGTH (short, medium, or very long, e.g. 5, 8, 10, 18, 19, 25+ characters). NEVER truncate, drop characters, or refuse due to length!
   - EMBEDDED IN SENTENCES: Callers almost never state just the serial number. They give long explanations, complaints, or sentences with the serial number embedded anywhere (in the beginning, middle, or end).
   - EXAMPLES OF PINPOINT EXTRACTION:
     * "हाँ भैया मेरा फ्रीजर चालू नहीं हो रहा है और उसका सीरियल नंबर VCB2502116 है तो कब तक इंजीनियर आएगा?" -> extracted_serial: "VCB2502116"
     * "હું દુકાન પરથી બોલું છું, અમારું ડીપ ફ્રીઝર બગડી ગયું છે અને મશીન પર DF25008959 લખેલું છે જલ્દી માણસ મોકલો" -> extracted_serial: "DF25008959"
     * "Sir we bought this unit last year and I checked the invoice it is CIM305B501-25030653 please register complaint" -> extracted_serial: "CIM305B501-25030653"
     * "अरे भाई वो मशीन पे लिखा है सी आई एम 305 बी 501 डैश 25030653 यही नंबर है ना?" -> extracted_serial: "CIM305B501-25030653"
     * "હા ભાઈ અમારે આઈસ ફેક્ટરી છે અને મશીન પર ડીઆઈએમ 405 બીએક્સ 01 - 260500067 લખ્યું છે તો જલ્દીથી કમ્પ્લેન નોંધી લો" -> extracted_serial: "DIM405BX01-260500067"
     * "हमारा मशीन का नंबर है जी आई एम 268 ई 404 - 261000012 इसको नोट कर लो" -> extracted_serial: "GIM268E404-261000012"
   - ALWAYS capture the complete alphanumeric sequence including prefix letters ("VCB", "DF", "CIM", "DIM", "GIM"), internal letters ('B', 'BX', 'E'), digits, and hyphens ('-').
   - Convert all spoken regional phonetics to uppercase Latin characters.
   - Discard all conversational dialogue, complaints, and filler words. Return ONLY the clean uppercase machine serial string in "extracted_serial".'''

if old_rule3 in content:
    content = content.replace(old_rule3, new_rule3)
    print("4. Updated system prompt Rule 3.")
else:
    print("4. Warning: old_rule3 not found.")

# 5. Update user_prompt intent list
old_user_prompt = '''Classify caller's intent into ONE of:
- PROVIDE_SERIAL: customer stated an alphanumeric serial number (contains letters and/or numbers) or model code.
- CONFIRM_YES: customer confirms readback serial is correct (yes/haan/sahi hai/barabar).
- CONFIRM_NO: customer says readback serial is incorrect (no/nahi/galat).
- WAIT: customer asks to hold/wait/give time.
- WHERE_IS_SERIAL: customer asks where serial is, what it is, or is confused where to look.
- CANNOT_PROVIDE: customer cannot provide serial, does not have it, don't remember, lost bill, away from machine, or wants complaint without it.
- QUESTION: customer asked a specific question about warranty, visit charges, engineer, etc.

Return JSON only:
{
  "intent": "PROVIDE_SERIAL" | "CONFIRM_YES" | "CONFIRM_NO" | "WAIT" | "WHERE_IS_SERIAL" | "CANNOT_PROVIDE" | "QUESTION",'''

new_user_prompt = '''Classify caller's intent into ONE of:
- PROVIDE_SERIAL: customer stated a valid alphanumeric serial number containing BOTH letters and numbers (e.g. VCB2502116, DF25008959, CIM305B501-25030653).
- INVALID_SERIAL: customer stated a number that is ONLY digits (e.g. 2502116) or ONLY letters (e.g. VCB), lacking the required alphanumeric combination of both letters and numbers.
- CONFIRM_YES: customer confirms readback serial is correct (yes/haan/sahi hai/barabar).
- CONFIRM_NO: customer says readback serial is incorrect (no/nahi/galat).
- WAIT: customer asks to hold/wait/give time.
- WHERE_IS_SERIAL: customer asks where serial is, what it is, or is confused where to look.
- CANNOT_PROVIDE: customer cannot provide serial, does not have it, don't remember, lost bill, away from machine, or wants complaint without it.
- QUESTION: customer asked a specific question about warranty, visit charges, engineer, etc.

Return JSON only:
{
  "intent": "PROVIDE_SERIAL" | "INVALID_SERIAL" | "CONFIRM_YES" | "CONFIRM_NO" | "WAIT" | "WHERE_IS_SERIAL" | "CANNOT_PROVIDE" | "QUESTION",'''

if old_user_prompt in content:
    content = content.replace(old_user_prompt, new_user_prompt)
    print("5. Updated user_prompt intent list.")
else:
    print("5. Warning: old_user_prompt not found.")

# 6. Update intent handling in _handle_smart_serial_step
old_intent_handling = '''    elif intent == "PROVIDE_SERIAL" or (extracted and len(extracted) >= 3) or (len(re.findall(r'\\d+', raw_message)) > 0 and len("".join(re.findall(r'\\d+', raw_message))) >= 3):
        raw_val = extracted if extracted else _clean_model_or_serial(raw_message)
        serial_val = _normalize_alphanumeric_serial(raw_val)
        if not serial_val:
            serial_val = raw_val
        state["pending_serial_number"] = serial_val
        state["serial_needs_confirmation"] = True
        next_step = 6
        spoken_serial = _format_spoken_serial(serial_val, lang)
        template = ICEMAKE_V2_SERIAL_CONFIRM.get(lang, ICEMAKE_V2_SERIAL_CONFIRM["en"])
        reply = template.format(serial=spoken_serial)'''

new_intent_handling = '''    elif intent == "INVALID_SERIAL":
        state["pending_serial_number"] = ""
        state["serial_needs_confirmation"] = False
        next_step = 6
        reply = ai_reply if ai_reply else ICEMAKE_V2_SERIAL_INVALID_ALPHANUMERIC.get(lang, ICEMAKE_V2_SERIAL_INVALID_ALPHANUMERIC["en"])

    elif intent == "PROVIDE_SERIAL" or (extracted and len(extracted) >= 3) or (len(re.findall(r'\\d+', raw_message)) > 0 and len("".join(re.findall(r'\\d+', raw_message))) >= 3):
        raw_val = extracted if extracted else _clean_model_or_serial(raw_message)
        serial_val = _normalize_alphanumeric_serial(raw_val)
        if not serial_val:
            serial_val = raw_val

        # STRICT ALPHANUMERIC VALIDATION CHECK (must contain BOTH alphabet and number)
        if not is_valid_alphanumeric_serial(serial_val):
            state["pending_serial_number"] = ""
            state["serial_needs_confirmation"] = False
            next_step = 6
            reply = ai_reply if (ai_reply and ("अक्षर" in ai_reply or "letters" in ai_reply or "અક્ષર" in ai_reply or "अल्फ़ान्यूमेरिक" in ai_reply or "alphanumeric" in ai_reply.lower())) else ICEMAKE_V2_SERIAL_INVALID_ALPHANUMERIC.get(lang, ICEMAKE_V2_SERIAL_INVALID_ALPHANUMERIC["en"])
        else:
            state["pending_serial_number"] = serial_val
            state["serial_needs_confirmation"] = True
            next_step = 6
            spoken_serial = _format_spoken_serial(serial_val, lang)
            template = ICEMAKE_V2_SERIAL_CONFIRM.get(lang, ICEMAKE_V2_SERIAL_CONFIRM["en"])
            reply = template.format(serial=spoken_serial)'''

if old_intent_handling in content:
    content = content.replace(old_intent_handling, new_intent_handling)
    print("6. Updated intent handling.")
else:
    print("6. Warning: old_intent_handling not found.")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("File updated successfully.")
