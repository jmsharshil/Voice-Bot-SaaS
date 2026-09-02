import os
import sys
import base64
import io
import wave
import numpy as np
import requests
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def pcm2ulaw(pcm_bytes: bytes) -> bytes:
    samples = np.frombuffer(pcm_bytes, dtype=np.int16)
    BIAS = 0x84
    samples = np.clip(samples, -32635, 32635)
    sign = (samples < 0).astype(np.uint8)
    mag = np.abs(samples) + BIAS
    
    exponent = np.zeros_like(mag, dtype=np.uint8)
    for i in range(7, -1, -1):
        mask = 1 << (i + 3)
        condition = (mag >= mask) & (exponent == 0)
        exponent[condition] = i + 1

    exponent = np.clip(exponent, 1, 8) - 1
    mantissa = ((mag.astype(np.int32) >> (exponent + 3)) & 0x0F).astype(np.uint8)
    ulaw = ~( (sign << 7) | (exponent << 4) | mantissa ) & 0xFF
    return ulaw.astype(np.uint8).tobytes()

def generate_icemake_greeting():
    greeting_text = "Welcome to Ice Make twenty four by seven service support. आप किस भाषा में बात करना पसंद करेंगे?"
    print(f"🎙️ Generating pre-rendered Ice Make greeting audio for: '{greeting_text}'")

    headers = {
        "api-subscription-key": SARVAM_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "inputs": [greeting_text],
        "target_language_code": "hi-IN",
        "speaker": "shreya",
        "model": "bulbul:v3",
        "pace": 1.05,
        "speech_sample_rate": 8000,
        "enable_preprocessing": True
    }

    res = requests.post("https://api.sarvam.ai/text-to-speech", json=payload, headers=headers, timeout=15)
    if res.status_code != 200:
        print(f"❌ Failed to generate TTS from Sarvam. Status: {res.status_code}, Body: {res.text}")
        return

    data = res.json()
    audios = data.get("audios", [])
    if not audios:
        print("❌ No audio returned from Sarvam")
        return

    wav_bytes = base64.b64decode(audios[0])

    with wave.open(io.BytesIO(wav_bytes), 'rb') as wav:
        frames = wav.readframes(wav.getnframes())

    ulaw_audio = pcm2ulaw(frames)

    out_dir = os.path.join(PROJECT_ROOT, "icemake_bot")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "icemake_greeting.raw")

    with open(out_file, "wb") as f:
        f.write(ulaw_audio)

    print(f"✅ Pre-rendered Ice Make greeting saved to {out_file} ({len(ulaw_audio)} bytes)")

if __name__ == "__main__":
    generate_icemake_greeting()
