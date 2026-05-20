# import os
# import audioop
# import azure.cognitiveservices.speech as speechsdk
# from dotenv import load_dotenv

# load_dotenv()

# AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
# AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

# VOICE_MAP = {
#     "en": "en-IN-AartiNeural",
#     "hi": "hi-IN-AartiNeural",
#     "gu": "gu-IN-DhwaniNeural"
# }

# PROSODY_MAP = {
#     "en": {"rate": "0%", "pitch": "0%", "volume": "0%"},
#     "hi": {"rate": "0%", "pitch": "0%", "volume": "0%"},
#     "gu": {"rate": "+10%", "pitch": "0%", "volume": "0%"},
# }

# def _amplify_pcm(pcm_data: bytes, gain: float = 2.0) -> bytes:
#     try:
#         return audioop.mul(pcm_data, 2, gain)
#     except Exception as e:
#         print(f"Amplify error: {e}")
#         return pcm_data

# def generate_tts_file(filename, text, lang="en"):
#     speech_config = speechsdk.SpeechConfig(
#         subscription=AZURE_SPEECH_KEY,
#         region=AZURE_SPEECH_REGION
#     )
#     voice_name = VOICE_MAP.get(lang, VOICE_MAP["en"])
#     speech_config.speech_synthesis_voice_name = voice_name
#     speech_config.set_speech_synthesis_output_format(
#         speechsdk.SpeechSynthesisOutputFormat.Raw8Khz16BitMonoPcm
#     )

#     synthesizer = speechsdk.SpeechSynthesizer(
#         speech_config=speech_config,
#         audio_config=None
#     )

#     prosody = PROSODY_MAP.get(lang, PROSODY_MAP["en"])
#     rate = prosody["rate"]
#     pitch = prosody["pitch"]

#     xml_lang = "en-IN" if lang == "en" else ("hi-IN" if lang == "hi" else "gu-IN")

#     ssml = f"""
#     <speak version='1.0' xmlns="http://www.w3.org/2001/10/synthesis" 
#            xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang='{xml_lang}'>
#         <voice name='{voice_name}'>
#             <mstts:silence type="Leading" value="150ms"/>
#             <prosody rate='{rate}' pitch='{pitch}' volume='0%'>
#                 {text}
#             </prosody>
#             <mstts:silence type="Tailing" value="50ms"/>
#         </voice>
#     </speak>
#     """

#     result = synthesizer.speak_ssml_async(ssml).get()

#     if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
#         pcm = result.audio_data
#         pcm = _amplify_pcm(pcm, gain=2.0)
#         ulaw = audioop.lin2ulaw(pcm, 2)
        
#         os.makedirs("mp3_responses", exist_ok=True)
#         file_path = os.path.join("mp3_responses", filename)
#         with open(file_path, "wb") as f:
#             f.write(ulaw)
            
#         print(f"Voice Generated: {file_path}")
#     else:
#         print(f"Failed: {result.reason}")

# if __name__ == "__main__":
#     print("Generating Multilingual Flow Audio Assets...")
#     assets = [
#         # English
#         ("en_step_intro_time.raw", "Sir, this is Naavya calling from Kia. Recently, you had shown interest in the Kia Seltos online, so I just wanted to quickly connect with you. Is this a convenient time for a short 2-minute conversation?", "en"),
#         ("en_step_driving_pattern.raw", "Thank you so much, Sir. Just to understand your requirement better and suggest the most suitable Seltos variant, may I know whether the car will be used mostly for city drives, highway travel, or a mix of both?", "en"),
#         ("en_step_family_size.raw", "Got it, Sir. And usually, how many family members travel together with you?", "en"),
#         ("en_step_driver_type.raw", "Understood. And will the vehicle be mainly self-driven by you, or would there also be a chauffeur driving it?", "en"),
#         ("en_step_fuel.raw", "Perfect. Sir, are you more inclined towards a Petrol model or Diesel?", "en"),
#         ("en_step_transmission.raw", "Sure. And for transmission, would you prefer Manual, iMT, or a fully Automatic driving experience?", "en"),
#         ("en_step_variant.raw", "Have you already explored any particular Seltos variant, like HTK, HTX, GTX Plus, or maybe the X-Line?", "en"),
#         ("en_step_budget.raw", "Just so I can recommend the best option within your expectations, may I know the budget range you’re considering for your new car?", "en"),
#         ("en_step_timeline.raw", "That sounds great, Sir. And how soon are you planning to purchase the vehicle — immediately, within the next month, or are you currently exploring options?", "en"),
#         ("en_step_exchange.raw", "Alright. Also, are you currently driving any car that you may consider exchanging while purchasing the new Seltos?", "en"),
#         ("en_step_pitch_test_drive.raw", "Based on what you've shared, Sir, I genuinely feel the Kia Seltos would suit your requirements very well — especially its comfort, premium features, and driving experience. I would highly recommend a test drive so you can experience it personally. Would you be more comfortable with a home test drive or visiting the showroom?", "en"),
#         ("en_step_appointment_time.raw", "Wonderful, Sir. Please let me know a convenient date and time for you, and I’ll arrange everything accordingly.", "en"),
#         ("en_step_closing.raw", "Thank you so much for your time, Sir. Your appointment has been successfully scheduled. We truly look forward to welcoming you to the Kia family and helping you experience the Seltos personally. Have a wonderful day ahead!", "en"),

