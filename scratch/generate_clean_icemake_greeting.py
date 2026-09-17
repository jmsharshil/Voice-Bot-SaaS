import os
import sys
import requests
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
SARVAM_URL = "https://api.sarvam.ai/text-to-speech/stream"

def generate_clean_greeting():
    greeting_text = "Welcome to Ice Make twenty four by seven service support. आप किस भाषा में बात करना पसंद करेंगे?"
    print(f"🎙️ Generating HD Studio Quality Ice Make greeting via Sarvam mulaw stream: '{greeting_text}'")

    headers = {
        "api-subscription-key": SARVAM_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "text": greeting_text,
        "target_language_code": "hi-IN",
        "speaker": "shreya",
        "model": "bulbul:v3",
        "pace": 1.05,
        "speech_sample_rate": 8000,
        "output_audio_codec": "mulaw",
        "enable_preprocessing": True
    }

    res = requests.post(SARVAM_URL, json=payload, headers=headers, timeout=20)
    if res.status_code != 200:
        print(f"❌ Failed to generate TTS from Sarvam. Status: {res.status_code}, Body: {res.text}")
        return

    mulaw_bytes = res.content

    out_file1 = os.path.join(PROJECT_ROOT, "icemake_bot", "icemake_greeting.raw")
    out_file2 = os.path.join(PROJECT_ROOT, "mp3_responses", "icemake_bot", "icemake_greeting.raw")
    out_file3 = os.path.join(PROJECT_ROOT, "mp3_responses", "icemake_greeting.raw")
    out_file4 = os.path.join(PROJECT_ROOT, "icemake_greeting.raw")

    os.makedirs(os.path.dirname(out_file1), exist_ok=True)
    os.makedirs(os.path.dirname(out_file2), exist_ok=True)

    for path in [out_file1, out_file2, out_file3, out_file4]:
        with open(path, "wb") as f:
            f.write(mulaw_bytes)
        print(f"✅ Saved clean mulaw audio to: {path} ({len(mulaw_bytes)} bytes)")

if __name__ == "__main__":
    generate_clean_greeting()
