with open('icemake_v2_bot/strategy.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_farewell_block = '''ICEMAKE_V2_SERIAL_FAREWELL = {
    "en": "No worries at all! A machine serial number is required to register a complaint. Please find your serial number and feel free to call us back anytime. Thank you for calling Ice Make! [FLOW_COMPLETE]",
    "hi": "कोई बात नहीं! शिकायत दर्ज करने के लिए सीरियल नंबर होना ज़रूरी है। आप आराम से अपना सीरियल नंबर देखकर दोबारा कॉल कर लीजिएगा। हमें आपकी मदद करने में बहुत खुशी होगी। आइस मेक में कॉल करने के लिए धन्यवाद! [FLOW_COMPLETE]",
    "gu": "કોઈ વાંધો નહીં! ફરિયાદ નોંધવા માટે સીરીયલ નંબર હોવો જરૂરી છે. તમે આરામથી સીરીયલ નંબર જોઈને ફરીથી કૉલ કરી શકો છો. તમારી મદદ કરવામાં અમને ખૂબ આનંદ થશે. આઈસ મેકમાં કૉલ કરવા બદલ આભાર! [FLOW_COMPLETE]",
    "te": "పర్వాలేదండి! ఫిర్యాదు నమోదు చేయడానికి సీరియల్ నంబర్ తప్పనిసరి. మీరు నిదానంగా మీ సీరియల్ నంబర్ చూసి మళ్లీ కాల్ చేయండి. ఐస్ మేక్‌కు కాల్ చేసినందుకు ధన్యవాదాలు! [FLOW_COMPLETE]",
    "pa": "ਕੋਈ ਗੱਲ ਨਹੀਂ ਜੀ! ਸ਼ਿਕਾਇਤ ਦਰਜ ਕਰਨ ਲਈ ਸੀਰੀਅਲ ਨੰਬਰ ਹੋਣਾ ਲਾਜ਼ਮੀ ਹੈ। ਤੁਸੀਂ ਆਰਾਮ ਨਾਲ ਆਪਣੀ ਮਸ਼ੀਨ ਦਾ ਸੀਰੀਅਲ ਨੰਬਰ ਦੇਖ ਕੇ ਦੁਬਾਰਾ ਕਾਲ ਕਰ ਲਵੋ। ਆਈਸ ਮੇਕ ਨੂੰ ਕਾਲ ਕਰਨ ਲਈ ਧੰਨਵਾਦ! [FLOW_COMPLETE]",
    "bn": "কোনো অসুবিধা নেই! অভিযোগ নথিভুক্ত করার জন্য সিরিয়াল নম্বর থাকা প্রয়োজন। আপনি সময় নিয়ে সিরিয়াল নম্বরটি দেখে আবার কল করবেন। আইס মেক-এ কল করার জন্য ধন্যবাদ! [FLOW_COMPLETE]",
    "mr": "काही हरकत नाही! तक्रार नोंदवण्यासाठी सिरीयल नंबर आवश्यक आहे. तुम्ही निवांत सिरीयल नंबर बघून पुन्हा कॉल करा. तुमची मदत करण्यात आम्हाला आनंदच होईल. आइस मेकला कॉल केल्याबद्दल धन्यवाद! [FLOW_COMPLETE]",
    "ta": "பரவாயில்லைங்க! புகார் பதிவு செய்ய சீரியல் எண் அவசியம். நீங்கள் நிதானமாக சீரியல் எண்ணைப் பார்த்துவிட்டு மீண்டும் அழைக்கலாம். ஐஸ் மேக் அழைத்ததற்கு நன்றி! [FLOW_COMPLETE]",
    "kn": "ಪರವಾಗಿಲ್ಲ! ದೂರು ದಾಖಲಿಸಲು ಸೀರಿಯಲ್ ಸಂಖ್ಯೆ ಅಗತ್ಯವಿದೆ. ನೀವು ನಿಧಾನವಾಗಿ ಸೀರಿಯಲ್ ಸಂಖ್ಯೆಯನ್ನು ನೋಡಿ ಮತ್ತೆ ಕರೆ ಮಾಡಿ. ಐಸ್ ಮೇಕ್‌ಗೆ ಕರೆ ಮಾಡಿದ್ದಕ್ಕಾಗಿ ಧನ್ಯವಾದಗಳು! [FLOW_COMPLETE]",
    "ml": "സാരമില്ല! പരാതി രജിസ്റ്റർ ചെയ്യാൻ സീരിയൽ നമ്പർ ആവശ്യമാണ്. നിങ്ങൾ സാവധാനം സീരിയൽ നമ്പർ കണ്ടെത്തിയ ശേഷം വീണ്ടും വിളിക്കൂ. നിങ്ങളെ സഹായിക്കുന്നതിൽ ഞങ്ങൾക്ക് സന്തോഷമേയുള്ളൂ. ഐസ് മേക്കിലേക്ക് വിളിച്ചതിന് നന്ദി! [FLOW_COMPLETE]"
}'''

new_farewell_block = '''ICEMAKE_V2_SERIAL_FAREWELL = {
    "en": "No worries at all! A machine serial number is required to register a complaint. Please find your serial number and feel free to call us back anytime. Thank you for contacting Ice Make 24 by 7 service support! Have a good day. [FLOW_COMPLETE]",
    "hi": "कोई बात नहीं! शिकायत दर्ज करने के लिए सीरियल नंबर होना ज़रूरी है। आप आराम से अपना सीरियल नंबर देखकर दोबारा कॉल कर लीजिएगा। आइस मेक 24 बाय 7 सर्विस सपोर्ट में संपर्क करने के लिए धन्यवाद। आपका दिन शुभ हो। [FLOW_COMPLETE]",
    "gu": "કોઈ વાંધો નહીં! ફરિયાદ નોંધવા માટે સીરીયલ નંબર હોવો જરૂરી છે. તમે આરામથી સીરીયલ નંબર જોઈને ફરીથી કૉલ કરી શકો છો. આઈસ મેક 24 બાય 7 સર્વિસ સપોર્ટનો સંપર્ક કરવા બદલ આભાર. તમારો દિવસ શુભ રહે. [FLOW_COMPLETE]",
    "te": "పర్వాలేదండి! ఫిర్యాదు నమోదు చేయడానికి సీరియల్ నంబర్ తప్పనిసరి. మీరు నిదానంగా మీ సీరియల్ నంబర్ చూసి మళ్లీ కాల్ చేయండి. ఐస్ మేక్ 24/7 సర్వీస్ సపోర్ట్‌ను సంప్రదించినందుకు ధన్యవాదాలు! హావ్ ఎ గుడ్ డే. [FLOW_COMPLETE]",
    "pa": "ਕੋਈ ਗੱਲ ਨਹੀਂ ਜੀ! ਸ਼ਿਕਾਇਤ ਦਰਜ ਕਰਨ ਲਈ ਸੀਰੀਅਲ ਨੰਬਰ ਹੋਣਾ ਲਾਜ਼ਮੀ ਹੈ। ਤੁਸੀਂ ਆਰਾਮ ਨਾਲ ਆਪਣੀ ਮਸ਼ੀਨ ਦਾ ਸੀਰੀਅਲ ਨੰਬਰ ਦੇਖ ਕੇ ਦੁਬਾਰਾ ਕਾਲ ਕਰ ਲਵੋ। ਆਈਸ ਮੇਕ 24 ਬਾਈ 7 ਸਰਵਿਸ ਸਪੋਰਟ ਨਾਲ ਸੰਪਰਕ ਕਰਨ ਲਈ ਧੰਨਵਾਦ! ਤੁਹਾਡਾ ਦਿਨ ਸ਼ੁਭ ਹੋਵੇ। [FLOW_COMPLETE]",
    "bn": "কোনো অসুবিধা নেই! অভিযোগ নথিভুক্ত করার জন্য সিরিয়াল নম্বর থাকা প্রয়োজন। আপনি সময় নিয়ে সিরিয়াল নম্বরটি দেখে আবার কল করবেন। আইস মেক ২৪/৭ সার্ভিস সাপোর্টে যোগাযোগ করার জন্য ধন্যবাদ! আপনার দিনটি শুভ হোক। [FLOW_COMPLETE]",
    "mr": "काही हरकत नाही! तक्रार नोंदवण्यासाठी सिरीयल नंबर आवश्यक आहे. तुम्ही निवांत सिरीयल नंबर बघून पुन्हा कॉल करा. आईस मेक २४ बाय ७ सर्व्हिस सपोर्टशी संपर्क साधल्याबद्दल धन्यवाद! तुमचा दिवस शुभ जावो. [FLOW_COMPLETE]",
    "ta": "பரவாயில்லைங்க! புகார் பதிவு செய்ய சீரியல் எண் அவசியம். நீங்கள் நிதானமாக சீரியல் எண்ணைப் பார்த்துவிட்டு மீண்டும் அழைக்கலாம். ஐஸ் மேக் 24/7 சேவை ஆதரவைத் தொடர்பு கொண்டதற்கு நன்றி! [FLOW_COMPLETE]",
    "kn": "ಪರವಾಗಿಲ್ಲ! ದೂರು ದಾಖಲಿಸಲು ಸೀರಿಯಲ್ ಸಂಖ್ಯೆ ಅಗತ್ಯವಿದೆ. ನೀವು ನಿಧಾನವಾಗಿ ಸೀರಿಯಲ್ ಸಂಖ್ಯೆಯನ್ನು ನೋಡಿ ಮತ್ತೆ ಕರೆ ಮಾಡಿ. ಐಸ್ ಮೇಕ್ 24/7 ಸೇವಾ ಬೆಂಬಲವನ್ನು ಸಂಪರ್ಕಿಸಿದ್ದಕ್ಕಾಗಿ ಧನ್ಯವಾದಗಳು! [FLOW_COMPLETE]",
    "ml": "സാരമില്ല! പരാതി രജിസ്റ്റർ ചെയ്യാൻ സീരിയൽ നമ്പർ ആവശ്യമാണ്. നിങ്ങൾ സാവധാനം സീരിയൽ നമ്പർ കണ്ടെത്തിയ ശേഷം വീണ്ടും വിളിക്കൂ. ഐസ് മേക്ക് 24/7 സർവീസ് സപ്പോർട്ടുമായി ബന്ധപ്പെട്ടതിന് നന്ദി! [FLOW_COMPLETE]"
}

ICEMAKE_THANKYOU_CLOSING = {
    "en": "Thank you for contacting Ice Make 24 by 7 service support. Have a good day.",
    "hi": "आइस मेक 24 बाय 7 सर्विस सपोर्ट में संपर्क करने के लिए धन्यवाद। आपका दिन शुभ हो।",
    "gu": "આઈસ મેક 24 બાય 7 સર્વિસ સપોર્ટનો સંપર્ક કરવા બદલ આભાર. તમારો દિવસ શુભ રહે.",
    "te": "ఐస్ మేక్ 24/7 సర్వీస్ సపోర్ట్‌ను సంప్రదించినందుకు ధన్యవాదాలు. హావ్ ఎ గుడ్ డే.",
    "pa": "ਆਈਸ ਮੇਕ 24 ਬਾਈ 7 ਸਰਵਿਸ ਸਪੋਰਟ ਨਾਲ ਸੰਪਰਕ ਕਰਨ ਲਈ ਧੰਨਵਾਦ। ਤੁਹਾਡਾ ਦਿਨ ਸ਼ੁਭ ਹੋਵੇ।",
    "bn": "আইস মেক ২৪/৭ সার্ভিস সাপোর্টে যোগাযোগ করার জন্য ধন্যবাদ। আপনার দিনটি শুভ হোক।",
    "mr": "आईस मेक २४ बाय ७ सर्व्हिस सपोर्टशी संपर्क साधल्याबद्दल धन्यवाद. तुमचा दिवस शुभ जावो.",
    "ta": "ஐஸ் மேக் 24/7 சேவை ஆதரவைத் தொடர்பு கொண்டதற்கு நன்றி. உங்கள் நாள் நல்லதாக இருக்கட்டும்.",
    "kn": "ಐಸ್ ಮೇಕ್ 24/7 ಸೇವಾ ಬೆಂಬಲವನ್ನು ಸಂಪರ್ಕಿಸಿದ್ದಕ್ಕಾಗಿ ಧನ್ಯವಾದಗಳು. ಶುಭ ದಿನ.",
    "ml": "ഐസ് മേക്ക് 24/7 സർവീസ് സപ്പോർട്ടുമായി ബന്ധപ്പെട്ടതിന് നന്ദി. നല്ലൊരു ദിവസം ആശംസിക്കുന്നു.",
}

def get_icemake_v2_serial_farewell(state=None, language="hi"):
    lang = language if language in ICEMAKE_V2_SERIAL_FAREWELL else "hi"
    return ICEMAKE_V2_SERIAL_FAREWELL.get(lang, ICEMAKE_V2_SERIAL_FAREWELL["hi"])'''

assert old_farewell_block in content, "old_farewell_block not found"
content = content.replace(old_farewell_block, new_farewell_block, 1)

# 2. Update rule 2b in system prompt
old_rule = 'b) SECOND TURN (guidance already given, or caller explicitly cannot provide it): Politely and firmly explain that without the machine serial number we cannot register any complaint, invite them to call back once located, and you MUST end your reply with [FLOW_COMPLETE].'
new_rule = 'b) SECOND TURN (guidance already given, or caller explicitly cannot provide it): Politely and firmly explain that without the machine serial number we cannot register any complaint, invite them to call back once located, ALWAYS include the farewell "आइस मेक 24 बाय 7 सर्विस सपोर्ट में संपर्क करने के लिए धन्यवाद। आपका दिन शुभ हो।" (or equivalent in {lang}), and you MUST end your reply with [FLOW_COMPLETE].'
assert old_rule in content, "old_rule not found"
content = content.replace(old_rule, new_rule, 1)

# 3. Update CANNOT_PROVIDE branch to append thank you closing if missing
old_cannot_provide = '''        else:
            state["serial_wait_requested"] = False
            reply = ai_reply if ai_reply else ICEMAKE_V2_SERIAL_FAREWELL.get(lang, ICEMAKE_V2_SERIAL_FAREWELL["en"])
            if "[FLOW_COMPLETE]" not in reply:
                reply += " [FLOW_COMPLETE]"'''

new_cannot_provide = '''        else:
            state["serial_wait_requested"] = False
            closing_thankyou = ICEMAKE_THANKYOU_CLOSING.get(lang, ICEMAKE_THANKYOU_CLOSING["hi"])
            if ai_reply:
                clean_ai = ai_reply.replace("[FLOW_COMPLETE]", "").strip()
                has_thankyou = any(k in clean_ai.lower() for k in ["24", "ice make", "आइस मेक", "આઈસ મેક", "ਸਰਵਿਸ", "సర్వీస్", "service support", "सपोर्ट", "સપોર્ટ"])
                if not has_thankyou:
                    clean_ai = f"{clean_ai} {closing_thankyou}"
                reply = f"{clean_ai} [FLOW_COMPLETE]"
            else:
                reply = ICEMAKE_V2_SERIAL_FAREWELL.get(lang, ICEMAKE_V2_SERIAL_FAREWELL["en"])
                if "[FLOW_COMPLETE]" not in reply:
                    reply += " [FLOW_COMPLETE]"'''

assert old_cannot_provide in content, "old_cannot_provide not found"
content = content.replace(old_cannot_provide, new_cannot_provide, 1)

# 4. Global guard on _handle_smart_serial_step before return:
old_return_guard = '''    state["current_step"] = next_step
    state["conversation_history"].append(f"Agent: {reply}")'''

new_return_guard = '''    if "[FLOW_COMPLETE]" in reply:
        closing_thankyou = ICEMAKE_THANKYOU_CLOSING.get(lang, ICEMAKE_THANKYOU_CLOSING["hi"])
        clean_rep = reply.replace("[FLOW_COMPLETE]", "").strip()
        has_thankyou = any(k in clean_rep.lower() for k in ["24", "ice make", "आइस मेक", "આઈસ મેક", "ਸਰਵਿਸ", "సర్వీస్", "service support", "सपोर्ट", "સપોર્ટ"])
        if not has_thankyou:
            clean_rep = f"{clean_rep} {closing_thankyou}"
        reply = f"{clean_rep} [FLOW_COMPLETE]"

    state["current_step"] = next_step
    state["conversation_history"].append(f"Agent: {reply}")'''

assert old_return_guard in content, "old_return_guard not found"
content = content.replace(old_return_guard, new_return_guard, 1)

with open('icemake_v2_bot/strategy.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: All changes applied!")
