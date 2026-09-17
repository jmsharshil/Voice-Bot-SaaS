# kia_syros_bot/audio_generator.py

import os
import sys
import audioop
import requests
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
SARVAM_URL = "https://api.sarvam.ai/text-to-speech/stream"

AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = "aSFxChEgBmCyExpaDqHd" # Kanika (Female Voice)

def trim_trailing_silence(pcm_data: bytes, threshold: int = 150) -> bytes:
    try:
        import numpy as np
        samples = np.frombuffer(pcm_data, dtype=np.int16)
        active_indices = np.where(np.abs(samples) > threshold)[0]
        if len(active_indices) == 0:
            return pcm_data
        
        last_active_idx = active_indices[-1]
        padding_samples = 2400
        end_idx = min(len(samples), last_active_idx + padding_samples)
        return samples[:end_idx].tobytes()
    except Exception as e:
        print(f"Trim silence error: {e}")
        return pcm_data

def trim_ulaw_silence(ulaw_data: bytes, threshold: int = 150) -> bytes:
    try:
        pcm = audioop.ulaw2lin(ulaw_data, 2)
        trimmed_pcm = trim_trailing_silence(pcm, threshold)
        return audioop.lin2ulaw(trimmed_pcm, 2)
    except Exception as e:
        print(f"Trim ulaw silence error: {e}")
        return ulaw_data

def generate_via_sarvam(text) -> bytes:
    if not SARVAM_API_KEY:
        raise ValueError("SARVAM_API_KEY not found in env")

    headers = {
        "api-subscription-key": SARVAM_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "text": text,
        "target_language_code": "hi-IN",
        "speaker": "shreya", 
        "model": "bulbul:v3",
        "pace": 1.05,
        "speech_sample_rate": 8000,
        "output_audio_codec": "mulaw",
        "enable_preprocessing": True
    }
    
    try:
        response = requests.post(SARVAM_URL, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        return response.content
    except requests.exceptions.HTTPError as http_err:
        print(f"   [Sarvam API Error Response]: {response.text}")
        raise http_err

def generate_via_elevenlabs(text) -> bytes:
    if not ELEVENLABS_API_KEY:
        raise ValueError("ELEVENLABS_API_KEY not found in env")
    
    from elevenlabs.client import ElevenLabs
    from elevenlabs.types.voice_settings import VoiceSettings
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    
    audio_generator = client.text_to_speech.convert(
        voice_id=ELEVENLABS_VOICE_ID,
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
        raise ValueError("ElevenLabs returned empty audio")
        
    if len(pcm) % 2 != 0:
        pcm = pcm[:-1]
    
    ulaw = audioop.lin2ulaw(pcm, 2)
    return ulaw

def generate_via_azure(text) -> bytes:
    if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
        raise ValueError("AZURE_SPEECH_KEY or AZURE_SPEECH_REGION not found in env")
        
    import azure.cognitiveservices.speech as speechsdk
    speech_config = speechsdk.SpeechConfig(
        subscription=AZURE_SPEECH_KEY,
        region=AZURE_SPEECH_REGION
    )
    speech_config.speech_synthesis_voice_name = "hi-IN-SwaraNeural"
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Raw8Khz16BitMonoPcm
    )

    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=None
    )

    ssml = f"""
    <speak version='1.0' xmlns="http://www.w3.org/2001/10/synthesis" 
           xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang='hi-IN'>
        <voice name='hi-IN-SwaraNeural'>
            <mstts:silence type="Leading" value="150ms"/>
            <prosody rate='0%' pitch='0%' volume='0%'>
                {text}
            </prosody>
            <mstts:silence type="Tailing" value="50ms"/>
        </voice>
    </speak>
    """
    result = synthesizer.speak_ssml_async(ssml).get()
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        pcm = result.audio_data
        ulaw = audioop.lin2ulaw(pcm, 2)
        return ulaw
    else:
        raise Exception(f"Azure Speech synthesis failed: {result.reason}")

def generate_tts_file(filename, text):
    subfolder = "kia_syros_bot"
    target_dir = os.path.join("mp3_responses", subfolder)
    os.makedirs(target_dir, exist_ok=True)
    file_path = os.path.join(target_dir, filename)

    # 1. Try Sarvam AI
    try:
        print(f"🎙️ Generating '{filename}' via Sarvam AI...")
        audio_data = generate_via_sarvam(text)
        if audio_data:
            audio_data = trim_ulaw_silence(audio_data)
            with open(file_path, "wb") as f:
                f.write(audio_data)
            print(f"[OK] Voice Generated via Sarvam: {file_path}")
            return
    except Exception as sarvam_err:
        print(f"⚠️ Sarvam AI generation failed: {sarvam_err}")

    # 2. Try ElevenLabs
    try:
        print(f"🔄 Falling back: Generating '{filename}' via ElevenLabs...")
        audio_data = generate_via_elevenlabs(text)
        if audio_data:
            with open(file_path, "wb") as f:
                f.write(audio_data)
            print(f"[OK] Voice Generated via ElevenLabs: {file_path}")
            return
    except Exception as elevenlabs_err:
        print(f"⚠️ ElevenLabs generation failed: {elevenlabs_err}")

    # 3. Fall back to Azure Speech
    try:
        print(f"🔄 Falling back: Generating '{filename}' via Azure Speech...")
        audio_data = generate_via_azure(text)
        if audio_data:
            with open(file_path, "wb") as f:
                f.write(audio_data)
            print(f"[OK] Voice Generated via Azure: {file_path}")
            return
    except Exception as azure_err:
        print(f"❌ [FAIL] All TTS systems failed for {filename}: {azure_err}")

if __name__ == "__main__":
    print("Generating Kia Syros Bot Audio Assets (MP3-First Flow)...")
    assets = [
        # Conversation flow audio files
        ("kia_syros_greeting.raw", "Hello, kya meri baat aapse ho rahi hai?"),
        ("kia_syros_pitch.raw", "Main Westcoast Kia se bol rahi hoon. Aapne pehle hamare dealership par enquiry ki thi. Isliye hum aapko all-new Kia Syros EV ke exclusive test drive experience ke liye invite karna chahte hain. Toh kya aap interested hain?"),
        ("kia_syros_callback_confirm.raw", "Thank you! Kya main confirm kar sakti hoon ki isi number par hamare EV Sales Expert aapse contact karein?"),
        ("kia_syros_booking_confirmed.raw", "Thank you. Hamari EV Sales Expert team aapse jald hi contact karegi aur aage ki process mein assist karegi. Have a great day!"),
        ("kia_syros_rejection.raw", "No problem. Agar aapko aage kabhi bhi Kia cars ki zaroorat ho, toh humse contact kar sakte hain. Have a great day!"),
        ("kia_syros_redirect.raw", "Iski complete aur accurate details hamare EV Sales Expert aapko callback mein explain karenge. Main unse request raise kar deti hoon ki wo aapse jaldi contact karein. Toh kya main aapka callback schedule kar doon?"),
        ("kia_syros_persuade.raw", "Ek chhoti si conversation mein hamare EV Sales Expert aapko saari information denge aur agar aap interested honge toh wo test drive bhi arrange kar denge. Kya main unse aapke liye callback schedule kar doon?"),
        ("kia_syros_alt_number.raw", "Ji bilkul, aap mujhe wo number bata dijiye, main note kar leti hoon."),
    ]

    for filename, text in assets:
        generate_tts_file(filename, text)

    print("\n[DONE] Kia Syros Bot audio assets built successfully.")
