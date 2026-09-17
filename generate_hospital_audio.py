import os
import audioop
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.types.voice_settings import VoiceSettings

load_dotenv()

# Initialize ElevenLabs Client
ELEVENLABS_CLIENT = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

# Use Sophia/Kanika voice (same as defined in other strategies)
VOICE_ID = "aSFxChEgBmCyExpaDqHd" 


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


def generate_tts_file(filename, text):
    file_path = os.path.join("mp3_responses", filename)

    try:
        # pcm_8000 = native 8kHz 16-bit PCM mono for telephony
        audio_generator = ELEVENLABS_CLIENT.text_to_speech.convert(
            voice_id=VOICE_ID,
            text=text,
            model_id="eleven_multilingual_v2",
            output_format="pcm_8000",
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

        os.makedirs("mp3_responses", exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(ulaw)

        print(f"[OK] Voice Generated: {file_path}")

    except Exception as e:
        print(f"[FAIL] Failed to generate {filename}: {e}")


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("Generating Hospital Appointment Scheduler Audio Assets via ElevenLabs...")
    
    assets = [
        ("hosp_step1_greeting.raw", "Hello! I am Sophia calling from City Clinic. We received your booking request for tomorrow. Can we confirm your appointment?"),
        ("hosp_step2_ask_slot.raw", "Great! Would you prefer a morning session between 10 to 12, or an afternoon session between 2 to 4?"),
        ("hosp_step3_closing.raw", "Perfect! Your slot has been confirmed. We have sent the confirmation details on WhatsApp. Thank you, take care!"),
        ("hosp_step_cancellation.raw", "Understood. We have cancelled your request. Have a good day. Goodbye!"),
    ]

    for filename, text in assets:
        generate_tts_file(filename, text)

    print("\n[DONE] Hospital flow audio is ready.")
