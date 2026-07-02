# samsung_bot/audio_generator.py

import os
import sys
import requests
import audioop
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

# Text segments to synthesize in Gujarati
AUDIO_ASSETS = {
    "samsung_step1_greeting.raw": "નમસ્તે! હું નાવ્યા છું. હું VTech Samsung Cafe તરફથી વાત કરી રહી છું. શું તમારી સાથે વાત થઈ શકે?",
    "samsung_step2_ask_consent.raw": "નમસ્તે. તમે થોડા દિવસ પહેલા Samsung Product માટે interest દર્શાવ્યો હતો એટલે તમને call કર્યો છે. શું તમારી સાથે 2 મિનિટ વાત થઈ શકે?",
    "samsung_step3_ask_phone.raw": "Okay. તો શું હું જાણી શકું કે તમે અત્યારે કયો phone વાપરી રહ્યા છો?",
    "samsung_step4_ask_interest.raw": "Okay. તો શું તમે નવો smartphone લેવાનું વિચારી રહ્યા છો કે પછી બીજી કોઈ Samsung ની Product માં interest ધરાવો છો જેમ કે Watch, Tablet કે Laptop?",
    "samsung_step5_ask_address.raw": "ખૂબ સરસ. મને કહો, તમે કયા area માં રહો છો જેથી ત્યાંના નજીકના Samsung Store ની team તમારો સંપર્ક કરી શકે.",
    "samsung_step6_closing.raw": "આભાર. નજીકના Samsung Store ની team ટૂંક સમયમાં તમારો સંપર્ક કરશે. તમારો કિંમતી સમય આપવા બદલ આભાર. તમારો દિવસ શુભ રહે.",
    "samsung_rejection.raw": "કોઈ વાંધો નહીં. તમારો સમય આપવા બદલ આભાર. તમારો દિવસ શુભ રહે.",
    "samsung_llm_greeting_static.raw": "નમસ્તે! હું વીટેક સેમસંગ કેફેમાંથી નાવ્યા બોલું છું. શું મારી વાત તમારી સાથે થઈ શકે?",
    "samsung_llm_greeting_body.raw": "હું વીટેક સેમસંગ કેફેમાંથી નાવ્યા બોલું છું. શું મારી વાત તમારી સાથે થઈ શકે?"
}

def generate_tts_file(filename, text):
    subfolder = "samsung_bot"
    target_dir = os.path.join("mp3_responses", subfolder)
    os.makedirs(target_dir, exist_ok=True)
    file_path = os.path.join(target_dir, filename)

    # Method 1: Sarvam AI
    if SARVAM_API_KEY:
        try:
            api_url = "https://api.sarvam.ai/text-to-speech/stream"
            headers = {
                "api-subscription-key": SARVAM_API_KEY,
                "Content-Type": "application/json"
            }
            payload = {
                "text": text,
                "target_language_code": "gu-IN",
                "speaker": "ishita",
                "model": "bulbul:v3",
                "pace": 1.05,
                "temperature": 0.75,
                "speech_sample_rate": 8000,
                "output_audio_codec": "mulaw",
                "enable_preprocessing": False
            }
            response = requests.post(api_url, headers=headers, json=payload, timeout=20)
            response.raise_for_status()
            audio_data = response.content
            if audio_data:
                with open(file_path, "wb") as f:
                    f.write(audio_data)
                print(f"[OK] Voice Generated (Sarvam - {payload['speaker']}): {file_path}")
                return
        except Exception as e:
            print(f"[WARN] Failed to generate {filename} via Sarvam: {e}. Trying Azure...")

    # Method 2: Azure Speech Service (Female Gujarati: gu-IN-DhwaniNeural)
    if AZURE_SPEECH_KEY and AZURE_SPEECH_REGION:
        try:
            import azure.cognitiveservices.speech as speechsdk
            speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_SPEECH_REGION)
            speech_config.speech_synthesis_voice_name = "gu-IN-DhwaniNeural"
            speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Raw8Khz16BitMonoPcm)
            
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
            result = synthesizer.speak_text_async(text).get()
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                pcm = result.audio_data
                ulaw = audioop.lin2ulaw(pcm, 2)
                with open(file_path, "wb") as f:
                    f.write(ulaw)
                print(f"[OK] Voice Generated (Azure - gu-IN-DhwaniNeural): {file_path}")
                return
            else:
                print(f"[WARN] Azure synthesis result: {result.reason}")
        except Exception as e:
            print(f"[WARN] Failed to generate {filename} via Azure: {e}")

    print(f"❌ Could not generate audio file {filename} (no available credentials).")

def main():
    print("Generating Naavya Samsung Store Voice Bot Gujarati Audio Assets...")
    for filename, text in AUDIO_ASSETS.items():
        generate_tts_file(filename, text)
    print("All audio files processed.")

if __name__ == "__main__":
    main()
