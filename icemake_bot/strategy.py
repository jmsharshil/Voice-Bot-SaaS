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
    },
    "pa": {
        1: "ਧੰਨਵਾਦ, ਕਿਰਪਾ ਕਰਕੇ ਆਪਣਾ ਨਾਮ ਦੱਸੋ।",
        2: "{name} ਜੀ, ਤੁਹਾਡੇ ਨਾਲ ਗੱਲ ਕਰਕੇ ਬਹੁਤ ਖੁਸ਼ੀ ਹੋਈ! ਤੁਹਾਡੀ ਬਿਹਤਰ ਮਦਦ ਲਈ, ਕੀ ਤੁਸੀਂ ਦੱਸ ਸਕਦੇ ਹੋ ਕਿ ਤੁਸੀਂ ਕਿਸ ਸੂਬੇ ਤੋਂ ਫ਼ੋਨ ਕਰ ਰਹੇ ਹੋ?",
        3: "ਠੀਕ ਹੈ, ਧੰਨਵਾਦ! ਅਤੇ ਤੁਹਾਡਾ ਸ਼ਹਿਰ, ਪਤਾ ਅਤੇ ਜੇ ਉਪਲਬਧ ਹੋਵੇ ਤਾਂ ਪਿੰਨਕੋਡ ਨੰਬਰ ਕੀ ਹੈ?",
        4: "ਕਿਰਪਾ ਕਰਕੇ ਆਪਣਾ ਫ਼ੋਨ ਨੰਬਰ ਦੱਸੋ।",
        6: "ਧੰਨਵਾਦ {name} ਜੀ! ਤੁਸੀਂ ਆਈਸ ਮੇਕ ਦਾ ਕਿਹੜਾ ਪ੍ਰੋਡਕਟ ਵਰਤ ਰਹੇ ਹੋ?",
    },
    "bn": {
        1: "ধন্যবাদ, দয়া করে আপনার নাম বলুন।",
        2: "{name} জি, আপনার সাথে কথা বলে খুব ভালো লাগলো! আপনাকে সাহায্য করতে, দয়া করে বলবেন আপনি কোন রাজ্য থেকে ফোন করছেন?",
        3: "ঠিক আছে, ধন্যবাদ! এবং আপনার শহর, ঠিকানা এবং পিনকোড নম্বর কত?",
        4: "দয়া করে আপনার ফোন নম্বরটি বলুন।",
        6: "ধন্যবাদ {name} জি! আপনি আইস মেকের কোন প্রোডাক্টটি ব্যবহার করছেন?",
    },
    "mr": {
        1: "धन्यवाद, कृपया तुमचे नाव सांगा.",
        2: "{name} जी, तुमच्याशी बोलून खूप आनंद झाला! तुम्हाला उत्तम मदत करण्यासाठी, तुम्ही कोणत्या राज्यातून बोलत आहात ते सांगू शकाल का?",
        3: "ठीक आहे, धन्यवाद! आणि तुमचा शहर, पत्ता आणि उपलब्ध असल्यास पिनकोड नंबर कोणता आहे?",
        4: "कृपया तुमचा फोन नंबर सांगा.",
        6: "धन्यवाद {name} जी! तुम्ही आईस मेकचे कोणते उत्पादन वापरत आहात?",
    },
    "ta": {
        1: "நன்றி, தயவுசெய்து உங்கள் பெயரை சொல்லுங்கள்.",
        2: "{name} அவர்களே, உங்களுடன் பேசுவதில் மிக்க மகிழ்ச்சி! உங்களுக்கு சிறந்த உதவி செய்வதற்கு, நீங்கள் எந்த மாநிலத்திலிருந்து அழைக்கிறீர்கள் என்று சொல்ல முடியுமா?",
        3: "சரி, நன்றி! உங்கள் நகரம், முகவரி மற்றும் பின்கோடு எண் என்ன?",
        4: "தயவுசெய்து உங்கள் தொலைபேசி எண்ணைச் சொல்லுங்கள்.",
        6: "நன்றி {name} அவர்களே! நீங்கள் எந்த ஐஸ் மேக் தயாரிப்பைப் பயன்படுத்துகிறீர்கள்?",
    },
    "kn": {
        1: "ಧನ್ಯವಾದಗಳು, ದಯವಿಟ್ಟು ನಿಮ್ಮ ಹೆಸರನ್ನು ಹೇಳಿ.",
        2: "{name} ಅವರೇ, ನಿಮ್ಮೊಂದಿಗೆ ಮಾತನಾಡಲು ತುಂಬಾ ಸಂತೋಷವಾಗಿದೆ! ನಿಮಗೆ ಉತ್ತಮವಾಗಿ ಸಹಾಯ ಮಾಡಲು, ನೀವು ಯಾವ ರಾಜ್ಯದಿಂದ ಕರೆ ಮಾಡುತ್ತಿದ್ದೀರಿ ಎಂದು ಹೇಳಬಹುದೇ?",
        3: "ಸರಿ, ಧನ್ಯವಾದಗಳು! ನಿಮ್ಮ ನಗರ, ವಿಳಾಸ ಮತ್ತು ಲಭ್ಯವಿದ್ದರೆ ಪಿನ್‌ಕೋಡ್ ಸಂಖ್ಯೆ ಯಾವುದು?",
        4: "ದಯವಿಟ್ಟು ನಿಮ್ಮ ದೂರವಾಣಿ ಸಂಖ್ಯೆಯನ್ನು ತಿಳಿಸಿ.",
        6: "ಧನ್ಯವಾದಗಳು {name} ಅವರೇ! ನೀವು ಐಸ್ ಮೇಕ್‌ನ ಯಾವ ಉತ್ಪನ್ನವನ್ನು ಬಳಸುತ್ತಿದ್ದೀರಿ?",
    },
    "ml": {
        1: "നന്ദി, ദയവായി താങ്കളുടെ പേര് പറയാമോ?",
        2: "{name} ജി, നിങ്ങളോട് സംസാരിക്കാൻ സാധിച്ചതിൽ സന്തോഷം! മികച്ച സേവനം നൽകുന്നതിനായി, ഏത് സംസ്ഥാനത്തു നിന്നാണ് വിളിക്കുന്നതെന്ന് പറയാമോ?",
        3: "തീർച്ചയായും, നന്ദി! നിങ്ങളുടെ നഗരം, വിലാസം, ലഭ്യമാണെങ്കിൽ പിൻകോഡ് നമ്പർ ഏതാണ്?",
        4: "ദയവായി നിങ്ങളുടെ ഫോൺ നമ്പർ പറയാമോ?",
        6: "നന്ദി {name} ജി! നിങ്ങൾ ഐസ് മേക്കിന്റെ ഏത് പ്രൊഡക്റ്റാണ് ഉപയോഗിക്കുന്നത്?",
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
    elif lang == "pa":
        pa_digit_words = {'0': 'ਜ਼ੀਰੋ', '1': 'ਇੱਕ', '2': 'ਦੋ', '3': 'ਤਿੰਨ', '4': 'ਚਾਰ', '5': 'ਪੰਜ', '6': 'ਛੇ', '7': 'ਸੱਤ', '8': 'ਅੱਠ', '9': 'ਨੌਂ'}
        return ", ".join(pa_digit_words.get(d, d) for d in phone_num)
    elif lang == "bn":
        bn_digit_words = {'0': 'শূন্য', '1': 'এক', '2': 'দুই', '3': 'তিন', '4': 'চার', '5': 'পাঁচ', '6': 'ছয়', '7': 'সাত', '8': 'আট', '9': 'নয়'}
        return ", ".join(bn_digit_words.get(d, d) for d in phone_num)
    elif lang == "mr":
        mr_digit_words = {'0': 'शून्य', '1': 'एक', '2': 'दोन', '3': 'तीन', '4': 'चार', '5': 'पाच', '6': 'सहा', '7': 'सात', '8': 'आठ', '9': 'नऊ'}
        return ", ".join(mr_digit_words.get(d, d) for d in phone_num)
    elif lang == "ta":
        ta_digit_words = {'0': 'சுழியம்', '1': 'ஒன்று', '2': 'இரண்டு', '3': 'மூன்று', '4': 'நான்கு', '5': 'ஐந்து', '6': 'ஆறு', '7': 'ஏழு', '8': 'எட்டு', '9': 'ஒன்பது'}
        return ", ".join(ta_digit_words.get(d, d) for d in phone_num)
    elif lang == "kn":
        kn_digit_words = {'0': 'ಶೂನ್ಯ', '1': 'ಒಂದು', '2': 'ಎರಡು', '3': 'ಮೂರು', '4': 'ನಾಲ್ಕು', '5': 'ಐದು', '6': 'ಆರು', '7': 'ಏಳು', '8': 'ಎಂಟು', '9': 'ಒಂಬತ್ತು'}
        return ", ".join(kn_digit_words.get(d, d) for d in phone_num)
    elif lang == "ml":
        ml_digit_words = {'0': 'പൂജ്യം', '1': 'ഒന്ന്', '2': 'രണ്ട്', '3': 'മൂന്ന്', '4': 'നാല്', '5': 'അഞ്ച്', '6': 'ആറ്', '7': 'ഏഴ്', '8': 'എട്ട്', '9': 'ഒൻപത്'}
        return ", ".join(ml_digit_words.get(d, d) for d in phone_num)
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
    elif lang == "pa":
        pa_digit_words = {'0': 'ਜ਼ੀਰੋ', '1': 'ਇੱਕ', '2': 'ਦੋ', '3': 'ਤਿੰਨ', '4': 'ਚਾਰ', '5': 'ਪੰਜ', '6': 'ਛੇ', '7': 'ਸੱਤ', '8': 'ਅੱਠ', '9': 'ਨੌਂ'}
        parts = [pa_digit_words.get(ch, ch) if ch.isdigit() else ('ਸੀ' if ch == 'C' else ch) for ch in ticket_number]
        return ", ".join(parts)
    elif lang == "bn":
        bn_digit_words = {'0': 'শূন্য', '1': 'এক', '2': 'দুই', '3': 'তিন', '4': 'চার', '5': 'পাঁচ', '6': 'ছয়', '7': 'সাত', '8': 'আট', '9': 'নয়'}
        parts = [bn_digit_words.get(ch, ch) if ch.isdigit() else ('সি' if ch == 'C' else ch) for ch in ticket_number]
        return ", ".join(parts)
    elif lang == "mr":
        mr_digit_words = {'0': 'शून्य', '1': 'एक', '2': 'दोन', '3': 'तीन', '4': 'चार', '5': 'पाच', '6': 'सहा', '7': 'सात', '8': 'आठ', '9': 'नऊ'}
        parts = [mr_digit_words.get(ch, ch) if ch.isdigit() else ('सी' if ch == 'C' else ch) for ch in ticket_number]
        return ", ".join(parts)
    elif lang == "ta":
        ta_digit_words = {'0': 'சுழியம்', '1': 'ஒன்று', '2': 'இரண்டு', '3': 'மூன்று', '4': 'நான்கு', '5': 'ஐந்து', '6': 'ஆறு', '7': 'ஏழு', '8': 'எட்டு', '9': 'ஒன்பது'}
        parts = [ta_digit_words.get(ch, ch) if ch.isdigit() else ('சி' if ch == 'C' else ch) for ch in ticket_number]
        return ", ".join(parts)
    elif lang == "kn":
        kn_digit_words = {'0': 'ಶೂನ್ಯ', '1': 'ಒಂದು', '2': 'ಎರಡು', '3': 'ಮೂರು', '4': 'ನಾಲ್ಕು', '5': 'ಐದು', '6': 'ಆರು', '7': 'ಏಳು', '8': 'ಎಂಟು', '9': 'ಒಂಬತ್ತು'}
        parts = [kn_digit_words.get(ch, ch) if ch.isdigit() else ('ಸಿ' if ch == 'C' else ch) for ch in ticket_number]
        return ", ".join(parts)
    elif lang == "ml":
        ml_digit_words = {'0': 'പൂജ്യം', '1': 'ഒന്ന്', '2': 'രണ്ട്', '3': 'മൂന്ന്', '4': 'നാല്', '5': 'അഞ്ച്', '6': 'ആറ്', '7': 'ഏഴ്', '8': 'എട്ട്', '9': 'ഒൻപത്'}
        parts = [ml_digit_words.get(ch, ch) if ch.isdigit() else ('സി' if ch == 'C' else ch) for ch in ticket_number]
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
    
    # ── Universal Spoken Number Word to ASCII Digit Converter ──
    raw_message = _convert_all_spoken_numbers_to_digits(raw_message, lang or "en")
    msg = raw_message.lower().strip()
    
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
                "urdu", "اردو", "उर्दू",
                "french", "फ़्रेंच", "फ्रेंच",
                "german", "जर्मन",
                "spanish", "स्पैनिश", "स्पेनिश",
                "arabic", "عربي", "अरबी",
                "odia", "oriya", "ଓଡ଼ିଆ", "उड़िया", "ओड़िया",
                "assamese", "অসমীয়া", "असमिया",
                "bhojpuri", "भोजपुरी",
                "nepali", "नेपाली",
                "konkani", "कोंकणी",
                "rajasthani", "राजस्थानी",
                "haryanvi", "हरियाणवी"
            ]

            
            if any(k in msg for k in [
                "malayalam", "malayalam", "ml", "malayala",
                "മലയാളം", "മലയാളത്തില്", "മലയാളത്തിൽ", "മലയാളം ഭാഷ",
                "मलयालम", "मलयालम में", "मलयालम भाषा"
            ]):
                lang = "ml"
            elif any(k in msg for k in [
                "kannada", "kanada", "kn",
                "ಕನ್ನಡ", "ಕನ್ನಡದಲ್ಲಿ", "ಕನ್ನಡ ಭಾಷೆ",
                "कन्नड़", "कन्नड", "कन्नड़ भाषा","कन्नाडा।"
            ]):
                lang = "kn"
            elif any(k in msg for k in [
                "tamil", "tamizh", "ta",
                "தமிழ்", "தமிழ", "தமிழில்", "தமிழ் மொழி",
                "तमिल", "तमिळ", "तमिल भाषा","तामिल","तामिल"
            ]):
                lang = "ta"
            elif any(k in msg for k in [
                "marathi", "marthi", "mr",
                "मराठी", "मराठि", "मराठीत", "मराठी भाषा", "मराठी मध्ये", "मराठीत बोला", "मराठी?"
            ]):
                lang = "mr"
            elif any(k in msg for k in [
                "bengali", "bangla", "bengoli", "bangoli", "bn",
                "বাংলা", "বাংলায়", "বাংলা ভাষা",
                "बंगाली", "बांग्ला", "बंगला","बंगाली","बेंगाली","बंगोली","बेंगोली","बंगोली","बांग्ला","बंगला","बैंगाली",
                "बंगाली भाषा","बंगाली में","बांग्ला भाषा","बांग्ला में"
            ]):
                lang = "bn"
            elif any(k in msg for k in [
                "gujarati", "gujrati", "gujrat", "guj", "gujarathi", "gujrathi",
                "ગુજરાતી", "ગુજરાતિ", "ગુજરાત", "ગુજરાતીમાં", "ગુજ", "હા",
                "गुजराती", "गुजराति", "गुजरात", "गिजराती", "गुजरती", "गुजरातीं","गुजराती?"
            ]):
                lang = "gu"
            elif any(k in msg for k in [
                "telugu", "telgu", "telugoo", "tlg", "telegu",
                "తెలుగు", "తెలుగూ", "తెలుగులో", "తెలుగులొ",
                "తేలుగు", "తేలుగూ", "తేలగు", "తేలగూ", "తేలుగు మేం",
                "તેલુગૂ", "તેલુગુ","तेलुगु", "तेलगु", "तेलुगू", "तेलुगू में",
                "तेलुगु में", "तेलगू", "तेलुगु भाषा", "तेलुगु में बात करो", "तेलुगु में बोलो"
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
                "punjabi", "panjabi", "ਪੰਜਾਬੀ", "پنجابی",
                "पंजाबी", "ਪੰਜਾਬੀ ਵਿੱਚ", "punjabi mein", "panjabi mein"
            ]):
                lang = "pa"
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
                if re.search(r'[\u0980-\u09ff]', raw_message):  # Bengali script
                    lang = "bn"
                elif re.search(r'[\u0a00-\u0a7f]', raw_message):  # Gurmukhi (Punjabi) script
                    lang = "pa"
                elif re.search(r'[\u0a80-\u0aff]', raw_message):
                    lang = "gu"
                elif re.search(r'[\u0c00-\u0c7f]', raw_message):  # Telugu script
                    lang = "te"
                elif re.search(r'[\u0b80-\u0bff]', raw_message):  # Tamil script
                    lang = "ta"
                elif re.search(r'[\u0cb0-\u0cff]', raw_message):  # Kannada script
                    lang = "kn"
                elif re.search(r'[\u0d00-\u0d7f]', raw_message):  # Malayalam script
                    lang = "ml"
                elif re.search(r'[\u0900-\u097f]', raw_message):
                    # Check if Devanagari message contains Gujarati phonetic words or Marathi words
                    if any(w in msg for w in ["गुजराती", "गुजरात", "गिजराती", "गुजरती", "गुजराती?"]):
                        lang = "gu"
                    elif any(w in msg for w in ["मराठी", "मराठि", "मराठीत", "आहे", "काय", "मला", "सांगा"]):
                        lang = "mr"
                    else:
                        lang = "hi"
                else:
                    lang = "en"
            
            if not lang:
                if re.search(r'[\u0d00-\u0d7f]', raw_message):  # Malayalam script
                    reply = "നിലവിൽ ഞങ്ങൾ ഇംഗ്ലീഷ്, ഹിന്ദി, ഗുജറാത്തി, തെലുങ്ക്, പഞ്ചാബി, ബംഗാളി, മറാത്തി, തമിഴ്, കന്നഡ, മലയാളം എന്നീ ഭാഷകളിൽ സേവനം നൽകുന്നു. ഏത് ഭാഷയിൽ തുടരാനാണ് നിങ്ങൾ ആഗ്രഹിക്കുന്നത്?"
                    tts_lang = "ml"
                elif re.search(r'[\u0980-\u09ff]', raw_message):  # Bengali script
                    reply = "বর্তমানে আমরা ইংলিশ, হিন্দি, গুজরাটি, তেলুগু, পাঞ্জাবি, মারাঠি, তামিল, কন্নড় এবং বাংলায় সেবা প্রদান করি। আপনি কোন ভাষায় এগিয়ে যেতে চান?"
                    tts_lang = "bn"
                elif re.search(r'[\u0a80-\u0aff]', raw_message):  # Gujarati script
                    reply = "હાલમાં અમે ઈંગ્લીશ, હિન્દી, ગુજરાતી, તેલુગુ, પંજાબી, બંગાળી, મરાઠી, તમિલ અને કન્નડમાં સેવા પૂરી પાડીએ છીએ. તમે કઈ ભાષામાં આગળ વધવા માંગો છો?"
                    tts_lang = "gu"
                elif re.search(r'[\u0c00-\u0c7f]', raw_message):  # Telugu script
                    reply = "ప్రస్తుతానికి మేము ఇంగ్లీష్, హిందీ, గుజరాతీ, తెలుగు, పంజాబీ, బెంగాలీ, మరాఠీ, తమిళం మరియు కన్నడ భాషలలో సేవలను అందిస్తున్నాము. మీరు ఏ భాషలో కొనసాగాలనుకుంటున్నారు?"
                    tts_lang = "te"
                elif re.search(r'[\u0b80-\u0bff]', raw_message):  # Tamil script
                    reply = "தற்போது நாங்கள் ஆங்கிலம், இந்தி, குஜராத்தி, தெலுங்கு, பஞ்சாபி, பெங்காலி, மராத்தி, தமிழ் மற்றும் கன்னடம் ஆகிய மொழிகளில் சேவைகளை வழங்குகிறோம். நீங்கள் எந்த மொழியில் தொடர விரும்புகிறீர்கள்?"
                    tts_lang = "ta"
                elif re.search(r'[\u0cb0-\u0cff]', raw_message):  # Kannada script
                    reply = "ಪ್ರಸ್ತುತ ನಾವು ಇಂಗ್ಲಿಷ್, ಹಿಂದಿ, ಗುಜರಾತಿ, ತೆಲುಗು, ಪಂಜಾಬಿ, ಬೆಂಗಾಲಿ, ಮರಾಠಿ, ತಮಿಳು ಮತ್ತು ಕನ್ನಡ ಭಾಷೆಗಳಲ್ಲಿ ಸೇವೆಗಳನ್ನು ನೀಡುತ್ತಿದ್ದೇವೆ. ನೀವು ಯಾವ ಭಾಷೆಯಲ್ಲಿ ಮುಂದುವರೆಯಲು ಬಯಸುತ್ತೀರಿ?"
                    tts_lang = "kn"
                elif re.search(r'[\u0a00-\u0a7f]', raw_message):  # Gurmukhi / Punjabi script
                    reply = "ਫਿਲਹਾਲ ਅਸੀਂ ਅੰਗਰੇਜ਼ੀ, ਹਿੰਦੀ, ਗੁਜਰਾਤੀ, ਤੇਲਗੂ, ਪੰਜਾਬੀ, ਬੰਗਾਲੀ, ਮਰਾਠੀ, ਤਮਿਲ ਅਤੇ ਕੰਨੜ ਵਿੱਚ ਸੇਵਾਵਾਂ ਪ੍ਰਦਾਨ ਕਰਦੇ ਹਾਂ। ਤੁਸੀਂ ਕਿਸ ਭਾਸ਼ਾ ਵਿੱਚ ਅੱਗੇ ਵਧਣਾ ਚਾਹੋਗੇ?"
                    tts_lang = "pa"
                elif re.search(r'[\u0900-\u097f]', raw_message):  # Devanagari script (Hindi / Marathi)
                    reply = "फ़िलहाल हम इंग्लिश, हिंदी, गुजराती, तेलुगु, पंजाबी, बंगाली, मराठी, तमिल, कन्नड़ और मलयालम में सेवा प्रदान करते हैं। आप किस भाषा में बात करना चाहेंगे?"
                    tts_lang = "hi"
                else:  # Default English
                    reply = "Currently, we support English, Hindi, Gujarati, Telugu, Punjabi, Bengali, Marathi, Tamil, Kannada, and Malayalam. Which language would you like to continue in?"
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
                        reply = f"धन्यवाद। नमस्ते {cust_name} जी! हम देख सकते हैं कि आप अपने आइस मेक {prod_name} के संबंध में कॉल कर रहे हैं। कृपया अपनी समस्या विस्तार से बताइए。"
                    elif lang == "gu":
                        reply = f"આભાર. નમસ્તે {cust_name} જી! અમે જોઈ શકીએ છીએ કે તમે તમારા આઈસ મેક {prod_name} અંગે કૉલ કરી રહ્યા છો. કૃપા કરીને તમારી સમસ્યા વિગતવાર જણાવો."
                    elif lang == "te":
                        reply = f"ధన్యవాదాలు. నమస్కారం {cust_name} గారు! మీరు మీ ఐస్ మేక్ {prod_name} గురించి కాల్ చేస్తున్నట్లు గమనించాము. దయచేసి మీ సమస్యను వివరించండి."
                    elif lang == "pa":
                        reply = f"ਧੰਨਵਾਦ। ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ {cust_name} ਜੀ! ਅਸੀਂ ਦੇਖ ਸਕਦੇ ਹਾਂ ਕਿ ਤੁਸੀਂ ਆਪਣੇ ਆਈਸ ਮੇਕ {prod_name} ਬਾਰੇ ਕਾਲ ਕਰ ਰਹੇ ਹੋ। ਕਿਰਪਾ ਕਰਕੇ ਆਪਣੀ ਸਮੱਸਿਆ ਵਿਸਥਾਰ ਨਾਲ ਦੱਸੋ।"
                    elif lang == "bn":
                        reply = f"ধন্যবাদ। নমস্কার {cust_name} জি! আমরা দেখতে পাচ্ছি যে আপনি আপনার আইস মেক {prod_name} সম্পর্কে কল করছেন। অনুগ্রহ করে আপনার সমস্যাটি বিস্তারিত বলুন।"
                    elif lang == "mr":
                        reply = f"धन्यवाद. नमस्कार {cust_name} जी! आम्ही पाहू शकतो की तुम्ही तुमच्या आईस मेक {prod_name} बाबत कॉल करत आहात. कृपया तुमची समस्या सविस्तर सांगा."
                    elif lang == "ta":
                        reply = f"நன்றி. வணக்கம் {cust_name} அவர்களே! நீங்கள் உங்கள் ஐஸ் மேக் {prod_name} பற்றி அழைக்கிறீர்கள் என்று பார்க்கிறோம். தயவுசெய்து உங்கள் பிரச்சனையை விரிவாக சொல்லுங்கள்."
                    elif lang == "kn":
                        reply = f"ಧನ್ಯವಾದಗಳು. ನಮಸ್ಕಾರ {cust_name} ಅವರೇ! ನೀವು ನಿಮ್ಮ ಐಸ್ ಮೇಕ್ {prod_name} ಕುರಿತು ಕರೆ ಮಾಡುತ್ತಿದ್ದೀರಿ ಎಂದು ನಾವು ನೋಡಬಹುದು. ದಯವಿಟ್ಟು ನಿಮ್ಮ ಸಮಸ್ಯೆಯನ್ನು ವಿವರವಾಗಿ ಹೇಳಿ."
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
                    elif lang == "pa":
                        reply = f"ਧੰਨਵਾਦ। ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ {cust_name} ਜੀ! ਤੁਸੀਂ ਆਈਸ ਮੇਕ ਦਾ ਕਿਹੜਾ ਪ੍ਰੋਡਕਟ ਵਰਤ ਰਹੇ ਹੋ?"
                    elif lang == "bn":
                        reply = f"ধন্যবাদ। নমস্কার {cust_name} জি! আপনি আইস মেকের কোন প্রোডাক্টটি ব্যবহার করছেন?"
                    elif lang == "mr":
                        reply = f"धन्यवाद. नमस्कार {cust_name} जी! तुम्ही आईस मेकचे कोणते उत्पादन वापरत आहात?"
                    elif lang == "ta":
                        reply = f"நன்றி. வணக்கம் {cust_name} அவர்களே! நீங்கள் எந்த ஐஸ் மேக் தயாரிப்பைப் பயன்படுத்துகிறீர்கள்?"
                    elif lang == "kn":
                        reply = f"ಧನ್ಯವಾದಗಳು. ನಮസ്ಕಾರ {cust_name} ಅವರೇ! ನೀವು ಐಸ್ ಮೇಕ್‌ನ ಯಾವ ಉತ್ಪನ್ನವನ್ನು ಬಳಸುತ್ತಿದ್ದೀರಿ?"
                    elif lang == "ml":
                        reply = f"നന്ദി. നമസ്കാരം {cust_name} ജി! നിങ്ങൾ ഐസ് മേക്കിന്റെ ഏത് പ്രൊഡക്റ്റാണ് ഉപയോഗിക്കുന്നത്?"
                    else:
                        reply = f"Thank you. Welcome Mr. {cust_name}! Which Ice Make product are you using?"
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
    
    # ── OUT-OF-FLOW INTERCEPTION ──
    out_of_flow_res = _check_and_handle_out_of_flow(raw_message, lang, prev_step, session, state, mode=mode)
    if out_of_flow_res:
        return out_of_flow_res

    state["conversation_history"].append(f"User: {raw_message}")
    _log_translator(raw_message, None, lang)

    # ── STEP 1: Process Customer Name ──
    if prev_step == 1:
        clean_name = _extract_person_name(raw_message, lang)
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
            elif lang == "pa":
                reply = "ਤੁਹਾਡੇ ਨਾਲ ਗੱਲ ਕਰਕੇ ਬਹੁਤ ਖੁਸ਼ੀ ਹੋਈ! ਤੁਹਾਡੀ ਬਿਹਤਰ ਮਦਦ ਲਈ, ਕੀ ਤੁਸੀਂ ਦੱਸ ਸਕਦੇ ਹੋ ਕਿ ਤੁਸੀਂ ਕਿਸ ਸੂਬੇ ਤੋਂ ਫ਼ੋਨ ਕਰ ਰਹੇ ਹੋ?"
            elif lang == "bn":
                reply = "আপনার সাথে কথা বলে খুব ভালো লাগলো! আপনাকে সাহায্য করতে, দয়া করে বলবেন আপনি কোন রাজ্য থেকে ফোন করছেন?"
            elif lang == "mr":
                reply = "तुमच्याशी बोलून खूप आनंद झाला! तुम्हाला उत्तम मदत करण्यासाठी, तुम्ही कोणत्या राज्यातून बोलत आहात ते सांगू शकाल का?"
            elif lang == "ta":
                reply = "உங்களுடன் பேசுவதில் மிக்க மகிழ்ச்சி! உங்களுக்கு சிறந்த உதவி செய்வதற்கு, நீங்கள் எந்த மாநிலத்திலிருந்து அழைக்கிறீர்கள் என்று சொல்ல முடியுமா?"
            elif lang == "kn":
                reply = "ನಿಮ್ಮೊಂದಿಗೆ ಮಾತನಾಡಲು ತುಂಬಾ ಸಂತೋಷವಾಗಿದೆ! ನಿಮಗೆ ಉತ್ತಮವಾಗಿ ಸಹಾಯ ಮಾಡಲು, ನೀವು ಯಾವ ರಾಜ್ಯದಿಂದ ಕರೆ ಮಾಡುತ್ತಿದ್ದೀರಿ ಎಂದು ಹೇಳಬಹುದೇ?"
            elif lang == "ml":
                reply = "നിങ്ങളോട് സംസാരിക്കാൻ സാധിച്ചതിൽ സന്തോഷം! മികച്ച സേവനം നൽകുന്നതിനായി, ഏത് സംസ്ഥാനത്തു നിന്നാണ് വിളിക്കുന്നതെന്ന് പറയാമോ?"
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
        pincode_extracted = _extract_pincode_ai(raw_message, lang)
        
        pin_patterns = [
            r'\b(pin|pincode|pin code)\b',
            r'पिन\s*कोड', r'पिन',           # Hindi / Marathi Devanagari
            r'પિન\s*કોડ', r'પિન',           # Gujarati
            r'পিন\s*কোড', r'পিন',           # Bengali
            r'பின்கோடு', r'பின்\s*கோடு',    # Tamil
            r'పిన్‌కోడ్', r'పిన్\s*కోడ్',    # Telugu
            r'പിൻകോഡ്', r'പിൻ\s*കോഡ്',    # Malayalam
            r'ಪಿನ್‌ಕೋಡ್', r'ಪಿನ್\s*ಕೋಡ್',    # Kannada
            r'ਪਿੰਨਕੋਡ', r'ਪਿੰਨ\s*ਕੋਡ'       # Punjabi
        ]
        has_pin_keyword = any(re.search(p, raw_message, re.IGNORECASE) for p in pin_patterns)

        mapped_msg = _map_regional_digits_to_ascii(raw_message)
        digit_matches = re.findall(r'\b\d+\b', mapped_msg)

        invalid_pincode_attempt = False
        if pincode_extracted:
            state["pin_code"] = pincode_extracted
            state["pincode"] = pincode_extracted
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
            elif lang == "pa":
                reply = "ਤੁਹਾਡਾ ਪਿੰਨਕੋਡ ਗਲਤ ਲੱਗਦਾ ਹੈ। ਪਿੰਨਕੋਡ 6 ਅੰਕਾਂ ਦਾ ਹੋਣਾ ਚਾਹੀਦਾ ਹੈ। ਕਿਰਪਾ ਕਰਕੇ ਆਪਣਾ 6 ਅੰਕਾਂ ਦਾ ਪਿੰਨਕੋਡ ਜਾਂ ਪਤਾ ਦੁਬਾਰਾ ਦੱਸੋ।"
            elif lang == "bn":
                reply = "আপনার পিনকোডটি ভুল মনে হচ্ছে। পিনকোড ৬ ডিজিটের হতে হবে। দয়া করে আপনার ৬ ডিজিটের পিনকোড বা ঠিকানা পুনরায় বলুন।"
            elif lang == "mr":
                reply = "तुमचा पिनकोड अमान्य वाटत आहे. पिनकोड ६ अंकांचा असावा. कृपया तुमचा ६ अंकांचा पिनकोड किंवा पत्ता पुन्हा सांगा."
            elif lang == "ta":
                reply = "உங்கள் பின்கோடு சரியில்லை என்று தெரிகிறது. பின்கோடு ஆறு இலக்கமாக இருக்க வேண்டும். தயவுசெய்து உங்கள் ஆறு இலக்க பின்கோடு அல்லது முகவரியை மீண்டும் சொல்லுங்கள்."
            elif lang == "kn":
                reply = "ನಿಮ್ಮ ಪಿನ್‌ಕೋಡ್ ತಪ್ಪಾಗಿದೆ ಎಂದು ತೋರುತ್ತದೆ. ಪಿನ್‌ಕೋಡ್ 6 ಅಂಕಿಗಳಿರಬೇಕು. ದಯವಿಟ್ಟು ನಿಮ್ಮ 6 ಅಂಕಿಗಳ ಪಿನ್‌ಕೋಡ್ ಅಥವಾ ವಿಳಾಸವನ್ನು ಮತ್ತೆ ಹೇಳಿ."
            elif lang == "ml":
                reply = "നിങ്ങളുടെ പിൻകോഡ് തെറ്റാണെന്ന് തോന്നുന്നു. പിൻകോഡ് 6 അക്കമുള്ളതായിരിക്കണം. ദയവായി നിങ്ങളുടെ 6 അക്ക പിൻകോഡും വിലാസവും വീണ്ടും പറയൂ."
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
                state["current_step"] = 4
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
            if lang == "hi":
                reply = "आपका नंबर अमान्य लग रहा है। कृपया अपना 10 अंकों का मोबाइल नंबर फिर से बताइए।"
            elif lang == "gu":
                reply = "તમારો નંબર અમાન્ય લાગે છે. કૃપા કરીને તમારો દસ અંકનો મોબાઈલ નંબર ફરીથી જણાવો."
            elif lang == "te":
                reply = "మీ నంబర్ సరిగ్గా లేదు. దయచేసి మీ 10 అంకెల మొబైల్ నంబర్‌ను మళ్లీ చెప్పండి."
            elif lang == "pa":
                reply = "ਤੁਹਾਡਾ ਨੰਬਰ ਗਲਤ ਲੱਗਦਾ ਹੈ। ਕਿਰਪਾ ਕਰਕੇ ਆਪਣਾ 10 ਅੰਕਾਂ ਦਾ ਮੋਬਾਈਲ ਨੰਬਰ ਦੁਬਾਰਾ ਦੱਸੋ।"
            elif lang == "bn":
                reply = "আপনার নম্বরটি ভুল মনে হচ্ছে। দয়া করে আপনার ১০ ডিজিটের মোবাইল নম্বরটি পুনরায় বলুন।"
            elif lang == "mr":
                reply = "तुमचा नंबर अमान्य वाटत आहे. कृपया तुमचा १० अंकांचा मोबाईल नंबर पुन्हा सांगा।"
            elif lang == "ta":
                reply = "உங்கள் எண் சரியில்லை என்று தெரிகிறது. தயவுசெய்து உங்கள் பத்து இலக்க மொபைல் எண்ணை மீண்டும் சொல்லுங்கள்."
            elif lang == "kn":
                reply = "ನಿಮ್ಮ ಸಂಖ್ಯೆ ತಪ್ಪಾಗಿದೆ ಎಂದು ತೋರುತ್ತದೆ. ದಯವಿಟ್ಟು ನಿಮ್ಮ 10 ಅಂಕಿಗಳ ಮೊಬೈಲ್ ಸಂಖ್ಯೆಯನ್ನು ಮತ್ತೆ ಹೇಳಿ."
            elif lang == "ml":
                reply = "നിങ്ങളുടെ നമ്പർ തെറ്റാണെന്ന് തോന്നുന്നു. ദയവായി നിങ്ങളുടെ 10 അക്ക മൊബൈൽ നമ്പർ വീണ്ടും പറയൂ."
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
            phone_num = valid_phone
            state["registered_mobile"] = phone_num
            state.pop("partial_phone_digits", None)
            next_step = 5
            spoken_num = _format_spoken_number(phone_num, lang)
            if lang == "hi":
                reply = f"धन्यवाद, मैंने आपका नंबर {spoken_num} दर्ज किया है। क्या आप पुष्टि कर सकते हैं कि यह आपका रजिस्टर्ड नंबर है?"
            elif lang == "gu":
                reply = f"આભાર, મેં તમારો નંબર {spoken_num} નોંધ્યો છે. શું તમે પુષ્ટિ કરી શકો છો કે આ તમારો રજિસ્ટર્ડ નંબર છે?"
            elif lang == "te":
                reply = f"ధన్యవాదాలు, నేను మీ నంబర్‌ను {spoken_num} గా నమోదు చేసాను. ఇది మీ రిజిస్టర్డ్ నంబర్ అని ధృవీకరిస్తారా?"
            elif lang == "pa":
                reply = f"ਧੰਨਵਾਦ, ਮੈਂ ਤੁਹਾਡਾ ਨੰਬਰ {spoken_num} ਦਰਜ ਕੀਤਾ ਹੈ। ਕੀ ਤੁਸੀਂ ਪੁਸ਼ਟੀ ਕਰ ਸਕਦੇ ਹੋ ਕਿ ਇਹ ਤੁਹਾਡਾ ਰਜਿਸਟਰਡ ਨੰਬਰ ਹੈ?"
            elif lang == "bn":
                reply = f"ধন্যবাদ, আমি আপনার নম্বরটি {spoken_num} হিসেবে নোট করেছি। আপনি কি নিশ্চিত করতে পারেন এটি আপনার রেজিস্টার্ড নম্বর?"
            elif lang == "mr":
                reply = f"धन्यवाद, मी तुमचा नंबर {spoken_num} म्हणून नोंदवला आहे. हा तुमचा नोंदणीकृत नंबर आहे याची तुम्ही खात्री करू शकता का?"
            elif lang == "ta":
                reply = f"நன்றி, நான் உங்கள் எண்ணை {spoken_num} என்று பதிவு செய்துள்ளேன். இது உங்கள் பதிவு செய்யப்பட்ட எண் என்று உறுதிப்படுத்த முடியுமா?"
            elif lang == "kn":
                reply = f"ಧನ್ಯವಾದಗಳು, ನಾನು ನಿಮ್ಮ ಸಂಖ್ಯೆಯನ್ನು {spoken_num} ಎಂದು ದಾಖಲಿಸಿದ್ದೇನೆ. ಇದು ನಿಮ್ಮ ನೋಂದಾಯಿತ ಸಂಖ್ಯೆ ಎಂದು ದೃಢೀಕರಿಸಬಹುದೇ?"
            elif lang == "ml":
                reply = f"നന്ദി, ഞാൻ നിങ്ങളുടെ നമ്പർ {spoken_num} എന്ന് രേഖപ്പെടുത്തിയിട്ടുണ്ട്. ഇത് നിങ്ങളുടെ രജിസ്റ്റർ ചെയ്ത നമ്പറാണെന്ന് സ്ഥിരീകരിക്കാമോ?"
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
            elif lang == "pa":
                reply = "ਧੰਨਵਾਦ! ਤੁਸੀਂ ਆਈਸ ਮੇਕ ਦਾ ਕਿਹੜਾ ਪ੍ਰੋਡਕਟ ਵਰਤ ਰਹੇ ਹੋ?"
            elif lang == "bn":
                reply = "ধন্যবাদ! আপনি আইস মেকের কোন প্রোডাক্টটি ব্যবহার করছেন?"
            elif lang == "mr":
                reply = "धन्यवाद! तुम्ही आईस मेकचे कोणते उत्पादन वापरत आहात?"
            elif lang == "ta":
                reply = "நன்றி! நீங்கள் எந்த ஐஸ் மேக் தயாரிப்பைப் பயன்படுத்துகிறீர்கள்?"
            elif lang == "kn":
                reply = "ಧನ್ಯವಾದಗಳು! ನೀವು ಐಸ್ ಮೇಕ್‌ನ ಯಾವ ಉತ್ಪನ್ನವನ್ನು ಬಳಸುತ್ತಿದ್ದೀರಿ?"
            elif lang == "ml":
                reply = "നന്ദി! നിങ്ങൾ ഐസ് മേക്കിന്റെ ഏത് പ്രൊഡക്റ്റാണ് ഉപയോഗിക്കുന്നത്?"
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
        elif lang == "pa":
            reply = "ਠੀਕ ਹੈ। ਕਿਰਪਾ ਕਰਕੇ ਆਪਣੀ ਸਮੱਸਿਆ ਵਿਸਥਾਰ ਨਾਲ ਦੱਸੋ। ਤੁਸੀਂ ਦੋ ਮਿੰਟ ਤੱਕ ਆਪਣੀ ਸਮੱਸਿਆ ਦੱਸ ਸਕਦੇ ਹੋ। ਇਹ ਕਾਲ ਰਿਕਾਰਡ ਕੀਤੀ ਜਾ ਰਹੀ ਹੈ ਅਤੇ ਤੁਰੰਤ ਕਾਰਵਾਈ ਲਈ ਇੰਜੀਨੀਅਰ ਨੂੰ ਭੇਜੀ ਜਾਵੇਗੀ।"
        elif lang == "bn":
            reply = "ঠিক আছে। দয়া করে আপনার সমস্যাটি বিস্তারিত বলুন। আপনি দুই মিনিট পর্যন্ত আপনার সমস্যা বলতে পারেন। এই কলটি রেকর্ড করা হচ্ছে এবং দ্রুত ব্যবস্থার জন্য ইঞ্জিনিয়ারের কাছে পাঠানো হবে।"
        elif lang == "mr":
            reply = "ठीक आहे. कृपया तुमची समस्या सविस्तर सांगा. तुम्ही दोन मिनिटांपर्यंत तुमची समस्या सांगू शकता. हा कॉल रेकॉर्ड केला जात आहे आणि त्वरित कारवाईसाठी इंजिनिअरकडे पाठवला जाईल."
        elif lang == "ta":
            reply = "சரி. தயவுசெய்து நீங்கள் எதிர்கொள்ளும் பிரச்சனையை விரிவாக சொல்லுங்கள். நீங்கள் இரண்டு நிமிடங்கள் வரை உங்கள் பிரச்சனையை சொல்லலாம். இந்த அழைப்பு பதிவு செய்யப்படுகிறது மற்றும் உடனடி நடவடிக்கைக்காக பொறியாளரிடம் அனுப்பப்படும்."
        elif lang == "kn":
            reply = "ಸರಿ. ದಯವಿಟ್ಟು ನಿಮ್ಮ ಸಮಸ್ಯೆಯನ್ನು ವಿವರವಾಗಿ ಹೇಳಿ. ನಿಮ್ಮ ಸಮಸ್ಯೆಯನ್ನು ನೀವು ಎರಡು ನಿಮಿಷಗಳವರೆಗೆ ಹೇಳಬಹುದು. ಈ ಕರೆಯನ್ನು ರೆಕಾರ್ಡ್ ಮಾಡಲಾಗುತ್ತಿದೆ ಮತ್ತು ತಕ್ಷಣದ ಕ್ರಮಕ್ಕಾಗಿ ಇಂಜಿನಿಯರ್‌ಗೆ ಕಳುಹಿಸಲಾಗುತ್ತದೆ."
        elif lang == "ml":
            reply = "ശരി. ദയവായി നിങ്ങളുടെ പ്രശ്നം വിശദമായി പറയൂ. രണ്ട് മിനിറ്റ് വരെ നിങ്ങളുടെ പ്രശ്നം വിവരിക്കാം. ഈ കോൾ റെക്കോർഡ് ചെയ്യപ്പെടുന്നുണ്ട്, ഉടൻ നടപടിക്കായി എഞ്ചിനീയർക്ക് കൈമാറുന്നതാണ്."
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
        elif lang == "pa":
            reply = (
                f"ਧੰਨਵਾਦ, ਮੈਂ ਤੁਹਾਡੀ ਸਮੱਸਿਆ ਨੋਟ ਕਰ ਲਈ ਹੈ। "
                f"ਆਈਸ ਮੇਕ 24 ਬਾਈ 7 ਸਰਵਿਸ ਸਪੋਰਟ ਨਾਲ ਸੰਪਰਕ ਕਰਨ ਲਈ ਧੰਨਵਾਦ। "
                f"ਤੁਹਾਡੀ ਸ਼ਿਕਾਇਤ ਦਰਜ ਕਰ ਲਈ ਗਈ ਹੈ ਅਤੇ ਤੁਹਾਡਾ ਸ਼ਿਕਾਇਤ ਨੰਬਰ {spoken_ticket} ਹੈ। ਤੁਹਾਨੂੰ ਆਪਣੇ ਵਟਸਐਪ 'ਤੇ ਜਾਣਕਾਰੀ ਮਿਲ ਜਾਵੇਗੀ। "
                f"ਸਾਡੀ ਸਰਵਿਸ ਟੀਮ ਤੁਹਾਡੀ ਸ਼ਿਕਾਇਤ ਦੀ ਸਮੀਖਿਆ ਕਰੇਗੀ ਅਤੇ ਅੱਗੇ ਤੁਹਾਡੀ ਮਦਦ ਕਰੇਗੀ। ਤੁਹਾਡਾ ਦਿਨ ਸ਼ੁਭ ਹੋਵੇ। [FLOW_COMPLETE]"
            )
        elif lang == "bn":
            reply = (
                f"ধন্যবাদ, আমি আপনার সমস্যাটি নোট করেছি। "
                f"আইস মেক ২৪/৭ সার্ভিস সাপোর্টে যোগাযোগ করার জন্য ধন্যবাদ। "
                f"আপনার অভিযোগটি নিবন্ধিত হয়েছে এবং আপনার অভিযোগ নম্বর হলো {spoken_ticket}। আপনি আপনার হোয়াটসঅ্যাপে বিস্তারিত তথ্য পেয়ে যাবেন। "
                f"আমাদের সার্ভিস টিম আপনার অভিযোগ পরীক্ষা করবে এবং আপনাকে সাহায্য করবে। আপনার দিনটি শুভ হোক। [FLOW_COMPLETE]"
            )
        elif lang == "mr":
            reply = (
                f"धन्यवाद, मी तुमची समस्या नोंदवून घेतली आहे. "
                f"आईस मेक २४/७ सर्व्हिस सपोर्टशी संपर्क साधल्याबद्दल धन्यवाद. "
                f"तुमची तक्रार नोंदवली गेली आहे आणि तुमचा तक्रार क्रमांक {spoken_ticket} हा आहे. तुम्हाला तुमच्या व्हॉट्सॲपवर माहिती मिळेल. "
                f"आमची सर्व्हिस टीम तुमच्या तक्रारीचे पुनरावलोकन करेल आणि पुढे तुम्हाला मदत करेल. तुमचा दिवस शुभ जावो. [FLOW_COMPLETE]"
            )
        elif lang == "ta":
            reply = (
                f"நன்றி, நான் உங்கள் பிரச்சனையை குறித்துக் கொண்டேன். "
                f"ஐஸ் மேக் இருபத்தி நான்கு மணி நேர சேவை ஆதரவை தொடர்பு கொண்டதற்கு நன்றி. "
                f"உங்கள் புகார் பதிவு செய்யப்பட்டுள்ளது மற்றும் உங்கள் புகார் எண் {spoken_ticket} ஆகும். உங்கள் வாட்ஸ்அப்பில் விவரங்கள் கிடைக்கும். "
                f"எங்கள் சேவை குழு உங்கள் புகாரை மதிப்பாய்வு செய்து மேலும் உங்களுக்கு உதவும். உங்கள் நாள் நல்லதாக இருக்கட்டும். [FLOW_COMPLETE]"
            )
        elif lang == "kn":
            reply = (
                f"ಧನ್ಯವಾದಗಳು, ನಾನು ನಿಮ್ಮ ಸಮಸ್ಯೆಯನ್ನು ಟಿಪ್ಪಣಿ ಮಾಡಿಕೊಂಡಿದ್ದೇನೆ. "
                f"ಐಸ್ ಮೇಕ್ ಇಪ್ಪತ್ತನಾಲ್ಕು ಗಂಟೆಗಳ ಸೇವಾ ಬೆಂಬಲವನ್ನು ಸಂಪರ್ಕಿಸಿದ್ದಕ್ಕಾಗಿ ಧನ್ಯವಾದಗಳು. "
                f"ನಿಮ್ಮ ದೂರು ನೋಂದಾಯಿಸಲ್ಪಟ್ಟಿದೆ ಮತ್ತು ನಿಮ್ಮ ದೂರು ಸಂಖ್ಯೆ {spoken_ticket} ಆಗಿದೆ. ನಿಮ್ಮ ವಾಟ್ಸಾಪ್‌ನಲ್ಲಿ ನೀವು ವಿವರಗಳನ್ನು ಪಡೆಯುತ್ತೀರಿ. "
                f"ನಮ್ಮ ಸೇವಾ ತಂಡವು ನಿಮ್ಮ ದೂರನ್ನು ಪರಿಶೀಲಿಸುತ್ತದೆ ಮತ್ತು ನಿಮಗೆ ಮತ್ತಷ್ಟು ಸಹಾಯ ಮಾಡುತ್ತದೆ. ಶುಭ ದಿನ. [FLOW_COMPLETE]"
            )
        elif lang == "ml":
            reply = (
                f"നന്ദി, ഞാൻ നിങ്ങളുടെ പ്രശ്നം കുറിച്ചെടുത്തിട്ടുണ്ട്. "
                f"ഐസ് മേക്ക് 24/7 സർവീസ് സപ്പോർട്ടിലേക്ക് ബന്ധപ്പെട്ടതിന് നന്ദി. "
                f"നിങ്ങളുടെ പരാതി രജിസ്റ്റർ ചെയ്തു, പരാതി നമ്പർ {spoken_ticket} ആകുന്നു. വിവരങ്ങൾ വാട്ട്സാപ്പിൽ ലഭിക്കുന്നതാണ്. "
                f"ഞങ്ങളുടെ സർവീസ് ടീം നിങ്ങളുടെ പരാതി പരിശോധിക്കുകയും തുടർന്ന് സഹായിക്കുകയും ചെയ്യും. നല്ലൊരു ദിവസം ആശംസിക്കുന്നു. [FLOW_COMPLETE]"
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
    (in Hindi, Hinglish, Gujarati, Telugu, Punjabi, Bengali, Marathi, Malayalam, or English) into clean, proper English string values for the Google Sheet.
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
You are an expert Refrigeration Engineering & CRM Data Extraction Assistant for Ice Make Refrigeration Ltd.
Analyze the customer's raw problem description carefully. Speech Recognition (STT) input might be noisy, phonetically garbled, informal, or in any regional language (Hindi, Gujarati, Tamil, Telugu, Marathi, Punjabi, Malayalam, Bengali, Kannada, English).

Your job is to INTELLIGENTLY identify the underlying technical refrigeration issue, repair any speech recognition errors, and map it into standardized technical terminology.

Raw Inputs:
- Customer Name Raw: "{raw_name}"
- State Raw: "{raw_state}"
- City Raw: "{raw_city}"
- Address/Company Raw: "{raw_address}"
- Product Name Raw: "{raw_product}"
- Issue Description Raw: "{raw_issue}"

Rules:
1. "customer_name": Extract ONLY the person's name in Title Case English (e.g., "Harshil Mehta").
2. "state": Extract ONLY the Indian state name in English (e.g., "Gujarat").
3. "city": Extract ONLY the city/area name in English Title Case (e.g., "Ahmedabad").
4. "address": Extract ONLY the company or address name (including 6-digit pincode if provided) in English Title Case.
5. "machine_model_no": Extract ONLY the clean product/machine name in English Title Case (e.g., "Blast Freezer", "Chiller", "Cold Storage Room", "Freezer", "Ice Plant").
6. "issue_type": INTELLIGENTLY classify the root technical issue into EXACTLY ONE of these standard categories:
   - "No Cooling / Insufficient Cooling" (for cooling failure, temperature not dropping, thandak nahi hona, thandak kam hona)
   - "Abnormal Noise & Vibration" (for loud noise, sound in compressor, fan noise, vibration)
   - "Gas Leakage / Low Pressure" (for gas leakage, pressure loss, gas kam hona)
   - "Electrical / Tripping Fault" (for machine tripping, power issue, current, MCB trip, not turning on)
   - "Water Leakage / Defrost Fault" (for water leaking, excessive ice accumulation, frosting issue)
   - "Temperature Sensor Error" (for display error, sensor fault, temperature indicator issue)
   - "General Maintenance / Service" (for routine checkup, general service, or unspecified issue)
7. "type_of_complaint": Formulate ONE clear, professional, grammatically correct English sentence summarizing the exact issue clearly, fixing any STT misrecognitions or informal phrasing (e.g., "thandak nahi ho raha" -> "Equipment is not cooling properly and temperature is failing to drop", "compressor sound kar raha hai" -> "Compressor is generating abnormal loud noise during operation").

Return ONLY a valid JSON object with keys:
{{"customer_name": "...", "state": "...", "city": "...", "address": "...", "machine_model_no": "...", "issue_type": "...", "type_of_complaint": "..."}}
"""

    try:
        response = client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are an expert refrigeration engineering entity extraction assistant for CRM data entry."},
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
            "issue_type": "No Cooling / Insufficient Cooling",
            "type_of_complaint": _clean_conversational_text(raw_issue)
        }

def _extract_person_name(raw_message: str, lang: str = "en") -> str:
    """
    Smart 2-tier name extraction system across all 10 supported languages:
    Tier 1: Fast regex-based cleaning via _clean_conversational_text.
    Tier 2: AI LLM entity extraction for complex/natural multi-word sentences to isolate ONLY the exact person name.
    """
    if not raw_message or not raw_message.strip():
        return "Not Provided"

    cleaned = _clean_conversational_text(raw_message)
    words = cleaned.split()

    # Tier 1 check: If response is 1 to 3 words (<= 25 chars) without conversational verbs/filler, use cleaned directly
    is_simple = len(words) <= 3 and len(cleaned) <= 25 and not any(
        w in cleaned.lower() for w in [
            "bol", "rha", "rhi", "hu", "chhe", "ahe", "call", "baat", "karni",
            "janna", "chahiy", "chhi", "aanu", "peru", "naam", "name", "state", "city",
            "cold", "storage", "freezer", "chiller", "ice", "make"
        ]
    )

    if is_simple and cleaned and cleaned != "Not Provided":
        return cleaned

    # Tier 2: AI LLM Extraction for complex conversational responses across all 10 languages
    try:
        from conversations.services.azure_openai_service import client
        from django.conf import settings

        prompt = f"""
Extract ONLY the caller's actual person name from this user utterance in any language (Hindi, Gujarati, English, Marathi, Punjabi, Bengali, Telugu, Tamil, Kannada, Malayalam).

Rules:
- Return ONLY the person's real name (e.g., "Harshil Mehta", "Yash Patel", "Vishnu", "Gurpreet Singh", "तक्ष", "હર્ષિલ").
- Do NOT include conversational words, location, city, state, or product terms.
- If the user did NOT state their name or gave a non-name answer (e.g. "Hello", "Gujarat se hu"), return "Not Provided".

User Utterance: "{raw_message}"
Name:"""

        response = client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are an expert name extraction assistant for multi-lingual voice calls."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=20
        )
        ai_name = response.choices[0].message.content.strip().strip('"').strip("'").strip(".")
        if ai_name and ai_name.lower() not in ["not provided", "none", "unknown", "n/a", "no name", "not mentioned"]:
            return ai_name
    except Exception as e:
        logger.warning("AI Name Extraction notice: %s", e)

    return cleaned if cleaned else "Not Provided"

def _map_regional_digits_to_ascii(text: str) -> str:
    """Converts any regional script digits (Devanagari, Gujarati, Bengali, Gurmukhi, Tamil, Telugu, Kannada, Malayalam) in string to ASCII '0'-'9'."""
    if not text:
        return ""
    regional_digit_map = {
        '०': '0', '१': '1', '२': '2', '३': '3', '४': '4', '५': '5', '६': '6', '७': '7', '८': '8', '९': '9',
        '૦': '0', '૧': '1', '૨': '2', '૩': '3', '૪': '4', '૫': '5', '૬': '6', '૭': '7', '૮': '8', '૯': '9',
        '০': '0', '১': '1', '২': '2', '৩': '3', '৪': '4', '৫': '5', '৬': '6', '৭': '7', '৮': '8', '৯': '9',
        '੦': '0', '੧': '1', '੨': '2', '੩': '3', '੪': '4', '੫': '5', '੬': '6', '੭': '7', '੮': '8', '੯': '9',
        '௦': '0', '௧': '1', '௨': '2', '௩': '3', '௪': '4', '௫': '5', '௬': '6', '௭': '7', '௮': '8', '௯': '9',
        '౦': '0', '౧': '1', '౨': '2', '౩': '3', '౪': '4', '౫': '5', '౬': '6', '౭': '7', '౮': '8', '౯': '9',
        '೦': '0', '೧': '1', '೨': '2', '೩': '3', '೪': '4', '೫': '5', '೬': '6', '೭': '7', '೮': '8', '೯': '9',
        '൦': '0', '൧': '1', '൨': '2', '൩': '3', '൪': '4', '൫': '5', '൬': '6', '൭': '7', '൮': '8', '൯': '9'
    }
    return "".join(regional_digit_map.get(ch, ch) for ch in text)

def _convert_all_spoken_numbers_to_digits(text: str, lang: str = "en") -> str:
    """
    Converts spoken number words (single digits, double digits/tens, compound numbers, and regional script digits)
    across all supported languages (Hindi, Gujarati, Marathi, Tamil, Telugu, Punjabi, Malayalam, Bengali, Kannada, English)
    into pure ASCII digits ('0'-'9').
    """
    if not text or not text.strip():
        return text

    # Step 1: Convert regional script digits to ASCII digits
    text = _map_regional_digits_to_ascii(text)

    # Step 2: Comprehensive Dictionary of Spoken Number Words -> ASCII Digits
    spoken_num_map = {
        # --- ENGLISH / HINGLISH ---
        "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
        "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
        "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13", "fourteen": "14",
        "fifteen": "15", "sixteen": "16", "seventeen": "17", "eighteen": "18", "nineteen": "19",
        "twenty": "20", "thirty": "30", "forty": "40", "fifty": "50",
        "sixty": "60", "seventy": "70", "eighty": "80", "ninety": "90",
        "hundred": "100", "thousand": "1000",

        # --- HINDI / DEVANAGARI / HINGLISH ---
        "शून्य": "0", "जीरो": "0", "ज़ीरो": "0", "एक": "1", "दो": "2", "तीन": "3",
        "चार": "4", "पांच": "5", "पाँच": "5", "छह": "6", "छः": "6", "सात": "7",
        "आठ": "8", "नौ": "9", "दस": "10", "ग्यारह": "11", "बारह": "12",
        "तेरह": "13", "चौदह": "14", "पंद्रह": "15", "सोलह": "16", "सत्रह": "17",
        "अठारह": "18", "उम्मीद": "19", "उन्नीस": "19", "बीस": "20", "तीस": "30",
        "चालिस": "40", "चालीस": "40", "पचास": "50", "साठ": "60", "सत्तर": "70",
        "अस्सी": "80", "नब्बे": "90", "सौ": "100", "हजार": "1000",

        # Phonetic English numbers transcribed in Devanagari STT
        "वन": "1", "टू": "2", "टु": "2", "थ्री": "3", "त्रि": "3", "फोर": "4",
        "फाइव": "5", "फ़ाइव": "5", "सिक्स": "6", "सेवन": "7", "एट": "8", "एइट": "8", "ऐट": "8", "नाइन": "9", "टेन": "10",

        # Hindi Compounds (90-99)
        "इक्यानवे": "91", "बान्वे": "92", "तिरान्वे": "93", "चौरान्वे": "94",
        "पचान्वे": "95", "छियान्वे": "96", "सत्तन्वे": "97", "अठान्वे": "98", "निन्यानवे": "99",

        # --- GUJARATI ---
        "શૂન્ય": "0", "ઝીરો": "0", "એક": "1", "બે": "2", "ત્રણ": "3",
        "ચાર": "4", "પાંચ": "5", "છ": "6", "સાત": "7", "આઠ": "8", "નવ": "9", "નવમું": "9",
        "દસ": "10", "અગિયાર": "11", "બાર": "12", "તેર": "13", "ચૌદ": "14",
        "પંદર": "15", "સોળ": "16", "સત્તર": "17", "અઢાર": "18", "ઓગણીસ": "19",
        "વીસ": "20", "ત્રીસ": "30", "ચાલીસ": "40", "પચાસ": "50", "સાઠ": "60",
        "સિત્તેર": "70", "એંસી": "80", "એસી": "80", "નેવુ": "90", "સો": "100", "હજાર": "1000",

        # Phonetic English numbers transcribed in Gujarati STT
        "વન": "1", "ટુ": "2", "થ્રી": "3", "ફોર": "4", "ફાઇવ": "5", "ફાઈવ": "5",
        "સિક્સ": "6", "સેવન": "7", "એઇટ": "8", "નાઇન": "9", "નાઈન": "9", "ટેન": "10",

        # Gujarati Compounds & Words
        "એકાણું": "91", "બાણું": "92", "ત્રાણું": "93", "ચોરાણું": "94",
        "પંચાણું": "95", "છિન્નાણું": "96", "સત્તાણું": "97", "અઠ્ઠાણું": "98", "નવ્વાણું": "99",
        "ચારસો": "400", "બેસો": "200", "ત્રણસો": "300", "પાંચસો": "500",

        # --- MARATHI ---
        "शून्य": "0", "एक": "1", "दोन": "2", "तीन": "3", "चार": "4",
        "पाच": "5", "सहा": "6", "सात": "7", "आठ": "8", "नऊ": "9", "दहा": "10",

        # --- TAMIL ---
        "பூஜ்ஜியம்": "0", "ஒன்று": "1", "இரண்டு": "2", "மூன்று": "3", "நான்கு": "4",
        "ஐந்து": "5", "ஆறு": "6", "ஏழு": "7", "எட்டு": "8", "ஒன்பது": "9", "பத்து": "10",

        # --- TELUGU ---
        "సున్నా": "0", "ఒకటి": "1", "రెండు": "2", "మూడు": "3", "నాలుగు": "4",
        "ఐదు": "5", "ఆరు": "6", "ఏడు": "7", "ఎనిమిది": "8", "తొమ్മിది": "9", "పది": "10",

        # --- PUNJABI ---
        "ਸਿਫ਼ਰ": "0", "ਜ਼ੀਰੋ": "0", "ਇੱਕ": "1", "ਦੋ": "2", "ਤਿੰਨ": "3", "ਚਾਰ": "4",
        "ਪੰਜ": "5", "ਛੇ": "6", "ਸੱਤ": "7", "ਅੱਠ": "8", "ਨੌਂ": "9", "ਦੱਸ": "10",

        # --- BENGALI ---
        "শূন্য": "0", "এক": "1", "দুই": "2", "তিন": "3", "চার": "4",
        "পাঁচ": "5", "ছয়": "6", "সাত": "7", "আট": "8", "নয়": "9", "দশ": "10",

        # --- KANNADA ---
        "ಶೂನ್ಯ": "0", "ಒಂದು": "1", "ಎರಡು": "2", "ಮೂರು": "3", "ನಾಲ್ಕು": "4",
        "ಐದು": "5", "ಆರು": "6", "ಏಳು": "7", "ಎಂಟು": "8", "ಒಂಬತ್ತು": "9", "ಹತ್ತು": "10",

        # --- MALAYALAM ---
        "പൂജ്യം": "0", "ഒന്ന്": "1", "രണ്ട്": "2", "മൂന്ന്": "3", "നാല്": "4",
        "അഞ്ച്": "5", "ആറ്": "6", "ഏഴ്": "7", "എട്ട്": "8", "ഒൻപത്": "9", "പത്ത്": "10"
    }

    sorted_words = sorted(spoken_num_map.keys(), key=lambda x: len(x), reverse=True)
    result = text
    for w in sorted_words:
        digit_val = spoken_num_map[w]
        pattern = r'(^|\s)' + re.escape(w) + r'(?=\s|[.,!?।]|$)'
        result = re.sub(pattern, r'\g<1>' + digit_val, result, flags=re.IGNORECASE)

    return result

def _extract_pincode_ai(raw_message: str, lang: str = "en") -> str:
    """
    Intelligent 2-tier 6-digit Indian Pincode extraction system across all 10 supported languages:
    
    Tier 1: Direct ASCII / Regional Script 6-Digit Match (< 1ms)
      - Converts regional script digits (Devanagari, Gujarati, etc.) to ASCII.
      - If regex matches 6 digits, return the 6 digits immediately.

    Tier 2: AI LLM Digit & Spoken Word Pincode Extractor (Azure OpenAI)
      - Handles mixed digits and spoken words (e.g., "3824 वन एट" -> 382418, "तीन आठ दो चार एक आठ" -> 382418, "3824 એક આઠ" -> 382418).
      - Returns exact 6 ASCII digits or empty string.
    """
    if not raw_message or not raw_message.strip():
        return ""

    mapped_msg = _map_regional_digits_to_ascii(raw_message)
    six_match = re.search(r'\b\d{6}\b', mapped_msg)
    if six_match:
        return six_match.group(0)

    try:
        from conversations.services.azure_openai_service import client
        from django.conf import settings

        prompt = f"""
You are an expert multi-lingual Indian pincode converter and digit extractor.
Extract and convert the user's spoken 6-digit Indian postal pincode into EXACTLY 6 ASCII digits.

The input may contain mixed digits and spoken number words in any language (Hindi, Gujarati, Marathi, Tamil, Telugu, Punjabi, Malayalam, Bengali, Kannada, English, Hinglish).
User input examples:
- Mixed digits and phonetic words: "3824 वन एट" -> 382418; "3824 एक आठ" -> 382418; "3824 one eight" -> 382418; "38 24 18" -> 382418; "382418".
- Spoken number words: "तीन आठ दो चार एक आठ" -> 382418; "ત્રણ આઠ બે ચાર એક આઠ" -> 382418.

Rules:
- Output ONLY the 6 ASCII digits without spaces, hyphens, punctuation, or explanations (e.g., 382418).
- If no valid 6-digit Indian pincode is spoken or present, output "NONE".

User Input: "{raw_message}"
6-Digit Pincode:"""

        response = client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are an expert pincode extraction assistant for multi-lingual Indian voice calls."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=15
        )
        ai_digits = response.choices[0].message.content.strip().strip('"').strip("'")
        ai_clean_digits = "".join(filter(str.isdigit, ai_digits))
        if len(ai_clean_digits) == 6:
            return ai_clean_digits
    except Exception as e:
        logger.warning("AI Pincode Extraction notice: %s", e)

    return ""

def _extract_phone_number_ai(raw_message: str, lang: str = "en") -> str:
    """
    Intelligent 2-tier phone number extraction system across all 10 supported languages
    (Hindi, Gujarati, Marathi, Tamil, Telugu, Punjabi, Malayalam, Bengali, Kannada, English, Hinglish):
    
    Tier 1: Fast Regional Digit Character & ASCII Digit Mapping
      - Maps Unicode digits from Devanagari, Gujarati, Bengali, Gurmukhi, Tamil, Telugu, Kannada, Malayalam directly to ASCII '0'-'9'.
      - Strips spaces, dashes, commas, dots, and trailing intonation marks like '?'.
      - If mapped result contains EXACTLY 10 ASCII digits, returns immediately (< 1ms).

    Tier 2: AI LLM Digit & Spoken Word Extraction (Azure OpenAI)
      - Used when numbers are spoken as words (e.g., "नौ चार दो सात दो आठ पाँच छह पाँच तीन", "9427 બે આઠ 5653", "ஒன்பது நான்கு...", "nine four two...").
      - Returns exact 10 ASCII digits or empty string.
    """
    if not raw_message or not raw_message.strip():
        return ""

    # Tier 1: Regional Script Unicode digit mapping
    regional_digit_map = {
        '०': '0', '१': '1', '२': '2', '३': '3', '४': '4', '५': '5', '६': '6', '७': '7', '८': '8', '९': '9',  # Devanagari
        '૦': '0', '૧': '1', '૨': '2', '૩': '3', '૪': '4', '૫': '5', '૬': '6', '૭': '7', '૮': '8', '૯': '9',  # Gujarati
        '০': '0', '১': '1', '২': '2', '৩': '3', '৪': '4', '৫': '5', '৬': '6', '৭': '7', '৮': '8', '৯': '9',  # Bengali
        '੦': '0', '੧': '1', '੨': '2', '੩': '3', '੪': '4', '੫': '5', '੬': '6', '੭': '7', '੮': '8', '੯': '9',  # Gurmukhi
        '௦': '0', '௧': '1', '௨': '2', '௩': '3', '௪': '4', '௫': '5', '௬': '6', '௭': '7', '௮': '8', '௯': '9',  # Tamil
        '౦': '0', '౧': '1', '౨': '2', '౩': '3', '౪': '4', '౫': '5', '౬': '6', '౭': '7', '౮': '8', '౯': '9',  # Telugu
        '೦': '0', '೧': '1', '೨': '2', '೩': '3', '೪': '4', '೫': '5', '೬': '6', '೭': '7', '೮': '8', '೯': '9',  # Kannada
        '൦': '0', '<ctrl42>': '1', '൨': '2', '൩': '3', '൪': '4', '൫': '5', '൬': '6', '൭': '7', '൮': '8', '൯': '9'   # Malayalam
    }

    converted_chars = []
    for ch in raw_message:
        if ch in regional_digit_map:
            converted_chars.append(regional_digit_map[ch])
        elif ch.isdigit():
            converted_chars.append(ch)

    tier1_digits = "".join(converted_chars)
    if len(tier1_digits) == 10:
        return tier1_digits

    # Tier 2: AI LLM Extraction for spoken numbers or mixed words/digits across all 10 languages
    try:
        from conversations.services.azure_openai_service import client
        from django.conf import settings

        prompt = f"""
You are an expert multi-lingual Indian phone number converter and digit extractor.
Extract and convert the user's spoken 10-digit phone number into EXACTLY 10 ASCII digits.

The input may be in any language (Hindi, Gujarati, Marathi, Tamil, Telugu, Punjabi, Malayalam, Bengali, Kannada, English, Hinglish).
User input can be spoken in ANY of these formats:
1. Single digit words: e.g. "नौ चार दो सात दो आठ पाँच छह पाँच तीन", "નવ ચાર બે સાત...", "nine four two..."
2. Compound / Double-digit / Tens words: e.g., Gujarati "નવમું ઝીરો એકાણું બાણું ચારસો બે" -> 90 91 92 40 02 -> 9091924002; Hindi "नब्बे तिरानवे चौरासी साठ पंद्रह" -> 90 93 84 60 15 -> 9093846015; English "ninety-four twenty-seven twenty-eight fifty-six fifty-three" -> 9427285653.
3. Mixed digits and words: e.g., "9427 બે આઠ 5653", "9427 double zero..."

Rules:
- Translate all regional number words, compound tens/hundreds phrases, and number names into their numeric digit representation.
- Output ONLY the 10 ASCII digits without spaces, hyphens, punctuation, or explanations (e.g., 9091924002).
- If no 10-digit number can be extracted, return "NONE".

User Input: "{raw_message}"
10-Digit Number:"""

        response = client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are an expert phone number extraction assistant for multi-lingual Indian voice calls handling spoken compound and single numbers."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=20
        )
        ai_digits = response.choices[0].message.content.strip().strip('"').strip("'")
        ai_clean_digits = "".join(filter(str.isdigit, ai_digits))
        if len(ai_clean_digits) == 10:
            return ai_clean_digits
    except Exception as e:
        logger.warning("AI Phone Number Extraction notice: %s", e)

    return tier1_digits

def _check_and_handle_out_of_flow(raw_message: str, lang: str, current_step: int, session, state: dict, mode: str = "telephony") -> dict:
    """
    Detects if user utterance is an out-of-flow question/query (FAQ, repeat request, office location, products, warranty, sales inquiry).
    If yes:
      Generates ONE single, natural, cohesive response in the user's language that answers their question directly
      and smoothly transitions back to the required step detail.
    """
    if not raw_message or len(raw_message.strip()) < 3 or current_step in (0, 7, 8):
        return None

    # Guard 1: If input contains a 10-digit phone number, it's phone data for Step 4 — NEVER intercept!
    digits = _extract_phone_number_ai(raw_message, lang)
    if len(digits) == 10:
        return None

    msg_lower = raw_message.lower()
    query_triggers = [
        "kaha", "kidhar", "where", "kahan", "kaunsa", "kya", "what", "kaise", "how",
        "office", "head office", "company", "location", "factory", "gandhinagar", "ahmedabad",
        "rate", "price", "cost", "kharidna", "buy", "purchase", "new cold room", "new chiller",
        "warranty", "guarantee", "timing", "open", "time", "contact",
        "repeat", "रिपीट", "फिर से", "દુબારા", "ફરીથી", "કહ્યું", "બોલ્યા", "ક્યાં", "ક્યાં છે", "ઓફિસ", "સરનામું", "ભાવ", "કિંમત"
    ]
    
    # Require explicit question trigger words (do not trigger on Azure STT's trailing '?' alone on phone/answers)
    has_trigger_word = any(t in msg_lower for t in query_triggers)
    if not has_trigger_word:
        return None

    step_goals = {
        1: "Ask caller for their person name",
        2: "Ask caller which Indian state they are calling from",
        3: "Ask caller for their city/area address and 6-digit pincode",
        4: "Ask caller for their 10-digit mobile phone number",
        5: "Ask caller to confirm if their phone number is registered",
        6: "Ask caller which Ice Make product they are using (e.g. Blast Freezer, Chiller, Cold Storage Room)"
    }
    
    step_goal = step_goals.get(current_step, "Ask caller for their complaint details")

    cust_name = state.get("customer_name", "Not Provided")
    state_name = state.get("state_name", "Not Provided")
    company_name = state.get("company_name", "Not Provided")
    reg_mobile = state.get("registered_mobile", "Not Provided")

    try:
        from conversations.services.azure_openai_service import client
        from django.conf import settings

        prompt = f"""
You are the 24x7 AI Voice Assistant for Ice Make Refrigeration Ltd.
The user is on a live customer service call. Currently we are collecting complaint registration details.

Current Call Context:
- Step Goal: {step_goal}
- Customer Name Collected: "{cust_name}"
- State Collected: "{state_name}"
- City/Address Collected: "{company_name}"
- Phone Number Collected: "{reg_mobile}"

Ice Make Company Knowledge:
- Head Office / Factory: Dantali, GIDC, Gandhinagar - Ahmedabad Highway, Gujarat.
- Products Manufactured: Cold Storage Rooms, Blast Freezers, Chillers, Deep Freezers, Ice Plants, Dairy Equipment.
- 24x7 Service Support: Complaints registered are assigned to service engineers immediately.
- New Sales / Pricing: Sales team will connect with customer after ticket registration for quotes.

User Input: "{raw_message}"

Instructions:
1. Answer or address the user's input/question directly, politely, and accurately in language code '{lang}'.
2. Then, in the SAME response, smoothly and naturally transition to asking for the required detail for the current step ({step_goal}).
3. Do NOT include redundant opening filler words like "जी बिल्कुल धन्यवाद" or "ચોક્કસ આભાર". Make the response sound like 1 natural, cohesive, elegant sentence.

Language Code: '{lang}'
Response:"""

        response = client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are a warm, natural, helpful customer service voice agent for Ice Make Refrigeration Ltd."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=80
        )
        full_reply = response.choices[0].message.content.strip().strip('"')
        
        if not full_reply:
            return None

        if "conversation_history" not in state:
            state["conversation_history"] = []
        state["conversation_history"].append(f"User: {raw_message}")
        state["conversation_history"].append(f"Agent: {full_reply}")
        save_session(session, state)
        _log_translator(raw_message, full_reply, lang)

        return {
            "static_reply": full_reply,
            "tts_language": lang,
            "skip_output_translation": True,
            "strategy_key": STRATEGY_KEY,
            "mode": mode,
            "session": session,
            "state": state
        }
    except Exception as e:
        logger.warning("Out-of-flow query intercept notice: %s", e)
        return None

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
        
        # Marathi fillers
        r'^(माझे\s+नाव|माझं\s+नाव|नाव|माझे\s+नाव\s+आहे|मी|नमस्कार|हॅलो)\s+',
        r'\s+(आहे|आहे।|बोलतोय|बोलतेय|बोलतोय\s+मी|बोलतेय\s+मी|नाव\s+आहे)$',
        
        # Devanagari Hindi & STT Phonetic fillers (e.g. हमारा नाम, मारुना ऐम टॉक, मेरा नाम)
        r'^(हमारा\s+नाम|अमारा\s+नाम|मारुना\s+ऐम\s+टॉक|मारुना\s+ऐम|मारुना\s+एम|मेरा\s+नाम|ममेरा\s+नाम|मेरा\s+नाम\s+है|मेरा\s+नाम्|जी\s+मेरा\s+नाम|जी|मैं|मै|हेलो|हाय|नमस्ते|मारु\s+नाम|मारू\s+नाम|मैरा\s+नाम|माय\s+नेम\s+इज|माय\s+नेम|आई\s+एम|आइ\s+एम)\s+',
        r'\s+(है|हूँ|हूं|बोल\s+रहा\s+हूँ|बोल\s+रही\s+हूँ|बोल\s+रहा\s+हु|बोल\s+रही\s+हु|नाम\s+है|बोल\s+रहा\s+है|बोल\s+रही\s+है|जी|जी।)$',
        r'^(है|हूँ|हूं|टॉक|talk|talking|speaking|जी)\s+|\s+(है|हूँ|हूं|टॉक|talk|talking|speaking|जी)$',
        
        # English / Hinglish fillers
        r'^(hello|hi|hey|namaste|my\s+name\s+is|my\s+name|i\s+am|iam|this\s+is|myself|mera\s+naam|mera\s+nam|mera\s+name|me\s+hu|main\s+hu|mai\s+hu)\s+',
        r'\s+(is\s+my\s+name|speaking|here|talking|bol\s+raha\s+hu|bol\s+rahi\s+hu|baat\s+kar\s+raha\s+hu|baat\s+kar\s+rahi\s+hu)$',
        
        # Telugu fillers
        r'^(naku\s+peru|naa\s+peru|na\s+peru|peru)\s+',
        r'\s+(vachesi|andi|garu)$',

        # Malayalam fillers
        r'^(എന്റെ\s+പേര്|എന്റെ\s+പേര്\s+ആണ്|എന്റെ\s+പേരു്|പേര്|എൻറെ\s+പേര്|ഞാൻ)\s+',
        r'\s+(ആണ്|ആണു്|ആകുന്നു|പറയുന്നത്|ആണ്।)$'
    ]
    
    # Apply 3 iterations to strip multi-layered fillers like "હેલો મારું નામ તક્ષ પટેલ છે" or "मारुना ऐम टॉक झे"
    for _ in range(3):
        for pattern in remove_patterns:
            clean = re.sub(pattern, '', clean, flags=re.IGNORECASE).strip()
    
    # Final cleanup of trailing single verbs, conversational words, or punctuation
    clean = re.sub(r'^(है|हूँ|हूं|hai|hu|છે|છુ|છું|ആണ്|टॉक|talk|speaking|talking)\s+|\s+(है|हूँ|हूं|hai|hu|છે|છુ|છું|ആണ്|टॉक|talk|speaking|talking)$', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'^[^\w\u0900-\u097F\u0A80-\u0AFF\u0C00-\u0C7F\u0D00-\u0D7F]+|[^\w\u0900-\u097F\u0A80-\u0AFF\u0C00-\u0C7F\u0D00-\u0D7F]+$', '', clean).strip()
    
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
                "issue_type": extracted.get("issue_type", state.get("issue_type", "No Cooling / Insufficient Cooling")),
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
    clean_issue_type = extracted.get("issue_type") or ticket.issue_type or "General Maintenance / Service"
    raw_issue_desc = extracted.get("type_of_complaint") or ticket.issue_description or "Not Provided"
    clean_issue = f"[{clean_issue_type}] {raw_issue_desc}" if (clean_issue_type and clean_issue_type != "Other" and clean_issue_type.lower() not in raw_issue_desc.lower()) else raw_issue_desc

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
    
    # Atomic DB claim to prevent thread race conditions
    from icemake_bot.models import IcemakeTicket
    if not force:
        updated_count = IcemakeTicket.objects.filter(
            id=ticket.id,
            google_sheet_synced=False
        ).update(google_sheet_synced=True)
        if updated_count == 0:
            print(f"[GOOGLE SHEET ALREADY CLAIMED]: Ticket #{ticket.ticket_number} already exported to Google Sheet by another thread. Skipping.")
            return
    else:
        ticket.google_sheet_synced = True
        ticket.save(update_fields=["google_sheet_synced"])

    try:
        response = requests.post(url, json=payload, timeout=25, allow_redirects=True)
        print(f"[Google Sheet Webhook Status]: {response.status_code}, response: {response.text[:200]}")
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
            f"⚙️ *Product Name:* {ticket.machine_model_no or 'N/A'}\n"
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

def _get_engineer_whatsapp_for_state(state_str: str):
    """
    Dynamically routes WhatsApp alert to designated Regional Service Engineer based on ticket state.
    Returns: (engineer_phone_number, engineer_name, region_name)
    """
    import os
    st = (state_str or "").lower().strip()

    # 1. GUJARAT REGION (Mr. Rutvik - 8733004773)
    gujarat_keywords = [
        "gujarat", "gujrat", "गिजरात", "गुजरात", "ગુજરાત",
        "ahmedabad", "gandhinagar", "surat", "vadodara", "rajkot", "bhavnagar", "jamnagar", "junagadh", "anand", "mehsana"
    ]
    if any(k in st for k in gujarat_keywords):
        num = os.getenv("ENGINEER_WHATSAPP_GUJARAT") or "918733004773"
        return num, "Mr. Rutvik", "Gujarat"

    # 2. NORTH REGION (Mr. Manjit - 9104142402)
    north_keywords = [
        "delhi", "दिल्ली", "દિલ્હી", "ncr", "new delhi",
        "haryana", "हरियाणा", "હરિયાણા", "gurgaon", "gurugram", "faridabad", "ambala",
        "uttar pradesh", "up", "उत्तर प्रदेश", "उत्तरप्रदेश", "ઉત્તર પ્રદેશ", "lucknow", "noida", "kanpur", "agra", "varanasi", "ghaziabad",
        "uttarakhand", "उत्तराखंड", "ઉત્તરાખંડ", "dehradun", "haridwar",
        "himachal", "himachal pradesh", "hp", "हिमाचल", "હિમાચલ", "shimla",
        "punjab", "पंजाब", "ਪੰਜਾਬ", "ludhiana", "amritsar", "jalandhar", "chandigarh",
        "j&k", "jk", "jammu", "kashmir", "जम्मू", "कश्मीर", "જમ્મુ"
    ]
    if any(k in st for k in north_keywords):
        num = os.getenv("ENGINEER_WHATSAPP_NORTH") or "919104142402"
        return num, "Mr. Manjit", "North"

    # 3. EAST REGION (Mr. Mahesh - 9913381306)
    east_keywords = [
        "west bengal", "bengal", "kolkata", "kolkatta", "पश्चिम बंगाल", "કોલકાતા", "બંગાળ",
        "assam", "असम", "અસમ", "guwahati",
        "bihar", "बिहार", "બિહાર", "patna",
        "chhattisgarh", "chattisgarh", "छत्तीसगढ़", "છત્તીસગઢ", "raipur",
        "orissa", "odisha", "उड़ीसा", "ओडिशा", "ઓડિશા", "bhubaneswar",
        "jharkhand", "झारखंड", "ઝારખંડ", "ranchi"
    ]
    if any(k in st for k in east_keywords):
        num = os.getenv("ENGINEER_WHATSAPP_EAST") or "919913381306"
        return num, "Mr. Mahesh", "East"

    # 4. WEST REGION (Mr. Ashok - 7490021566)
    west_keywords = [
        "maharashtra", "maharastra", "मराठी", "महाराष्ट्र", "મહારાષ્ટ્ર", "mumbai", "pune", "nagpur", "nashik", "thane",
        "rajasthan", "राजस्थान", "રાજસ્થાન", "jaipur", "jodhpur", "udaipur", "kota",
        "madhya pradesh", "mp", "madyapradesh", "मध्य प्रदेश", "મધ્ય પ્રદેશ", "indore", "bhopal", "gwalior",
        "goa", "गोवा", "ગોવા"
    ]
    if any(k in st for k in west_keywords):
        num = os.getenv("ENGINEER_WHATSAPP_WEST") or "917490021566"
        return num, "Mr. Ashok", "West"

    # 5. SOUTH REGION (Ms. Vaidehi - 9725891156)
    south_keywords = [
        "kerala", "केरल", "કેરળ", "kochi", "trivandrum",
        "tamil nadu", "tamilnadu", "तमिलनाडु", "તમિલનાડુ", "chennai", "coimbatore",
        "telangana", "telungana", "तेलंगाना", "તેલંગાણા", "hyderabad",
        "karnataka", "कर्नाटक", "કર્ણાટક", "bengaluru", "bangalore", "mysore",
        "andhra", "andhra pradesh", "आंध्र प्रदेश", "આંધ્ર પ્રદેશ", "vizag", "vijayawada"
    ]
    if any(k in st for k in south_keywords):
        num = os.getenv("ENGINEER_WHATSAPP_SOUTH") or "919725891156"
        return num, "Ms. Vaidehi", "South"

    # Fallback Default: Gujarat Engineer (Mr. Rutvik)
    num = os.getenv("ENGINEER_WHATSAPP_GUJARAT") or os.getenv("ENGINEER_WHATSAPP_NUMBER") or "918733004773"
    return num, "Mr. Rutvik", "Gujarat"


def _send_whatsapp_engineer_notification(ticket):
    """
    Sends WhatsApp alert to the designated Regional Service Engineer based on ticket state.
    """
    try:
        import os
        from bot.services.whatsapp_service import send_whatsapp_message
        
        state_str = f"{ticket.city_state or ''} {ticket.company_name or ''}".strip()
        engineer_number, engineer_name, region_name = _get_engineer_whatsapp_for_state(state_str)

        clean_eng = "".join(filter(str.isdigit, str(engineer_number)))
        if len(clean_eng) == 10:
            clean_eng = "91" + clean_eng

        cust_phone = ticket.registered_mobile or (ticket.conversation.user_number if ticket.conversation else "N/A")

        wa_text = (
            f"🚨 *NEW ICEMAKE SERVICE TICKET ALERT ({region_name.upper()} REGION)*\n\n"
            f"A new complaint ticket has been logged by customer:\n\n"
            f"📋 *Ticket #:* {ticket.ticket_number}\n"
            f"👤 *Customer Name:* {ticket.customer_name or 'N/A'}\n"
            f"📞 *Customer Mobile:* {cust_phone}\n"
            f"📍 *City / State:* {ticket.city_state or 'N/A'}\n"
            f"🏠 *Address:* {ticket.company_name or 'N/A'}\n"
            f"⚙️ *Product Name:* {ticket.machine_model_no or 'N/A'}\n"
            f"🛠️ *Issue Type:* {ticket.issue_type or 'Other'}\n"
            f"📝 *Description:* {ticket.issue_description or 'N/A'}\n\n"
            f"👤 *Assigned Engineer:* {engineer_name}\n"
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

        print(f"🚨 [ENGINEER WA ALERT SUCCESS]: Alert sent to {region_name} Engineer {engineer_name} ({clean_eng}) for Ticket #{ticket.ticket_number}. Response: {res}")
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
