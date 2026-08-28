# scratch/generate_raahi_greeting.py

import os
import sys
import requests

api_key = None
env_path = os.path.join(os.getcwd(), ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("SARVAM_API_KEY="):
                api_key = line.split("=", 1)[1].strip().strip('"').strip("'")

if not api_key:
    api_key = os.getenv("SARVAM_API_KEY")

api_url = "https://api.sarvam.ai/text-to-speech/stream"

headers = {
    "api-subscription-key": api_key,
    "Content-Type": "application/json"
}

text = "Namaste! Main Raahi, Triple I E M se. Aapka naam?"

payload = {
    "text": text,
    "target_language_code": "hi-IN",
    "speaker": "shreya",
    "model": "bulbul:v3",
    "pace": 1.18,
    "speech_sample_rate": 8000,
    "output_audio_codec": "mulaw",
    "enable_preprocessing": False
}

print(f"Synthesizing Raahi greeting: '{text}' using Sarvam AI...")
response = requests.post(api_url, headers=headers, json=payload, timeout=15)
response.raise_for_status()

ulaw_bytes = response.content

out_dir = os.path.join(os.getcwd(), "mp3_responses", "raahi_iiiem_bot")
os.makedirs(out_dir, exist_ok=True)
out_file = os.path.join(out_dir, "raahi_greeting.raw")

with open(out_file, "wb") as f:
    f.write(ulaw_bytes)

print(f"[OK] Saved u-law raw audio to {out_file} ({len(ulaw_bytes)} bytes)")
