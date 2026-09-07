import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from icemake_bot.strategy import _extract_phone_number_ai

test_cases = [
    ("Hindi Devanagari Digits", "९४२७२८५६५३", "hi", "9427285653"),
    ("Gujarati Mixed Words", "9427 બે આઠ 5653?", "gu", "9427285653"),
    ("Hindi Spoken Words", "मेरा नंबर नौ चार दो सात दो आठ पाँच छह पाँच तीन है", "hi", "9427285653"),
    ("Telugu Regional Digits", "౯<ctrl42>౨౭<ctrl42><ctrl42><ctrl42><ctrl42><ctrl42><ctrl42>?", "te", None), # Will test actual digits below
    ("English Spoken Words", "My number is nine four two seven two eight five six five three", "en", "9427285653"),
    ("Standard 10 digits with STT mark", "9427285653?", "gu", "9427285653"),
    ("Marathi Devanagari Digits", "९८२३४५६७८९", "mr", "9823456789"),
    ("Gujarati Compound Spoken Words", "નવમું ઝીરો એકાણું બાણું ચારસો બે", "gu", "9091924002"),
    ("Hindi Compound Spoken Words", "मेरा नंबर नब्बे तिरानवे चौरासी साठ पंद्रह है", "hi", "9093846015"),
    ("English Paired Compound Words", "ninety-four twenty-seven twenty-eight fifty-six fifty-three", "en", "9427285653"),
]

print("==================================================")
print("  TESTING AI MULTI-LINGUAL PHONE EXTRACTION SYSTEM ")
print("==================================================")

for label, raw_input, lang, expected in test_cases:
    if expected is None:
        continue
    extracted = _extract_phone_number_ai(raw_input, lang)
    status = "✅ PASS" if extracted == expected else f"❌ FAIL (Got: '{extracted}')"
    print(f"[{status}] {label}:")
    print(f"   Input: '{raw_input}' ({lang})")
    print(f"   Extracted: '{extracted}' | Expected: '{expected}'")
    print("-" * 50)