#         # Hindi (Hinglish) - Completely Humanized with Pauses and Fillers
#         ("hi_step_intro_time.raw", "Namaste Sir... main Naavya bol rahi hoon Kia se. Aapne recently Kia Seltos ke liye online enquiry ki thi, isliye bas aapse short connect karna tha. ... Kya abhi 2 minute baat karne ka convenient time hai?", "hi"),
#         ("hi_step_driving_pattern.raw", "Bahut badiya Sir. ... Aapki requirement ko better samajhne ke liye batayiye, gaadi zyada city driving ke liye rahegi... highway travel ke liye... ya dono ka mix rahega?", "hi"),
#         ("hi_step_family_size.raw", "Achha ji... aur usually aapke saath kitne family members travel karte hain?", "hi"),
#         ("hi_step_driver_type.raw", "Samajh gayi... Aur gaadi mainly aap khud drive karenge ya driver bhi rahega?", "hi"),
#         ("hi_step_fuel.raw", "Perfect... To Aap Petrol prefer kar rahe hain ya Diesel model dekh rahe hain?", "hi"),
#         ("hi_step_transmission.raw", "Theek hai. ... Aur driving comfort ke hisaab se aap Manual... iMT... ya Automatic transmission pasand karenge?", "hi"),
#         ("hi_step_variant.raw", "Kya aapne Seltos ka koi specific variant explore kiya hai abhi tak? ... Jaise HTK... HTX... GTX Plus... ya X-Line?", "hi"),
#         ("hi_step_budget.raw", "hmm... aapki expectation ke according best variant suggest karne ke liye... kya main aapka approximate budget range jaan sakti hoon?", "hi"),
#         ("hi_step_timeline.raw", "Bahut achha. ... Aur aap gaadi kab tak purchase karne ka plan kar rahe hain? Immediate... agle 1 mahine mein... ya abhi options explore kar rahe hain?", "hi"),
#         ("hi_step_exchange.raw", "Okay Sir. ... Kya aapke paas abhi koi existing car hai jise aap exchange karna consider karenge?", "hi"),
#         ("hi_step_pitch_test_drive.raw", "Aapki requirement sunke lag raha hai Sir ki Kia Seltos aapko kaafi pasand aayegi... specially uska comfort, premium feel aur driving experience. ... Main definitely recommend karungi ki aap ek test drive experience karein. Aap showroom visit prefer karenge... ya hum home test drive arrange kar dein?", "hi"),
#         ("hi_step_appointment_time.raw", "Wonderful Sir. ... Aapke liye kaunsa date aur time convenient rahega? Main accordingly appointment arrange kar deti hoon.", "hi"),
#         ("hi_step_closing.raw", "Bahut bahut dhanyavaad aapka, aapne apna valuable time diya. ... Aapka appointment successfully schedule ho gaya hai. Hum jaldi hi aapse milne ke liye excited hain aur umeed hai ki aapko Kia Seltos ka experience bahut pasand aayega. ... Aapka din shubh ho!", "hi"),

