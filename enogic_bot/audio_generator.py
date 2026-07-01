import os
import sys
import audioop
import shutil
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

VOICE_NAME = "hi-IN-ArjunNeural"

def _amplify_pcm(pcm_data: bytes, gain: float = 1.0) -> bytes:
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
    # We will save a copy inside the local enogic_bot/audio_assets folder
    local_dir = os.path.join(os.path.dirname(__file__), "audio_assets")
    os.makedirs(local_dir, exist_ok=True)
    local_path = os.path.join(local_dir, filename)

    # And we will also save a copy in mp3_responses/enogic_bot/ for runtime loading
    runtime_dir = os.path.join("mp3_responses", "enogic_bot")
    os.makedirs(runtime_dir, exist_ok=True)
    runtime_path = os.path.join(runtime_dir, filename)

    try:
        speech_config = speechsdk.SpeechConfig(
            subscription=AZURE_SPEECH_KEY,
            region=AZURE_SPEECH_REGION
        )
        speech_config.speech_synthesis_voice_name = VOICE_NAME
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
            <voice name='{VOICE_NAME}'>
                <mstts:silence type="Leading" value="150ms"/>
                <prosody rate='10%' pitch='0%' volume='0%'>
                    {text}
                </prosody>
                <mstts:silence type="Tailing" value="50ms"/>
            </voice>
        </speak>
        """

        result = synthesizer.speak_ssml_async(ssml).get()

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            pcm = result.audio_data
            pcm = _amplify_pcm(pcm, gain=1.2)
            ulaw = audioop.lin2ulaw(pcm, 2)
            
            # Write to both locations
            with open(local_path, "wb") as f:
                f.write(ulaw)
            with open(runtime_path, "wb") as f:
                f.write(ulaw)
            print(f"[OK] Voice Generated: {runtime_path}")
        else:
            print(f"[FAIL] Synthesis failed for {filename}: {result.reason}")

    except Exception as e:
        print(f"[FAIL] Failed to generate {filename}: {e}")

if __name__ == "__main__":
    target_filters = sys.argv[1:] if len(sys.argv) > 1 else []
    
    if target_filters:
        print(f"Generating Enogic Bot audio only for files matching: {target_filters}")
    else:
        print("Generating ENOGIC COMMERCIAL TRADE PRIVATE LIMITED MSME ZED Certification Audio Assets via Azure Speech...")

    assets = [
        ("enogic_step1_greeting.raw", "Hello! Namaste... main Shubham bol raha hoon. Kya aapka MSME business hai?"),
        ("enogic_step2_ask_zed_knowledge.raw", "Acha, kya aapko ZED certification ke baare mein pata hai?"),
        ("enogic_step3_explain_and_ask_purchase.raw", "ZED Certification se aapke business ki quality behtareen hoti hai aur wastage kam hoti hai. Saath hi MSMEs ko government subsidies aur benefits bhi milte hain. Toh kya aap apne business ke liye ZED certification purchase karna chahenge?"),
        ("enogic_step4_ask_purchase_directly.raw", "Bahut accha! Toh kya aap apne business ke liye ZED certification purchase karna chahenge?"),
        ("enogic_step8_closing.raw", "Great! Hamari expert consulting team bahut jald aapse contact karegi. Thank you so much!"),
        ("enogic_step9_graceful_exit.raw", "Bilkul theek hai, koi baat nahi. Agar aapko aage kabhi bhi ZED Certification ya compliance support ki zaroorat ho, toh Enogic hamesha aapke liye ready hai. Apna time dene ke liye shukriya!")
    ]

    generated_count = 0
    for filename, text in assets:
        if target_filters and not any(t_filter in filename for t_filter in target_filters):
            continue
        generate_tts_file(filename, text)
        generated_count += 1

    print(f"\n[DONE] Generated {generated_count} Enogic Bot audio asset(s).")
