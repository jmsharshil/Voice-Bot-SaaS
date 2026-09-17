import os
import sys
import audioop
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.types.voice_settings import VoiceSettings

# Ensure stdout encodes correctly
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

ELEVENLABS_CLIENT = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

# Kanika Neural Voice ID
ELEVENLABS_VOICE_MAP = {
    "en": "aSFxChEgBmCyExpaDqHd",
    "hi": "aSFxChEgBmCyExpaDqHd",
    "gu": "aSFxChEgBmCyExpaDqHd",
}

def _amplify_pcm(pcm_data: bytes, gain: float = 0.6) -> bytes:
    try:
        import numpy as np
        samples = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32)
        samples = samples * gain
        samples = np.clip(samples, -32768, 32767)
        return samples.astype(np.int16).tobytes()
    except Exception as e:
        print(f"Amplify error: {e}")
        return pcm_data

def generate_tts_file(filename, text, lang="en"):
    # Output path in subfolder
    subfolder = "Naavya"
    target_dir = os.path.join("mp3_responses", subfolder)
    os.makedirs(target_dir, exist_ok=True)
    
    file_path = os.path.join(target_dir, filename)

    voice_id = ELEVENLABS_VOICE_MAP.get(lang, ELEVENLABS_VOICE_MAP["en"])

    try:
        audio_generator = ELEVENLABS_CLIENT.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id="eleven_multilingual_v2",
            output_format="pcm_8000", # Native 8kHz PCM for telephony
            voice_settings=VoiceSettings(
                stability=0.55,
                similarity_boost=0.75,
                style=0.00,
                use_speaker_boost=False,
                speed=1.00
            )
        )

        pcm = b""
        for chunk in audio_generator:
            if chunk:
                pcm += chunk

        if not pcm:
            print(f"❌ ElevenLabs returned empty audio for: {filename}")
            return

        if len(pcm) % 2 != 0:
            pcm = pcm[:-1]

        pcm = _amplify_pcm(pcm, gain=0.6)
        ulaw = audioop.lin2ulaw(pcm, 2)

        with open(file_path, "wb") as f:
            f.write(ulaw)

        print(f"[OK] Voice Generated: {file_path}")

    except Exception as e:
        print(f"[FAIL] Failed to generate {filename}: {e}")

