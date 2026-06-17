import os
import sys
import audioop
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

VOICE_NAME = "gu-IN-DhwaniNeural"

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
    subfolder = "reminder_bot"
    target_dir = os.path.join("mp3_responses", subfolder)
    os.makedirs(target_dir, exist_ok=True)
    
    file_path = os.path.join(target_dir, filename)

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
               xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang='gu-IN'>
            <voice name='{VOICE_NAME}'>
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
            pcm = _amplify_pcm(pcm, gain=2.0)
            ulaw = audioop.lin2ulaw(pcm, 2)
            
            with open(file_path, "wb") as f:
                f.write(ulaw)
            print(f"[OK] Voice Generated: {file_path}")
        else:
            print(f"[FAIL] Synthesis failed for {filename}: {result.reason}")

    except Exception as e:
        print(f"[FAIL] Failed to generate {filename}: {e}")

if __name__ == "__main__":
    target_filters = sys.argv[1:] if len(sys.argv) > 1 else []
    
    if target_filters:
        print(f"Generating Reminder Bot audio only for files matching: {target_filters}")
    else:
        print("Generating JMS Bank Loan Reminder Bot Gujarati Flow Audio Assets via Azure Speech...")

    assets = [
        ("reminder_step1_greeting.raw", "નમસ્તે! હું જે એમ એસ બેંકમાંથી નવ્યા બોલું છું. તમારી ઈ એમ આઈ ની તારીખ નજીક છે, તમે ક્યારે ચુકવણી કરશો?"),
        ("reminder_step2_ask_mode.raw", "ધન્યવાદ જણાવવા માટે, તમે કઈ રીતે ચુકવણી કરશો? યુ પી આઈ, નેટબેંકિંગ કે અન્ય કોઈ રીતે?"),
        ("reminder_step3_closing.raw", "સરસ! તમારી વિગતો નોંધી લેવામાં આવી છે. સમયસર ચુકવણી કરવા બદલ આભાર!"),
        ("reminder_step_rejection.raw", "તમારી અસુવિધા બદલ દિલગીર છું. તમારી માહિતી નોંધી લેવામાં આવી છે. સમયસર ચુકવણી કરવા બદલ આભાર!")
    ]

    generated_count = 0
    for filename, text in assets:
        if target_filters and not any(t_filter in filename for t_filter in target_filters):
            continue
        generate_tts_file(filename, text)
        generated_count += 1

    print(f"\n[DONE] Generated {generated_count} Reminder Bot audio asset(s).")
