import os
import sys
try:
    import audioop
except ImportError:
    import audioop_lts as audioop
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
load_dotenv()

AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", "centralindia")

def generate_azure_icemake_greeting():
    if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
        print("❌ AZURE_SPEECH_KEY or AZURE_SPEECH_REGION missing!")
        return

    print("🎙️ Generating Studio Quality Azure Greeting for Ice Make...")

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

    ssml = """
    <speak version='1.0' xmlns="http://www.w3.org/2001/10/synthesis" 
           xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang='hi-IN'>
        <voice name='hi-IN-SwaraNeural'>
            <mstts:silence type="Leading" value="250ms"/>
            <prosody rate='0%' pitch='0%' volume='+20%'>
                Welcome to Ice Make 24 by 7 service support. आप किस भाषा में बात करना पसंद करेंगे?
            </prosody>
            <mstts:silence type="Tailing" value="100ms"/>
        </voice>
    </speak>
    """

    result = synthesizer.speak_ssml_async(ssml).get()
    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(f"❌ Azure synthesis failed: {result.reason}")
        return

    pcm = result.audio_data
    if len(pcm) % 2 != 0:
        pcm = pcm[:-1]

    # Convert 16-bit PCM (8000Hz) to G.711 A-law
    alaw_bytes = audioop.lin2alaw(pcm, 2)

    out_file1 = os.path.join(PROJECT_ROOT, "icemake_bot", "icemake_greeting.raw")
    out_file2 = os.path.join(PROJECT_ROOT, "mp3_responses", "icemake_bot", "icemake_greeting.raw")
    out_file3 = os.path.join(PROJECT_ROOT, "mp3_responses", "icemake_greeting.raw")
    out_file4 = os.path.join(PROJECT_ROOT, "icemake_greeting.raw")

    for path in [out_file1, out_file2, out_file3, out_file4]:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(alaw_bytes)
        print(f"✅ Saved studio Azure A-law greeting to: {path} ({len(alaw_bytes)} bytes)")

if __name__ == "__main__":
    generate_azure_icemake_greeting()
