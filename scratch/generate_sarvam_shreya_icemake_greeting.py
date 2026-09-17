import os
import sys
import requests
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
SARVAM_URL = "https://api.sarvam.ai/text-to-speech/stream"

def generate_sarvam_shreya_greeting():
    if not SARVAM_API_KEY:
        print("❌ SARVAM_API_KEY missing!")
        return

    print("🎙️ Generating Dual-Lang Sarvam 'shreya' Greeting (English + Hindi)...")

    headers = {
        "api-subscription-key": SARVAM_API_KEY,
        "Content-Type": "application/json"
    }

    # Part 1: English intro with en-IN model
    payload_en = {
        "text": "Hello! Welcome to Ice Make twenty four seven service support.",
        "target_language_code": "en-IN",
        "speaker": "shreya",
        "model": "bulbul:v3",
        "pace": 0.98,
        "speech_sample_rate": 8000,
        "output_audio_codec": "alaw",
        "enable_preprocessing": True
    }

    # Part 2: Hindi language selection prompt with hi-IN model
    payload_hi = {
        "text": "आप किस भाषा में बात करना पसंद करेंगे?",
        "target_language_code": "hi-IN",
        "speaker": "shreya",
        "model": "bulbul:v3",
        "pace": 1.0,
        "speech_sample_rate": 8000,
        "output_audio_codec": "alaw",
        "enable_preprocessing": True
    }

    res_en = requests.post(SARVAM_URL, json=payload_en, headers=headers, timeout=20)
    if res_en.status_code != 200:
        print(f"❌ Sarvam EN failed: {res_en.status_code}, {res_en.text}")
        return

    res_hi = requests.post(SARVAM_URL, json=payload_hi, headers=headers, timeout=20)
    if res_hi.status_code != 200:
        print(f"❌ Sarvam HI failed: {res_hi.status_code}, {res_hi.text}")
        return

    alaw_en = res_en.content
    alaw_hi = res_hi.content

    # Silence frame in G.711 A-law is b'\xd5'
    silence_leading = b'\xd5' * 4000  # 500ms leading silence for channel un-muting
    silence_pause = b'\xd5' * 2000    # 250ms pause between English & Hindi

    final_alaw = silence_leading + alaw_en + silence_pause + alaw_hi

    out_file1 = os.path.join(PROJECT_ROOT, "icemake_bot", "icemake_greeting.raw")
    out_file2 = os.path.join(PROJECT_ROOT, "mp3_responses", "icemake_bot", "icemake_greeting.raw")
    out_file3 = os.path.join(PROJECT_ROOT, "mp3_responses", "icemake_greeting.raw")
    out_file4 = os.path.join(PROJECT_ROOT, "icemake_greeting.raw")

    for path in [out_file1, out_file2, out_file3, out_file4]:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(final_alaw)
        print(f"✅ Saved studio Sarvam 'shreya' A-law greeting to: {path} ({len(final_alaw)} bytes)")

if __name__ == "__main__":
    generate_sarvam_shreya_greeting()
