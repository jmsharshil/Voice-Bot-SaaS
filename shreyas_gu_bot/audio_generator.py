# shreyas_gu_bot/audio_generator.py

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
ELEVENLABS_VOICE_ID = "aSFxChEgBmCyExpaDqHd"

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
        "target_language_code": "gu-IN",
        "speaker": "ishita", # Best Indian Gujarati humanised female voice
        "model": "bulbul:v3",
        "pace": 1.16,
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
            speed=1.16
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
    speech_config.speech_synthesis_voice_name = "gu-IN-DhwaniNeural"
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Raw8Khz16BitMonoPcm
    )

    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=None
    )

    ssml = f"""
    <speak version='1.0' xmlns="http://www.w3.org/2001/10/synthesis" 
           xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang='gu-IN'>
        <voice name='gu-IN-DhwaniNeural'>
            <mstts:silence type="Leading" value="150ms"/>
            <prosody rate='+16%' pitch='0%' volume='0%'>
                {text}
            </prosody>
        </voice>
    </speak>
    """
    
    result = synthesizer.speak_ssml_async(ssml).get()
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        # result.audio_data contains 8kHz 16-bit Mono PCM
        pcm = result.audio_data
        if len(pcm) % 2 != 0:
            pcm = pcm[:-1]
        ulaw = audioop.lin2ulaw(pcm, 2)
        return ulaw
    else:
        raise ValueError(f"Azure Speech Synthesis failed: {result.reason}")

def generate_tts_file(filename, text):
    os.makedirs(os.path.join("mp3_responses", "shreyas_gu_bot"), exist_ok=True)
    file_path = os.path.join("mp3_responses", "shreyas_gu_bot", filename)

    print(f"🎙️ Generating '{filename}' via Sarvam AI...")
    try:
        audio_data = generate_via_sarvam(text)
        audio_data = trim_ulaw_silence(audio_data, threshold=150)
        with open(file_path, "wb") as f:
            f.write(audio_data)
        print(f"[OK] Voice Generated via Sarvam: {file_path}")
        return
    except Exception as sarvam_err:
        print(f"⚠️ Sarvam AI generation failed: {sarvam_err}")
        
    print(f"🔄 Falling back: Generating '{filename}' via ElevenLabs...")
    try:
        audio_data = generate_via_elevenlabs(text)
        audio_data = trim_ulaw_silence(audio_data, threshold=150)
        with open(file_path, "wb") as f:
            f.write(audio_data)
        print(f"[OK] Voice Generated via ElevenLabs: {file_path}")
        return
    except Exception as eleven_err:
        print(f"⚠️ ElevenLabs generation failed: {eleven_err}")

    print(f"🔄 Falling back: Generating '{filename}' via Azure Speech...")
    try:
        audio_data = generate_via_azure(text)
        audio_data = trim_ulaw_silence(audio_data, threshold=150)
        with open(file_path, "wb") as f:
            f.write(audio_data)
        print(f"[OK] Voice Generated via Azure: {file_path}")
        return
    except Exception as azure_err:
        print(f"❌ [FAIL] All TTS systems failed for {filename}: {azure_err}")

