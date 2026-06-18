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
    subfolder = "temp_real_estate_bot"
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
                <mstts:silence type="Leading" value="100ms"/>
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
        print(f"Generating Real Estate Bot audio only for files matching: {target_filters}")
    else:
        print("Generating JMS Real Estate Bot Gujarati Flow Audio Assets via Azure Speech...")

    assets = [
        ("real_estate_step1_greeting.raw", "હલો, નમસ્તે જી! હું જેએમએસ રિયલ એસ્ટેટ તરફથી નવ્યા વાત કરું છું. અમે અત્યારે ખૂબ જ સરસ લક્ઝુરિયસ ફ્લેટ્સ વેચી રહ્યા છીએ. તો મને જણાવશો, તમારે કયા પ્રકારનો ફ્લેટ જોઈએ છે, જેમ કે વન બીએચકે કે ટુ બીએચકે?"),
        ("real_estate_step2_ask_area.raw", "અરે વાહ, ખૂબ જ સરસ! તો તમે અમદાવાદમાં કયા એરિયા કે વિસ્તારમાં ફ્લેટ લેવાનું વધારે પસંદ કરશો?"),
        ("real_estate_step3_ask_budget.raw", "ઓકે, અને તમારું અંદાજિત બજેટ કેટલું રાખ્યું છે, કોઈ પણ આશરે કિંમત જણાવશો તો પણ ચાલશે."),
        ("real_estate_step4_ask_name.raw", "જી ચોક્કસ, મેં વિગત નોંધી લીધી છે.. પ્લીઝ તમારું નામ જણાવો."),
        ("real_estate_step5_closing.raw", "જી ખૂબ ખૂબ આભાર! મેં તમારી બધી જ જરૂરિયાતો અહીંયા નોંધી લીધી છે. હવે અમારી સેલ્સ ટીમ ટૂંક સમયમાં તમારો સંપર્ક કરશે. તમારો કિંમતી સમય આપવા બદલ ખૂબ આભાર, આવજો!")
    ]

    generated_count = 0
    for filename, text in assets:
        if target_filters and not any(t_filter in filename for t_filter in target_filters):
            continue
        generate_tts_file(filename, text)
        generated_count += 1

    print(f"\n[DONE] Generated {generated_count} Real Estate Bot audio asset(s).")
