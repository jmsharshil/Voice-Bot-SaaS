import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from icemake_bot.strategy import _convert_all_spoken_numbers_to_digits, _extract_pincode_ai, _extract_phone_number_ai

test_cases = [
    ("Gujarati Compound Spoken Phone", "નવમું ઝીરો એકાણું બાણું ચારસો બે", "gu", "9091924002"),
    ("Phonetic English in Hindi Devanagari", "99। 133। एट वन। 306।", "hi", "9913381306"),
    ("User Exact Log (Hindi Phonetic Pincode)", "जी मेरा शहर अहमदाबाद है। मेरा पिन कोड है। 3824। वन एट।", "hi", "382418"),
    ("Hindi Spoken Digits Phone", "मेरा नंबर नौ चार दो सात दो आठ पांच छह पांच तीन है", "hi", "9427285653"),
    ("Gujarati Spoken Words Pincode", "મારું ઘર અમદાવાદ પિન કોડ ત્રણ આઠ બે ચાર આઠ એક છે", "gu", "382481"),
    ("English Mixed Spoken Pincode", "my city is ahmedabad and pincode is three eight two four one eight", "en", "382418"),
]

print("==================================================")
print("  TESTING UNIVERSAL SPOKEN NUMBER TO DIGIT CONVERTER ")
print("==================================================")

for label, raw_input, lang, expected in test_cases:
    converted = _convert_all_spoken_numbers_to_digits(raw_input, lang)
    pincode = _extract_pincode_ai(converted, lang)
    phone = _extract_phone_number_ai(converted, lang)
    
    print(f"[{label}]:")
    print(f"   Original Input: '{raw_input}'")
    print(f"   Converted Digits: '{converted}'")
    print(f"   Extracted Pincode: '{pincode}' | Extracted Phone: '{phone}'")
    print("-" * 50)