if __name__ == "__main__":
    target_filters = sys.argv[1:] if len(sys.argv) > 1 else []
    
    if target_filters:
        print(f"Generating Naavya audio only for files matching: {target_filters}")
    else:
        print("Generating Naavya Multilingual Flow Audio Assets via ElevenLabs...")

    assets = [
        # HINDI / HINGLISH

        ("hi_step1_greeting.raw", "Namaste! Main Naavya bol rahi hoon JMS automobile se. Aasha karti hoon aapka din achha ja raha hoga. Kya main aapse do minute baat kar sakti hoon?", "hi"),

        ("hi_step2_discover_use.raw", "Bahut shukriya. Main aapki zaroorat ko thoda aur behatar samajhna chahti hoon. Kya aap gaadi zyada shehar mein chalane ke liye dekh rahe hain, lambi yatraon ke liye, ya dono ke liye?", "hi"),

        ("hi_step2_end_call.raw", "Koi baat nahi sir. Aapne apna samay diya uske liye dhanyavaad. Agar bhavishya mein gaadi se judi kisi bhi jaankari ki zaroorat ho, toh humse kabhi bhi sampark kar sakte hain. Aapka din shubh ho.", "hi"),

        ("hi_step3_discover_budget.raw", "Samajh gayi. Taaki main aapko behtar vikalp suggest kar sakoon, kya aap apna  budget range bata sakte hain?", "hi"),

        ("hi_step4_discover_family.raw", "Bahut badhiya. Kya yeh gaadi mukhyata aapke vyaktigat upyog ke liye hogi ya poore parivaar ke liye bhi?", "hi"),

        ("hi_step5_discover_musthaves.raw", "Aur kya aapki koi khaas pasand ya requirement hai? Jaise sunroof, automatic transmission, electric vehicle, ya phir adhik safety features?", "hi"),

        ("hi_step6_pitch_visit.raw", "Sach kahun toh gaadi ki asli premium feeling usmein baithkar hi mehsoos hoti hai. Photos aur videos us experience ko poori tarah nahi dikha paate. Kya aap is hafte showroom visit karna pasand karenge?", "hi"),

        ("hi_step7_offer_testdrive.raw", "Aur ek test drive se aap gaadi ki comfort, performance aur driving experience ko khud mehsoos kar sakte hain. Kya main aapke liye ek test drive schedule kar doon?", "hi"),

        ("hi_step8_collect_details.raw", "Bahut achha. Kripya apna naam, suvidhajanak din aur samay  bata dijiye taaki main booking confirm kar sakoon.", "hi"),

        ("hi_step9_closing.raw", " Aapki booking safaltaapurvak note kar li gayi hai. Aapka din mangalmay ho. ", "hi"),


        # ("hi_step1_greeting.raw", "Hi there! Main Naavya bol rahi hoon. So lovely to connect with you! Kya aap abhi koi new car explore kar rahe hain... ya kisi specific model par baat karni hai?", "hi"),
        # ("hi_step2_discover_use.raw", "Bahut badiya! Aapki requirement ko thoda aur achhe se samajhne ke liye... kya main jaan sakti hoon ki car zyada city drives ke liye rahegi... highway travel ke liye... ya dono ka mix rahega?", "hi"),
        # ("hi_step2_end_call.raw", "Koi baat nahi sir, call receive karne ke liye shukriya. Jab bhi aapko car related koi query ho, aap bejijhak connect kar sakte hain. Take care! Bye!", "hi"),
        # ("hi_step3_discover_budget.raw", "Sahi hai. Aur lagbhag kitne budget range mein gaadi dekh rahe hain aap? Ek ballpark figure bhi chalega.", "hi"),
        # ("hi_step4_discover_family.raw", "Samajh gayi. Aur gaadi mainly aap apne personal use ke liye dekh rahe hain... ya family ke liye bhi?", "hi"),
        # ("hi_step5_discover_musthaves.raw", "Great! Aur koi specific must-haves hain aapki list mein? Jaise panoramic sunroof, electric vehicle, automatic transmission, ya higher ground clearance?", "hi"),
        # ("hi_step6_pitch_visit.raw", "Sach kahun toh... pictures aur videos mein wo premium feel nahi aati jo gaadi mein baith kar aati hai. Humare floor par ye cars stunning lagti hain. Kya main aapko is week showroom aane ke liye invite kar sakti hoon?", "hi"),
        # ("hi_step7_offer_testdrive.raw", "Aur bilkul... sabse best part! Kya aap ek test drive lena pasand karenge? Drive karne se hi car ki real driving dynamics pata chalti hai. Main aapke liye test drive kab schedule karoon?", "hi"),
        # ("hi_step8_collect_details.raw", "Perfect! Mujhe please aapka name, aane ki convenient date aur time, aur contact number bata dijiye taaki main test drive book kar sakoon.", "hi"),
        # ("hi_step9_closing.raw", "Thank you so much! Maine aapki appointment confirm kar di hai. Hum aapse showroom par milenge aur test drive ready rakhenge. Drive safe! Bye!", "hi"),

        # ENGLISH
        ("en_step1_greeting.raw", "Hi there! This is Naavya. So lovely to connect with you! Are you exploring a new car today, or is there a specific model you have your eye on?", "en"),
        ("en_step2_discover_use.raw", "That's wonderful! To understand your needs better, are you looking for a car for daily city use, weekend adventures, or a mix of both?", "en"),
        ("en_step2_end_call.raw", "No worries at all. Thank you so much for taking the call. Feel free to connect whenever you're ready to explore. Take care! Goodbye!", "en"),
        ("en_step3_discover_budget.raw", "Got it. And what budget range are you considering? A rough ballpark is totally fine.", "en"),
        ("en_step4_discover_family.raw", "Understood. Will this vehicle be primarily for yourself, or is it for the family too?", "en"),
        ("en_step5_discover_musthaves.raw", "Great choice! And do you have any must-haves, like a sunroof, an EV, an automatic gearbox, or high ground clearance?", "en"),
        ("en_step6_pitch_visit.raw", "Honestly, pictures and specs don't capture how premium it feels inside. Sitting inside makes all the difference! Would you like to visit our showroom this week?", "en"),
        ("en_step7_offer_testdrive.raw", "And of course, the best part — would you like to take it for a spin? A test drive tells you what no brochure can. What day works best for you?", "en"),
        ("en_step8_collect_details.raw", "Perfect! May I have your name, preferred date and time, and your phone number to confirm the booking?", "en"),
        ("en_step9_closing.raw", "Awesome! I have got you booked. We will have everything ready for you. Really looking forward to meeting you. Drive safe!", "en"),

        # GUJARATI
        ("gu_step1_greeting.raw", "હેલો! કેમ છો? હું પ્રિયા બોલી રહી છું. તમારી સાથે વાત કરીને આનંદ થયો! શું તમે આજે કોઈ નવી કાર જોવા માંગો છો કે કોઈ ખાસ મોડેલ વિશે વાત કરવી છે?", "gu"),
        ("gu_step2_discover_use.raw", "ખૂબ સરસ! તમારી જરૂરિયાતોને વધુ સારી રીતે સમજવા માટે, શું તમે આ કાર રોજિંદા સિટી ડ્રાઇવ માટે જુઓ છો, વીકેન્ડ મુસાફરી માટે, કે બંનેના મિક્સ માટે?", "gu"),
        ("gu_step2_end_call.raw", "કોઈ વાંધો નહીં. કૉલ પર વાત કરવા બદલ આભાર. જ્યારે પણ કાર વિશે કોઈ માહિતી જોઈએ, ચોક્કસ સંપર્ક કરજો. આવજો!", "gu"),
        ("gu_step3_discover_budget.raw", "બરાબર. અને તમારું અંદાજિત બજેટ કેટલું છે? એક અંદાજ આપશો તો પણ ચાલશે.", "gu"),
        ("gu_step4_discover_family.raw", "સમજી ગઈ. અને આ ગાડી મુખ્યત્વે તમારા પોતાના વપરાશ માટે છે, કે ફેમિલી માટે પણ છે?", "gu"),
        ("gu_step5_discover_musthaves.raw", "સરસ! અને શું તમારી કોઈ ખાસ જરૂરિયાતો છે, જેમ કે સનરૂફ, ઇલેક્ટ્રિક કાર, ઓટોમેટિક ગીયરબોક્સ, કે વધુ ગ્રાઉન્ડ ક્લિયરન્સ?", "gu"),
        ("gu_step6_pitch_visit.raw", "સાચું કહું તો, ફોટા કે વિડીયોમાં તે પ્રીમિયમ ફીલ નથી આવતી જે કારમાં બેસીને આવે છે. શું તમે આ અઠવાડિયે શોરૂમની મુલાકાત લેવાનું પસંદ કરશો?", "gu"),
        ("gu_step7_offer_testdrive.raw", "અને હા, સૌથી ઉત્તમ વસ્તુ — શું તમે ટેસ્ટ ડ્રાઇવ લેવા માંગો છો? એક વાર ચલાવી જોશો તો બધો ખ્યાલ આવી જશે. તમારા માટે કયો દિવસ અનુકૂળ રહેશે?", "gu"),
        ("gu_step8_collect_details.raw", "ખૂબ સરસ! ટેસ્ટ ડ્રાઈવ બુક કરવા માટે કૃપા કરીને તમારું નામ, અનુકૂળ તારીખ અને સમય, અને ફોન નંબર જણાવશો?", "gu"),
        ("gu_step9_closing.raw", "ખૂબ સરસ! મેં તમારી એપોઇન્ટમેન્ટ બુક કરી લીધી છે. અમે શોરૂમ પર તમારી રાહ જોઈશું. સેફ ડ્રાઇવ કરજો! આવજો!", "gu"),
    ]

    generated_count = 0
    for filename, text, lang in assets:
        if target_filters and not any(t_filter in filename for t_filter in target_filters):
            continue
        generate_tts_file(filename, text, lang)
        generated_count += 1

    print(f"\n[DONE] Generated {generated_count} Naavya audio asset(s).")
