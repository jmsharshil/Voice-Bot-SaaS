# fold8_bot/audio_generator.py
import os
import sys
import requests
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
if not SARVAM_API_KEY:
    print("❌ Error: SARVAM_API_KEY not found in environment!")
    sys.exit(1)

def generate_sarvam_file(filename, text):
    subfolder = "fold8_bot"
    target_dir = os.path.join("mp3_responses", subfolder)
    os.makedirs(target_dir, exist_ok=True)
    
    file_path = os.path.join(target_dir, filename)
    api_url = "https://api.sarvam.ai/text-to-speech/stream"
    
    headers = {
        "api-subscription-key": SARVAM_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "text": text,
        "target_language_code": "gu-IN",
        "speaker": "ishita",
        "model": "bulbul:v3",
        "pace": 1.05,
        "speech_sample_rate": 8000,
        "output_audio_codec": "mulaw",
        "enable_preprocessing": True,
        "temperature": 0.50
    }
    
    try:
        print(f"🎙️ Synthesizing '{text}' to {filename} (pace=1.05)...")
        response = requests.post(api_url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        
        if response.content:
            with open(file_path, "wb") as f:
                f.write(response.content)
            print(f"[OK] Voice Generated: {file_path}")
        else:
            print(f"[FAIL] No audio returned for {filename}")
    except Exception as e:
        print(f"[FAIL] Failed to generate {filename}: {e}")

if __name__ == "__main__":
    assets = [
        ("fold8_step2_launch_info.raw", "અરે વાહ! બાવીસ જુલાઈએ સેમસંગની અનપેક્ડ ઈવેન્ટમાં નવો ગેલેક્સી ઝેડ ફોલ્ડ આઠ અને ફ્લિપ આઠ લોન્ચ થવાનો છે. શું તમે આ નવો ફોન જોવા માટે ઉત્સુક છો?"),
        ("fold8_step3_pitch_reservation.raw", "જી બિલકુલ! માત્ર નવસો નવાણું રૂપિયા આપીને તમે પ્રી-રિઝર્વ કરાવી શકો છો, જે પૂરેપૂરા રિફંડેબલ છે. સાથે જ તમને બે હજાર સાતસો નવાણું રૂપિયાનું વાઉચર પણ મળશે. તો શું આપણે તમારો સ્લોટ બુક કરીએ?"),
        ("fold8_objection_explanation.raw", "અચ્છા, હું તમને સમજાવું. આ માત્ર એક એડવાન્સ સ્લોટ બુકિંગ છે. જો લોન્ચ પછી તમને ફોન ના ગમે, તો તમારા આ નવસો નવાણું રૂપિયા સો ટકા પાછા મળી જશે. એટલે આમાં કોઈ જોખમ નથી. તો શું આપણે સ્લોટ બુક કરીએ?"),
        ("fold8_step4_ask_area.raw", "ચોક્કસ! તમે અમદાવાદમાં કયા એરિયામાં રહો છો, જેથી હું નજીકનો સ્ટોર શોધી શકું?"),
        ("fold8_step6_ask_name.raw", "જી ચોક્કસ. પ્રી-રિઝર્વેશન માટે શું હું તમારું પૂરું નામ જાણી શકું?"),
        ("fold8_step7_ask_phone.raw", "બરાબર. અને આ જ નંબર પર સ્ટોરની ટીમ તમારો સંપર્ક કરે અને બધી વિગત મોકલે, એ યોગ્ય રહેશે કે બીજો કોઈ નંબર આપવો છે?"),
        ("fold8_step8_ask_time.raw", "જી ચોક્કસ. સ્ટોરની ટીમ તમને કયા સમયે કોલ કરે તો અનુકૂળ રહેશે - સવારે, બપોરે કે સાંજે?"),
        ("fold8_step9_closing.raw", "બરાબર છે. તો અમારી સ્ટોરની ટીમ તમારો સંપર્ક કરશે. આપનો કિંમતી સમય આપવા બદલ ખૂબ ખૂબ આભાર! આવજો!"),
        ("fold8_rejection.raw", "કોઈ વાંધો નહીં, આપનો સમય આપવા બદલ ખૂબ ખૂબ આભાર! ધ્યાન રાખજો."),
        ("fold8_store_vijay.raw", "બરાબર છે. તમારા માટે વિજય ક્રોસ રોડ સ્ટોર સૌથી નજીક રહેશે. તો શું આ લોકેશન અનુકૂળ રહેશે?"),
        ("fold8_store_bodakdev.raw", "બરાબર છે. તમારા માટે બોડકદેવ સ્ટોર સૌથી નજીક રહેશે. તો શું આ લોકેશન અનુકૂળ રહેશે?"),
        ("fold8_store_palladium.raw", "બરાબર છે. તમારા માટે પેલેડિયમ મોલ સ્ટોર સૌથી નજીક રહેશે. તો શું આ લોકેશન અનુકૂળ રહેશે?"),
        ("fold8_store_paldi.raw", "બરાબર છે. તમારા માટે પાલડી સ્ટોર સૌથી નજીક રહેશે. તો શું આ લોકેશન અનુકૂળ રહેશે?"),
        ("fold8_store_isanpur.raw", "બરાબર છે. તમારા માટે ઈસનપુર સ્ટોર સૌથી નજીક રહેશે. તો શું આ લોકેશન અનુકૂળ રહેશે?"),
        ("fold8_store_naroda.raw", "બરાબર છે. તમારા માટે ન્યૂ નરોડા સ્ટોર સૌથી નજીક રહેશે. તો શું આ લોકેશન અનુકૂળ રહેશે?"),
        ("fold8_area_not_found.raw", "બરાબર છે. અમારા સ્ટોર ટીમમાંથી એક પ્રતિનિધિ નજીકના સ્ટોરની વિગત સાથે તમારો સંપર્ક કરશે. પ્રી-રિઝર્વેશન માટે શું હું તમારું પૂરું નામ જાણી શકું?")
    ]
    
    print("Generating Fold8 Bot Sarvam Female Voice Audio Assets (Overwriting at pace=1.05)...")
    for filename, text in assets:
        generate_sarvam_file(filename, text)
    print("\n[DONE] Finished pre-synthesizing all Fold8 audio assets at pace=1.05.")