if __name__ == "__main__":
    print("Generating Shreyas Foundation Sports Gujarati Bot Audio Assets...")
    assets = [
        ("shreyas_gu_step1_greeting.raw", "નમસ્તે જી! શ્રેયસ ફાઉન્ડેશન સ્પોર્ટ્સ એક્ટિવિટીઝમાં તમારું ખૂબ ખૂબ સ્વાગત છે. અમારે ત્યાં બાળકો માટે ઘોડેસવારી, સ્કેટિંગ, ફૂટબોલ અને પર્સનાલિટી ડેવલપમેન્ટ જેવા સરસ પ્રોગ્રામ્સ ચાલે છે. તો તમારા બાળકને આમાંથી શેમાં રસ છે?"),
        
        # 1. Program Selection
        ("filler_1_a.raw", "અરે વાહ, બહુ જ સરસ ચોઈસ છે! હું બેચના ટાઈમિંગ ચેક કરી લઉં..."),
        ("filler_1_b.raw", "ખૂબ સરસ પ્રોગ્રામ પસંદ કર્યો તમે! હું જરા બેચ ડિટેઈલ્સ ચેક કરી લઉં..."),
        ("filler_1_c.raw", "સરસ ચોઈસ! ચાલો હું ચેક કરી લઉં કે આ પ્રોગ્રામની કઈ કઈ બેચ ઉપલબ્ધ છે..."),
        ("filler_1_d.raw", "બહુ સરસ! હું જરા જોઈ લઉં કે આ એક્ટિવિટીના ક્લાસ ક્યારે ક્યારે ચાલે છે..."),
        ("filler_1_e.raw", "વાહ! આ બહુ સરસ પ્રોગ્રામ છે. બસ એક જ મિનિટ, હું ટાઈમિંગ ચેક કરી લઉં..."),
        
        # 2. Age / Timing
        ("filler_2_a.raw", "સરસ! હું આ એજ ગ્રુપ માટે આપણી બેચનું શેડ્યૂલ જોઈ લઉં..."),
        ("filler_2_b.raw", "બરાબર! હું આ ઉંમર પ્રમાણે બેચના કયા કયા ટાઈમિંગ ખાલી છે એ જોઈ લઉં..."),
        ("filler_2_c.raw", "ઓકે, હું ચેક કરી લઉં કે આ ઉંમરના બાળકો માટે કઈ બેચ અત્યારે ચાલુ છે..."),
        ("filler_2_d.raw", "ખૂબ સરસ, બાળકની ઉંમર પ્રમાણે હું યોગ્ય ટાઈમ સ્લોટ શોધી લઉં..."),
        ("filler_2_e.raw", "બરાબર! આ ઉંમર માટે સાંજે કઈ કઈ બેચ ઉપલબ્ધ છે, હું હમણાં જ ચેક કરી લઉં..."),
        
        # 3. WhatsApp Consent
        ("filler_3_a.raw", "હાજી ચોક્કસ, બસ એક જ સેકન્ડ..."),
        ("filler_3_b.raw", "જી સારું, હું હમણાં જ ચેક કરું છું..."),
        ("filler_3_c.raw", "ચોક્કસ, બસ હમણાં જ જણાવું..."),
        ("filler_3_d.raw", "હા, બિલકુલ, બસ એક જ મિનિટ..."),
        ("filler_3_e.raw", "જી હાજી, હું વિગતો જોઈ લઉં..."),
        
        # 4. Question / Inquiry
        ("filler_4_a.raw", "બહુ સારો પ્રશ્ન પૂછ્યો તમે! હું આની ડિટેઈલ્સ ચેક કરી લઉં..."),
        ("filler_4_b.raw", "સારું પૂછ્યું તમે! હું આ વિગત જરા ચકાસી લઉં..."),
        ("filler_4_c.raw", "સાચો સવાલ કર્યો તમે! હું જરા આના વિશે કન્ફર્મ કરી લઉં..."),
        ("filler_4_d.raw", "રસપ્રદ સવાલ છે! હું હમણાં જ આની સાચી ડિટેઈલ્સ ચેક કરી લઉં..."),
        ("filler_4_e.raw", "હાજી, હું જરા આપણી સિસ્ટમમાં આ માહિતી ચેક કરીને જણાવું..."),
        
        # 5. Default / Fallback
        ("filler_5_a.raw", "હાજી ચોક્કસ, બસ એક જ મિનિટ આપો, હું જોઈ લઉ..."),
        ("filler_5_b.raw", "જી, બસ એક સેકન્ડ આપો, હું ચેક કરી લઉં..."),
        ("filler_5_c.raw", "ચોક્કસ, હું જરા વિગતો ચેક કરી લઉં..."),
        ("filler_5_d.raw", "જી બિલકુલ, હું હમણાં જ આ માહિતી ચકાસી લઉં..."),
        ("filler_5_e.raw", "ચોક્કસ, બસ થોડી સેકન્ડ આપો, હું જોઈ લઉં..."),
    ]

    for filename, text in assets:
        generate_tts_file(filename, text)

    print("\n[DONE] Shreyas Gujarati Bot audio assets built successfully.")
