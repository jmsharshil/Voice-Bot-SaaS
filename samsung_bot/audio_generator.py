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
    "samsung_step1_greeting.raw": "નમસ્તે! હું નીલ છું. હું VTech Samsung Cafe તરફથી વાત કરી રહ્યો છું. શું મારી વાત Customer જી સાથે થઈ રહી છે?",
    "samsung_step2_ask_consent.raw": "નમસ્તે Customer જી. તમે થોડા દિવસ પહેલા Samsung Product માટે ઇન્ટરેસ્ટ દર્શાવ્યો હતો એટલે તમને કોલ કર્યો છે. શું તમારી સાથે 2 મિનિટ વાત થઈ શકે?",
    "samsung_step3_ask_phone.raw": "ઓકે. તો શું હું જાણી શકું કે તમે અત્યારે કયો ફોન વાપરી રહ્યા છો?",
    "samsung_step4_ask_interest.raw": "ઓકે. તો શું તમે નવો સ્માર્ટફોન લેવાનું વિચારી રહ્યા છો કે પછી બીજી કોઈ Samsung ની Product માં ઇન્ટરેસ્ટ ધરાવો છો જેમ કે Watch, Tablet કે Laptop?",
    "samsung_step5_ask_address.raw": "ખૂબ સરસ. મને કહો, તમે કયા એરિયામાં રહો છો જેથી ત્યાંના નજીકના Samsung Store ની ટીમ તમારો સંપર્ક કરી શકે.",
    "samsung_step6_closing.raw": "આભાર. નજીકના Samsung Store ની ટીમ ટૂંક સમયમાં તમારો સંપર્ક કરશે. તમારો કિંમતી સમય આપવા બદલ આભાર. તમારો દિવસ શુભ રહે.",
    "samsung_rejection.raw": "કોઈ વાંધો નહીં. તમારો સમય આપવા બદલ આભાર. તમારો દિવસ શુભ રહે."
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
                "speaker": "shubh",
                "model": "bulbul:v3",
                "pace": 1.15,
                "speech_sample_rate": 8000,
                "output_audio_codec": "mulaw",
                "enable_preprocessing": True
            }
            response = requests.post(api_url, headers=headers, json=payload, timeout=20)
            response.raise_for_status()
            audio_data = response.content
            if audio_data:
                with open(file_path, "wb") as f:
                    f.write(audio_data)
                print(f"[OK] Voice Generated (Sarvam - Shubh): {file_path}")
                return
        except Exception as e:
            print(f"[WARN] Failed to generate {filename} via Sarvam: {e}. Trying Azure...")

    # Method 2: Azure Speech Service (Male Gujarati: gu-IN-NiranjanNeural)
    if AZURE_SPEECH_KEY and AZURE_SPEECH_REGION:
        try:
            import azure.cognitiveservices.speech as speechsdk
            speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_SPEECH_REGION)
            speech_config.speech_synthesis_voice_name = "gu-IN-NiranjanNeural"
            speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Raw8Khz16BitMonoPcm)
            
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
            result = synthesizer.speak_text_async(text).get()
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                pcm = result.audio_data
                ulaw = audioop.lin2ulaw(pcm, 2)
                with open(file_path, "wb") as f:
                    f.write(ulaw)
                print(f"[OK] Voice Generated (Azure - gu-IN-NiranjanNeural): {file_path}")
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
