# shreyas_bot/audio_generator.py

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
ELEVENLABS_VOICE_ID = "aSFxChEgBmCyExpaDqHd" # Kanika (Female English Voice)

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
        "target_language_code": "en-IN",
        "speaker": "shreya", # Matches the bot name 'Shreya'
        "model": "bulbul:v3",
        "pace": 1.0,
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
    
    # Encode pcm to u-law
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
    speech_config.speech_synthesis_voice_name = "en-IN-AartiNeural"
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Raw8Khz16BitMonoPcm
    )

    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=None
    )

    ssml = f"""
    <speak version='1.0' xmlns="http://www.w3.org/2001/10/synthesis" 
           xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang='en-IN'>
        <voice name='en-IN-AartiNeural'>
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
    subfolder = "shreyas_bot"
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
    print("Generating Shreyas Foundation Sports Bot Audio Assets...")
    assets = [
        ("shreyas_step1_greeting.raw", "namaste, Welcome to Shreyas Foundation Sports and Outreach Programs. We offer horse riding, skating, football, life-skills, and communication programs, open to all. Which one would your child like to try?"),
        
        # 1. Program Selection
        ("filler_1_a.raw", "Excellent choice! Let me check the batch timings for you."),
        ("filler_1_b.raw", "That is a great program! Let me check the timings and details."),
        ("filler_1_c.raw", "Wonderful choice! Let see what slots we have available for that."),
        ("filler_1_d.raw", "Great! Let me check the schedules for this activity."),
        ("filler_1_e.raw", "Perfect! Let me pull up the class timings for you."),
        
        # 2. Age / Timing
        ("filler_2_a.raw", "Perfect! Let me check the schedules for this age group."),
        ("filler_2_b.raw", "Alright! Let me see what batch options we have for this age."),
        ("filler_2_c.raw", "Got it! Let me check the available time slots for that age."),
        ("filler_2_d.raw", "Great! Let me check the batch timings for that age group."),
        ("filler_2_e.raw", "Sure! Let me check our schedule for this specific age."),
        
        # 3. WhatsApp Consent (Neutral Acknowledgment)
        ("filler_3_a.raw", "Yes sure, just a second..."),
        ("filler_3_b.raw", "Alright, I am checking right now..."),
        ("filler_3_c.raw", "Sure, I'll let you know in just a moment..."),
        ("filler_3_d.raw", "Yes, absolutely, just a minute..."),
        ("filler_3_e.raw", "Okay, let me get the details ready..."),
        
        # 4. Question / Inquiry
        ("filler_4_a.raw", "Good question! Let me look up the details for you."),
        ("filler_4_b.raw", "Let me verify that information for you."),
        ("filler_4_c.raw", "Interesting question! Let me check the system details."),
        ("filler_4_d.raw", "Let me look that up for you right now."),
        ("filler_4_e.raw", "Sure, let me check the details for that."),
        
        # 5. Default / Fallback
        ("filler_5_a.raw", "Sure, please give me a moment to check."),
        ("filler_5_b.raw", "Alright, let me look into that for you."),
        ("filler_5_c.raw", "Sure, let me check the details on that."),
        ("filler_5_d.raw", "Okay, let me find the right details for you."),
        ("filler_5_e.raw", "Sure, let me look that up for you."),
    ]

    for filename, text in assets:
        generate_tts_file(filename, text)

    print("\n[DONE] Shreyas Bot audio assets built successfully.")
