import os
import sys
import audioop
from dotenv import load_dotenv
import requests
import azure.cognitiveservices.speech as speechsdk
import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
SARVAM_URL = "https://api.sarvam.ai/text-to-speech/stream"

AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")
AZURE_VOICE_NAME = "gu-IN-DhwaniNeural"

def _amplify_pcm(pcm_data: bytes, gain: float = 1.0) -> bytes:
    try:
        samples = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32)
        samples = samples * gain
        samples = np.clip(samples, -32768, 32767)
        return samples.astype(np.int16).tobytes()
    except Exception as e:
        print(f"Amplify error: {e}")
        return pcm_data

def trim_trailing_silence(pcm_data: bytes, threshold: int = 150) -> bytes:
    try:
        samples = np.frombuffer(pcm_data, dtype=np.int16)
        # Find all indices where absolute amplitude is greater than threshold
        active_indices = np.where(np.abs(samples) > threshold)[0]
        if len(active_indices) == 0:
            return pcm_data
        
        last_active_idx = active_indices[-1]
        
        # Add 300ms of tailing padding (0.3s * 8000 samples/sec = 2400 samples)
        padding_samples = 2400
        end_idx = min(len(samples), last_active_idx + padding_samples)
        
        trimmed_pcm = samples[:end_idx].tobytes()
        print(f"   [Trim] {len(samples)} samples -> {end_idx} samples (saved {round((len(samples)-end_idx)/8000, 2)}s)")
        return trimmed_pcm
    except Exception as e:
        print(f"Trim silence error: {e}")
        return pcm_data

def trim_ulaw_silence(ulaw_data: bytes, threshold: int = 150) -> bytes:
    try:
        # Convert μ-law to 16-bit PCM
        pcm = audioop.ulaw2lin(ulaw_data, 2)
        # Trim silence
        trimmed_pcm = trim_trailing_silence(pcm, threshold)
        # Convert back to μ-law
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
        "speaker": "ishita",
        "model": "bulbul:v3",
        "pace": 1.16,
        "speech_sample_rate": 8000,
        "output_audio_codec": "mulaw",
        "enable_preprocessing": True
    }
    
    response = requests.post(SARVAM_URL, headers=headers, json=payload, timeout=20)
    response.raise_for_status()
    return response.content

def generate_via_azure(text) -> bytes:
    if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
        raise ValueError("AZURE_SPEECH_KEY or AZURE_SPEECH_REGION not found in env")

    speech_config = speechsdk.SpeechConfig(
        subscription=AZURE_SPEECH_KEY,
        region=AZURE_SPEECH_REGION
    )
    speech_config.speech_synthesis_voice_name = AZURE_VOICE_NAME
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
        <voice name='{AZURE_VOICE_NAME}'>
            <mstts:silence type="Leading" value="150ms"/>
            <prosody rate='+20%' pitch='0%' volume='0%'>
                {text}
            </prosody>
            <mstts:silence type="Tailing" value="50ms"/>
        </voice>
    </speak>
    """

    result = synthesizer.speak_ssml_async(ssml).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        pcm = result.audio_data
        pcm = trim_trailing_silence(pcm)
        pcm = _amplify_pcm(pcm, gain=2.0)
        ulaw = audioop.lin2ulaw(pcm, 2)
        return ulaw
    else:
        raise Exception(f"Azure Speech synthesis failed: {result.reason}")

def generate_tts_file(filename, text):
    subfolder = "carekay_bot"
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

    # 2. Fall back to Azure Speech
    try:
        print(f"🔄 Falling back: Generating '{filename}' via Azure Speech...")
        audio_data = generate_via_azure(text)
        if audio_data:
            with open(file_path, "wb") as f:
                f.write(audio_data)
            print(f"[OK] Voice Generated via Azure: {file_path}")
            return
    except Exception as azure_err:
        print(f"❌ [FAIL] Both Sarvam and Azure failed for {filename}: {azure_err}")

if __name__ == "__main__":
    target_filters = sys.argv[1:] if len(sys.argv) > 1 else []
    
    if target_filters:
        print(f"Generating Carekay Bot audio only for files matching: {target_filters}")
    else:
        print("Generating Carekay Insurance Renewal Bot Gujarati Flow Audio Assets...")

    assets = [
        ("carekay_step1_greeting.raw", "હલો, નમસ્તે જી! હું કેરકે ઇન્શ્યોરન્સમાંથી કેય વાત કરું છું. તમારી ગાડીનો મોટર ઇન્શ્યોરન્સ આવતા અઠવાડિયે એક્સપાયર થઈ રહ્યો છે. તો શું તમારી સાથે ૨ મિનિટ વાત થઈ શકે?"),
        ("carekay_step2_ask_whatsapp.raw", "આભાર! તમારું નવું પ્રીમિયમ લગભગ ગયા વર્ષ જેટલું જ છે. તો શું હું તમને વોટ્સએપ પર રિન્યુઅલ અને પેમેન્ટ લિંક મોકલી આપું જેથી તમે તેને ચેક કરી શકો?"),
        ("carekay_step3_closing.raw", "જી સારું, મેં લિંક મોકલી આપી છે. જો કોઈ પ્રશ્ન હોય તો જણાવજો. તમારો કિંમતી સમય આપવા બદલ આભાર, આવજો!"),
        ("carekay_rejection.raw", "કોઈ વાંધો નહીં જી, તમારો કિંમતી સમય આપવા બદલ ખૂબ આભાર. તમારો દિવસ શુભ રહે, આવજો!")
    ]

    generated_count = 0
    for filename, text in assets:
        if target_filters and not any(t_filter in filename for t_filter in target_filters):
            continue
        generate_tts_file(filename, text)
        generated_count += 1

    print(f"\n[DONE] Generated {generated_count} Carekay Bot audio asset(s).")
