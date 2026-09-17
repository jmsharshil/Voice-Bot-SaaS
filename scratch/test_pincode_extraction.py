import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from icemake_bot.strategy import _extract_pincode_ai

test_cases = [
    ("User Exact Log Case", "जी मेरा शहर अहमदाबाद है। मेरा पिन कोड है। 3824। वन एट।", "hi", "382418"),
    ("Hindi Spoken Words", "मेरा शहर अहमदाबाद और पिन कोड तीन आठ दो चार एक आठ है", "hi", "382418"),
    ("Gujarati Mixed Words", "મારું ઘર ગોતા અમદાવાદ પિનકોડ 382481 છે", "gu", "382481"),
    ("Standard 6 Digits", "380001", "en", "380001"),
    ("English Spoken Words", "pincode is three eight two four one eight", "en", "382418"),
]

print("==================================================")
print("  TESTING AI MULTI-LINGUAL PINCODE EXTRACTION     ")
print("==================================================")

for label, raw_input, lang, expected in test_cases:
    extracted = _extract_pincode_ai(raw_input, lang)
    status = "✅ PASS" if extracted == expected else f"❌ FAIL (Got: '{extracted}')"
    print(f"[{status}] {label}:")
    print(f"   Input: '{raw_input}' ({lang})")
    print(f"   Extracted: '{extracted}' | Expected: '{expected}'")
    print("-" * 50)