#         # Gujarati
#         ("gu_step_intro_time.raw", "નમસ્તે સર, મારું નામ આરતી છે અને હું કિયા માંથી બોલું છું. તમે તાજેતરમાં કિયા સેલ્ટોસ માટે રસ દાખવ્યો હતો. શું અત્યારે બે મિનિટ વાત કરી શકાય?", "gu"),
#         ("gu_step_driving_pattern.raw", "આભાર સર. યોગ્ય વેરિઅન્ટ સૂચવવા માટે, ગાડી વધુ સિટીમાં ચાલશે, હાઇવે પર, કે મિક્સ ચાલશે?", "gu"),
#         ("gu_step_family_size.raw", "સામાન્ય રીતે કેટલા સભ્યો એકસાથે મુસાફરી કરે છે?", "gu"),
#         ("gu_step_driver_type.raw", "ગાડી તમે જાતે ચલાવશો કે ડ્રાઈવર ચલાવશે?", "gu"),
#         ("gu_step_fuel.raw", "સર, તમે પેટ્રોલ જુઓ છો કે ડીઝલ?", "gu"),
#         ("gu_step_transmission.raw", "અને તમે મેન્યુઅલ, iMT, કે ઓટોમેટિક ટ્રાન્સમિશન પસંદ કરશો?", "gu"),
#         ("gu_step_variant.raw", "શું તમે સેલ્ટોસનું કોઈ ચોક્કસ વેરિઅન્ટ જોયું છે, જેમ કે HTK, HTX, GTX Plus, કે X-Line?", "gu"),
#         ("gu_step_budget.raw", "તમારી જરૂરિયાત મુજબ યોગ્ય વેરિઅન્ટ સૂચવવા માટે, શું હું તમારું અંદાજિત બજેટ જાણી શકું?", "gu"),
#         ("gu_step_timeline.raw", "તમે ગાડી ક્યારે લેવાનું વિચારી રહ્યા છો? તરત, એક મહિનામાં, કે અત્યારે માત્ર તપાસ કરી રહ્યા છો?", "gu"),
#         ("gu_step_exchange.raw", "શું તમારી પાસે કોઈ જૂની ગાડી છે જેને તમે એક્સચેન્જ કરવા માંગો છો?", "gu"),
#         ("gu_step_pitch_test_drive.raw", "તમારી જરૂરિયાત મુજબ, હું ટેસ્ટ ડ્રાઈવ માટે ભલામણ કરીશ જેથી તમે સેલ્ટોસના પ્રીમિયમ ફીચર્સ અનુભવી શકો. શું તમે ઘરે ટેસ્ટ ડ્રાઈવ પસંદ કરશો કે શોરૂમ આવવાનું પસંદ કરશો?", "gu"),
#         ("gu_step_appointment_time.raw", "તમારા માટે કયો દિવસ અને સમય અનુકૂળ રહેશે?", "gu"),
#         ("gu_step_closing.raw", "તમારો કિંમતી સમય આપવા બદલ ખૂબ ખૂબ આભાર. મેં તમારી એપોઇન્ટમેન્ટ બુક કરી લીધી છે. તમારો દિવસ શુભ રહે!", "gu")
#     ]

#     for filename, text, lang in assets:
#         generate_tts_file(filename, text, lang)
#     print("Done! All multilingual Fast-Path flow audio is ready.")













import os
import audioop
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.types.voice_settings import VoiceSettings

load_dotenv()

ELEVENLABS_CLIENT = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

ELEVENLABS_VOICE_MAP = {
    "en": "aSFxChEgBmCyExpaDqHd",  # Kanika
    "hi": "aSFxChEgBmCyExpaDqHd",
    "gu": "aSFxChEgBmCyExpaDqHd",
}


