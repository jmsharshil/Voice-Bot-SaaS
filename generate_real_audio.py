# import os
# import audioop
# import azure.cognitiveservices.speech as speechsdk
# from dotenv import load_dotenv

# load_dotenv()

# AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
# AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

# # EXACT match to consumers.py
# VOICE_NAME = "en-IN-AartiNeural"

# def _amplify_pcm(pcm_data: bytes, gain: float = 2.0) -> bytes:
#     """Matches the exact amplification used in consumers.py"""
#     try:
#         return audioop.mul(pcm_data, 2, gain)
#     except Exception as e:
#         print(f"Amplify error: {e}")
#         return pcm_data

# def generate_tts_file(filename, text):
#     speech_config = speechsdk.SpeechConfig(
#         subscription=AZURE_SPEECH_KEY,
#         region=AZURE_SPEECH_REGION
#     )
#     speech_config.speech_synthesis_voice_name = VOICE_NAME

#     # Request EXACTLY what consumers.py requests
#     speech_config.set_speech_synthesis_output_format(
#         speechsdk.SpeechSynthesisOutputFormat.Raw8Khz16BitMonoPcm
#     )

#     synthesizer = speechsdk.SpeechSynthesizer(
#         speech_config=speech_config,
#         audio_config=None
#     )

#     # Use exact same SSML prosody (rate=0%, pitch=0%, volume=0%)
#     ssml = f"""
#     <speak version='1.0' xmlns="http://www.w3.org/2001/10/synthesis" 
#            xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang='en-IN'>
#         <voice name='{VOICE_NAME}'>
#             <mstts:silence type="Leading" value="150ms"/>
#             <prosody rate='0%' pitch='0%' volume='0%'>
#                 {text}
#             </prosody>
#             <mstts:silence type="Tailing" value="50ms"/>
#         </voice>
#     </speak>
#     """

#     result = synthesizer.speak_ssml_async(ssml).get()

#     if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
#         # 1. Get raw 16-bit PCM
#         pcm = result.audio_data
        
#         # 2. Apply the exact 2.0x gain from consumers.py
#         pcm = _amplify_pcm(pcm, gain=2.0)
        
#         # 3. Encode to u-law (G.711) exactly like consumers.py
#         ulaw = audioop.lin2ulaw(pcm, 2)
        
#         # 4. Save to .raw
#         os.makedirs("mp3_responses", exist_ok=True)
#         file_path = os.path.join("mp3_responses", filename)
#         with open(file_path, "wb") as f:
#             f.write(ulaw)
            
#         print(f"Voice Generated: {file_path}")
#     else:
#         print(f"Failed: {result.reason}")

# if __name__ == "__main__":
#     print("Generating EXACT Consumer-Match Voice Assets...")
#     assets = [
#         ("test_drive_offer.raw", "Great! Kya aap iski test drive lena pasand karenge?"),
#         ("ask_venue_showroom_home.raw", "Great! Aap test drive kahan pasand karenge, showroom aana chahenge ya ghar par?"),
#         ("ask_address_time.raw", "Theek hai, kis time par aana pasand karenge?"),
#         ("ask_showroom_time.raw", "Sahi decision. Kis time par showroom aana pasand karenge?"),
#         ("ask_future_interest.raw", "Koi baat nahi, kya main aapko gaadi ki details WhatsApp par bhej doon?"),
#         ("kia_pricing_general.raw", "Kia Seltos ki price barah lakh se shuru hoti hai. Kya main aapko details bhejoon?"),
#         ("showroom_location.raw", "Hamara showroom highway par hai. Main aapko location bhej deti hoon."),
#         ("greeting.raw", "Hello, main Kia motors se baat kar rahi hoon. Kya meri baat Ayushi se ho rahi hai?")
#     ]

#     for filename, text in assets:
#         generate_tts_file(filename, text)
#     print("Done! The Fast-Path voice now matches the Consumer voice 100%.")













import os
import audioop
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.types.voice_settings import VoiceSettings

load_dotenv()

ELEVENLABS_CLIENT = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

VOICE_ID = "aSFxChEgBmCyExpaDqHd"  # Kanika


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


def generate_tts_file(filename, text):
    file_path = os.path.join("mp3_responses", filename)
    # Always regenerate to apply updated voice settings
    # if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
    #     print(f"⏭️  Skipping (already exists): {filename}")
    #     return

    try:
        # pcm_8000 = native 8kHz 16-bit PCM mono — no MP3 decode, no pydub needed
        audio_generator = ELEVENLABS_CLIENT.text_to_speech.convert(
            voice_id=VOICE_ID,
            text=text,
            model_id="eleven_multilingual_v2",  # More natural than turbo
            output_format="pcm_8000",            # Native 8kHz PCM for telephony
            voice_settings=VoiceSettings(
                stability=0.55,          # Natural human-like tone variation
                similarity_boost=0.75,   # Balanced — reduces artifacts & over-enunciation
                style=0.00,
                use_speaker_boost=False, # Softer, warmer — removes loud "studio" effect
                speed=1.00               # Medium speed — natural pace on telephony
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
    print("Generating Consumer-Match Voice Assets via ElevenLabs...")
    assets = [
        ("test_drive_offer.raw",        "Great! Kya aap iski test drive lena pasand karenge?"),
        ("ask_venue_showroom_home.raw",  "Great! Aap test drive kahan pasand karenge, showroom aana chahenge ya ghar par?"),
        ("ask_address_time.raw",         "Theek hai, kis time par aana pasand karenge?"),
        ("ask_showroom_time.raw",        "Sahi decision. Kis time par showroom aana pasand karenge?"),
        ("ask_future_interest.raw",      "Koi baat nahi, kya main aapko gaadi ki details WhatsApp par bhej doon?"),
        ("kia_pricing_general.raw",      "Kia Seltos ki price barah lakh se shuru hoti hai. Kya main aapko details bhejoon?"),
        ("showroom_location.raw",        "Hamara showroom highway par hai. Main aapko location bhej deti hoon."),
        ("greeting.raw",                 "Hello, main Kia motors se baat kar rahi hoon. Kya meri baat Ayushi se ho rahi hai?"),
    ]

    for filename, text in assets:
        generate_tts_file(filename, text)

    print("\nDone!")