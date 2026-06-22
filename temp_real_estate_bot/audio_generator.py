import os
import sys
import audioop
from dotenv import load_dotenv
import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
API_URL = "https://api.sarvam.ai/text-to-speech/stream"

def generate_tts_file(filename, text):
    subfolder = "temp_real_estate_bot"
    target_dir = os.path.join("mp3_responses", subfolder)
    os.makedirs(target_dir, exist_ok=True)
    
    file_path = os.path.join(target_dir, filename)

    headers = {
        "api-subscription-key": SARVAM_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "text": text,
        "target_language_code": "gu-IN",
        "speaker": "ishita",
        "model": "bulbul:v3",
        "pace": 1.17,
        "speech_sample_rate": 8000,
        "output_audio_codec": "mulaw",
        "enable_preprocessing": True
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        
        audio_data = response.content
        if not audio_data:
            print(f"❌ Sarvam returned empty audio for: {filename}")
            return

        with open(file_path, "wb") as f:
            f.write(audio_data)

        print(f"[OK] Voice Generated: {file_path}")

    except Exception as e:
        print(f"[FAIL] Failed to generate {filename}: {e}")

if __name__ == "__main__":
    target_filters = sys.argv[1:] if len(sys.argv) > 1 else []
    
    if target_filters:
        print(f"Generating Real Estate Bot audio only for files matching: {target_filters}")
    else:
        print("Generating JMS Real Estate Bot Gujarati Flow Audio Assets via Sarvam AI...")

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