def _amplify_pcm(pcm_data: bytes, gain: float = 1.5) -> bytes:
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
    file_path = os.path.join("mp3_responses", filename)
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        print(f"⏭️  Skipping (already exists): {filename}")
        return

    voice_id = ELEVENLABS_VOICE_MAP.get(lang, ELEVENLABS_VOICE_MAP["en"])

    try:
        # pcm_8000 = native 8kHz 16-bit PCM mono — no MP3 decode, no pydub needed
        audio_generator = ELEVENLABS_CLIENT.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id="eleven_multilingual_v2",  # More natural than turbo
            output_format="pcm_8000",            # Native 8kHz PCM for telephony
            voice_settings=VoiceSettings(
                stability=0.25,          # Lower = more expressive, less robotic
                similarity_boost=0.75,   # Stay close to voice character
                style=0.50,              # Natural rhythm and emphasis
                use_speaker_boost=True   # Cleaner audio, less glitch
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

        pcm = _amplify_pcm(pcm, gain=1.5)
        ulaw = audioop.lin2ulaw(pcm, 2)

        os.makedirs("mp3_responses", exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(ulaw)

        print(f"✅ Voice Generated: {file_path}")

    except Exception as e:
        print(f"❌ Failed to generate {filename}: {e}")


if __name__ == "__main__":
    print("Generating Multilingual Flow Audio Assets via ElevenLabs...")
    assets = [
        # English
        ("en_step_intro_time.raw", "Sir, this is Naavya calling from Kia. Recently, you had shown interest in the Kia Seltos online, so I just wanted to quickly connect with you. Is this a convenient time for a short 2-minute conversation?", "en"),
        ("en_step_driving_pattern.raw", "Thank you so much, Sir. Just to understand your requirement better and suggest the most suitable Seltos variant, may I know whether the car will be used mostly for city drives, highway travel, or a mix of both?", "en"),
        ("en_step_family_size.raw", "Got it, Sir. And usually, how many family members travel together with you?", "en"),
        ("en_step_driver_type.raw", "Understood. And will the vehicle be mainly self-driven by you, or would there also be a chauffeur driving it?", "en"),
        ("en_step_fuel.raw", "Perfect. Sir, are you more inclined towards a Petrol model or Diesel?", "en"),
        ("en_step_transmission.raw", "Sure. And for transmission, would you prefer Manual, iMT, or a fully Automatic driving experience?", "en"),
        ("en_step_variant.raw", "Have you already explored any particular Seltos variant, like HTK, HTX, GTX Plus, or maybe the X-Line?", "en"),
        ("en_step_budget.raw", "Just so I can recommend the best option within your expectations, may I know the budget range you're considering for your new car?", "en"),
        ("en_step_timeline.raw", "That sounds great, Sir. And how soon are you planning to purchase the vehicle — immediately, within the next month, or are you currently exploring options?", "en"),
        ("en_step_exchange.raw", "Alright. Also, are you currently driving any car that you may consider exchanging while purchasing the new Seltos?", "en"),
        ("en_step_pitch_test_drive.raw", "Based on what you've shared, Sir, I genuinely feel the Kia Seltos would suit your requirements very well — especially its comfort, premium features, and driving experience. I would highly recommend a test drive so you can experience it personally. Would you be more comfortable with a home test drive or visiting the showroom?", "en"),
        ("en_step_appointment_time.raw", "Wonderful, Sir. Please let me know a convenient date and time for you, and I'll arrange everything accordingly.", "en"),
        ("en_step_closing.raw", "Thank you so much for your time, Sir. Your appointment has been successfully scheduled. We truly look forward to welcoming you to the Kia family and helping you experience the Seltos personally. Have a wonderful day ahead!", "en"),

        # Hindi (Hinglish)
        ("hi_step_intro_time.raw", "Namaste Sir... main Naavya bol rahi hoon Kia se. Aapne recently Kia Seltos ke liye online enquiry ki thi, isliye bas aapse short connect karna tha. Kya abhi 2 minute baat karne ka convenient time hai?", "hi"),
        ("hi_step_driving_pattern.raw", "Bahut badiya Sir. Aapki requirement ko better samajhne ke liye batayiye, gaadi zyada city driving ke liye rahegi, highway travel ke liye, ya dono ka mix rahega?", "hi"),
        ("hi_step_family_size.raw", "Achha ji... aur usually aapke saath kitne family members travel karte hain?", "hi"),
        ("hi_step_driver_type.raw", "Samajh gayi... Aur gaadi mainly aap khud drive karenge ya driver bhi rahega?", "hi"),
        ("hi_step_fuel.raw", "Perfect... To Aap Petrol prefer kar rahe hain ya Diesel model dekh rahe hain?", "hi"),
        ("hi_step_transmission.raw", "Theek hai. Aur driving comfort ke hisaab se aap Manual, iMT, ya Automatic transmission pasand karenge?", "hi"),
        ("hi_step_variant.raw", "Kya aapne Seltos ka koi specific variant explore kiya hai abhi tak? Jaise HTK, HTX, GTX Plus, ya X-Line?", "hi"),
        ("hi_step_budget.raw", "Aapki expectation ke according best variant suggest karne ke liye, kya main aapka approximate budget range jaan sakti hoon?", "hi"),
        ("hi_step_timeline.raw", "Bahut achha. Aur aap gaadi kab tak purchase karne ka plan kar rahe hain? Immediate, agle 1 mahine mein, ya abhi options explore kar rahe hain?", "hi"),
        ("hi_step_exchange.raw", "Okay Sir. Kya aapke paas abhi koi existing car hai jise aap exchange karna consider karenge?", "hi"),
        ("hi_step_pitch_test_drive.raw", "Aapki requirement sunke lag raha hai Sir ki Kia Seltos aapko kaafi pasand aayegi, specially uska comfort, premium feel aur driving experience. Main definitely recommend karungi ki aap ek test drive experience karein. Aap showroom visit prefer karenge, ya hum home test drive arrange kar dein?", "hi"),
        ("hi_step_appointment_time.raw", "Wonderful Sir. Aapke liye kaunsa date aur time convenient rahega? Main accordingly appointment arrange kar deti hoon.", "hi"),
        ("hi_step_closing.raw", "Bahut bahut dhanyavaad aapka, aapne apna valuable time diya. Aapka appointment successfully schedule ho gaya hai. Hum jaldi hi aapse milne ke liye excited hain aur umeed hai ki aapko Kia Seltos ka experience bahut pasand aayega. Aapka din shubh ho!", "hi"),

        # Gujarati
        ("gu_step_intro_time.raw", "નમસ્તે સર, મારું નામ આરતી છે અને હું કિયા માંથી બોલું છું. તમે તાજેતરમાં કિયા સેલ્ટોસ માટે રસ દાખવ્યો હતો. શું અત્યારે બે મિનિટ વાત કરી શકાય?", "gu"),
        ("gu_step_driving_pattern.raw", "આભાર સર. યોગ્ય વેરિઅન્ટ સૂચવવા માટે, ગાડી વધુ સિટીમાં ચાલશે, હાઇવે પર, કે મિક્સ ચાલશે?", "gu"),
        ("gu_step_family_size.raw", "સામાન્ય રીતે કેટલા સભ્યો એકસાથે મુસાફરી કરે છે?", "gu"),
        ("gu_step_driver_type.raw", "ગાડી તમે જાતે ચલાવશો કે ડ્રાઈવર ચલાવશે?", "gu"),
        ("gu_step_fuel.raw", "સર, તમે પેટ્રોલ જુઓ છો કે ડીઝલ?", "gu"),
        ("gu_step_transmission.raw", "અને તમે મેન્યુઅલ, iMT, કે ઓટોમેટિક ટ્રાન્સમિશન પસંદ કરશો?", "gu"),
        ("gu_step_variant.raw", "શું તમે સેલ્ટોસનું કોઈ ચોક્કસ વેરિઅન્ટ જોયું છે, જેમ કે HTK, HTX, GTX Plus, કે X-Line?", "gu"),
        ("gu_step_budget.raw", "તમારી જરૂરિયાત મુજબ યોગ્ય વેરિઅન્ટ સૂચવવા માટે, શું હું તમારું અંદાજિત બજેટ જાણી શકું?", "gu"),
        ("gu_step_timeline.raw", "તમે ગાડી ક્યારે લેવાનું વિચારી રહ્યા છો? તરત, એક મહિનામાં, કે અત્યારે માત્ર તપાસ કરી રહ્યા છો?", "gu"),
        ("gu_step_exchange.raw", "શું તમારી પાસે કોઈ જૂની ગાડી છે જેને તમે એક્સચેન્જ કરવા માંગો છો?", "gu"),
        ("gu_step_pitch_test_drive.raw", "તમારી જરૂરિયાત મુજબ, હું ટેસ્ટ ડ્રાઈવ માટે ભલામણ કરીશ જેથી તમે સેલ્ટોસના પ્રીમિયમ ફીચર્સ અનુભવી શકો. શું તમે ઘરે ટેસ્ટ ડ્રાઈવ પસંદ કરશો કે શોરૂમ આવવાનું પસંદ કરશો?", "gu"),
        ("gu_step_appointment_time.raw", "તમારા માટે કયો દિવસ અને સમય અનુકૂળ રહેશે?", "gu"),
        ("gu_step_closing.raw", "તમારો કિંમતી સમય આપવા બદલ ખૂબ ખૂબ આભાર. મેં તમારી એપોઇન્ટમેન્ટ બુક કરી લીધી છે. તમારો દિવસ શુભ રહે!", "gu"),
    ]

    for filename, text, lang in assets:
        generate_tts_file(filename, text, lang)

    print("\nDone! All multilingual Fast-Path flow audio is ready.")