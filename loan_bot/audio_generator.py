import os
import sys
import audioop
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.types.voice_settings import VoiceSettings

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

ELEVENLABS_CLIENT = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

# Kanika Neural Voice ID
ELEVENLABS_VOICE_MAP = {
    "en": "aSFxChEgBmCyExpaDqHd",
    "hi": "aSFxChEgBmCyExpaDqHd",
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

def generate_tts_file(filename, text, lang="hi"):
    subfolder = "loan_bot"
    target_dir = os.path.join("mp3_responses", subfolder)
    os.makedirs(target_dir, exist_ok=True)
    
    file_path = os.path.join(target_dir, filename)

    if lang == "hi":
        import requests
        api_key = os.getenv("SARVAM_API_KEY")
        api_url = "https://api.sarvam.ai/text-to-speech/stream"
        
        headers = {
            "api-subscription-key": api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "target_language_code": "hi-IN",
            "speaker": "shubh",
            "model": "bulbul:v3",
            "pace": 1.15,
            "speech_sample_rate": 8000,
            "output_audio_codec": "mulaw",
            "enable_preprocessing": True
        }
        
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=20)
            response.raise_for_status()
            
            audio_data = response.content
            if not audio_data:
                print(f"❌ Sarvam returned empty audio for: {filename}")
                return

            with open(file_path, "wb") as f:
                f.write(audio_data)

            print(f"[OK] Voice Generated (Sarvam): {file_path}")
            return
        except Exception as e:
            print(f"[FAIL] Failed to generate {filename} via Sarvam: {e}. Falling back to ElevenLabs...")

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

        print(f"[OK] Voice Generated (ElevenLabs): {file_path}")

    except Exception as e:
        print(f"[FAIL] Failed to generate {filename}: {e}")

if __name__ == "__main__":
    target_filters = sys.argv[1:] if len(sys.argv) > 1 else []
    
    if target_filters:
        print(f"Generating Loan Bot audio only for files matching: {target_filters}")
    else:
        print("Generating JMS Bank Loan Bot Multilingual Flow Audio Assets via ElevenLabs...")

    assets = [
        ("loan_step1_greeting.raw", "Hello! Namaste... main JMS Bank ki taraf se Rahul bol raha hoon. Aaj main aapko hamare exclusive loan products ke baare mein batana chahta hoon — home loan, business loan, personal loan aur bahut kuch. Kya aap apne kisi financial goal ke liye loan explore kar rahe hain?", "hi"),
        ("loan_step2_discover_type.raw", "Wonderful! JMS Bank mein hum aapki har zaroorat ke liye tailor-made loan solutions offer karte hain — chahe wo dream home ho, apna business grow karna ho, ya koi personal zaroorat. Aap kaunsa loan option explore karna chahenge?", "hi"),
        ("loan_step3_discover_amount.raw", "Great choice! aapko approximately kitne amount ka loan chahiye? Exact figure nahi pata toh koi baat nahi, ek rough idea bhi kaafi hai — hum uske hisaab se best plan suggest kar sakte hain.", "hi"),
        ("loan_step4_closing.raw", "Excellent! Aapki saari details note kar li gayi hain. Hamari expert team bahut jald aapse connect karegi aur aapke liye best loan offer ready karegi. JMS Bank choose karne ke liye bahut bahut shukriya!", "hi"),
        ("loan_step_rejection.raw", "Bilkul theek hai, koi problem nahi! Jab bhi aapko zaroorat ho, JMS Bank hamesha aapke liye available hai. Apna precious time dene ke liye dil se shukriya. Aapka din bahut accha jaye!", "hi")
    ]

    generated_count = 0
    for filename, text, lang in assets:
        if target_filters and not any(t_filter in filename for t_filter in target_filters):
            continue
        generate_tts_file(filename, text, lang)
        generated_count += 1

    print(f"\n[DONE] Generated {generated_count} Loan Bot audio asset(s).")
