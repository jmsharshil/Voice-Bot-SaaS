# from pathlib import Path
# import os
# import base64
# import azure.cognitiveservices.speech as speechsdk
# from dotenv import load_dotenv

# ROOT = Path(__file__).resolve().parents[3]
# load_dotenv(ROOT / ".env")

# AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
# AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

# if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
#     raise RuntimeError("AZURE_SPEECH_KEY / AZURE_SPEECH_REGION not set")

# # cache per voice
# _synthesizers = {}


# def _get_synthesizer(voice_name: str):
#     if voice_name not in _synthesizers:
#         speech_config = speechsdk.SpeechConfig(
#             subscription=AZURE_SPEECH_KEY,
#             region=AZURE_SPEECH_REGION,
#         )
#         speech_config.speech_synthesis_voice_name = voice_name

#         _synthesizers[voice_name] = speechsdk.SpeechSynthesizer(
#             speech_config=speech_config
#         )

#     return _synthesizers[voice_name]


# # ================================
# # BACKEND / TERMINAL USE (UNCHANGED)
# # ================================
# def speak(text: str, voice_name: str = None):
#     if not text:
#         return

#     if not voice_name:
#         voice_name = "en-IN-NeerjaNeural"  # safe fallback

#     print(f"🤖 Agent ({voice_name}):", text)

#     synthesizer = _get_synthesizer(voice_name)
#     synthesizer.speak_text_async(text).get()


# # ================================
# # FRONTEND USE (NEW)
# # ================================
# def speak_to_base64(text: str, voice_name: str) -> str:
#     if not text:
#         return ""

#     if not voice_name:
#         voice_name = "en-IN-NeerjaNeural"

#     synthesizer = _get_synthesizer(voice_name)
#     result = synthesizer.speak_text_async(text).get()

#     if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
#         return base64.b64encode(result.audio_data).decode("utf-8")

#     return ""










import os
import base64
import azure.cognitiveservices.speech as speechsdk
from pathlib import Path
from dotenv import load_dotenv

# Load .env
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
    raise RuntimeError("Azure Speech config missing")

def synthesize_to_base64(text: str, voice="en-IN-NeerjaNeural") -> str:
    if not text:
        return ""
    
    text = text.strip()
    text = text.replace("&", "and").replace("\n", " ")

    speech_config = speechsdk.SpeechConfig(
        subscription=AZURE_SPEECH_KEY,
        region=AZURE_SPEECH_REGION
    )
    speech_config.speech_synthesis_voice_name = voice

    # ✅ Telecom optimized
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Raw8Khz16BitMonoPcm
    )


    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=None
    )

    # result = synthesizer.speak_text_async(text).get()
    ssml = f"""
    <speak version='1.0' xml:lang='en-IN'>
        <voice name='{voice}'>
            <prosody rate='-5%' pitch='0%'>
                {text}
            </prosody>
        </voice>
    </speak>
    """

    result = synthesizer.speak_ssml_async(ssml).get()

    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        raise RuntimeError("Azure TTS failed")

    return base64.b64encode(result.audio_data).decode("utf-8")