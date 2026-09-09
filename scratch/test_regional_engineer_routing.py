import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from icemake_bot.strategy import _get_engineer_whatsapp_for_state

test_states = [
    ("Gujarat English", "Gujarat", "Mr. Rutvik", "918733004773"),
    ("Gujarat Hindi", "गुजरात", "Mr. Rutvik", "918733004773"),
    ("Gujarat Gujarati", "અમદાવાદ, ગુજરાત", "Mr. Rutvik", "918733004773"),
    ("North Delhi", "Delhi NCR", "Mr. Manjit", "919104142402"),
    ("North UP Hindi", "उत्तर प्रदेश", "Mr. Manjit", "919104142402"),
    ("North Punjab", "Ludhiana, Punjab", "Mr. Manjit", "919104142402"),
    ("East Kolkata", "Kolkata, West Bengal", "Mr. Mahesh", "919913381306"),
    ("East Bihar", "Patna, Bihar", "Mr. Mahesh", "919913381306"),
    ("West Maharashtra", "Mumbai, Maharashtra", "Mr. Ashok", "917490021566"),
    ("West Rajasthan", "Jaipur, Rajasthan", "Mr. Ashok", "917490021566"),
    ("South Tamil Nadu", "Chennai, Tamil Nadu", "Ms. Vaidehi", "919725891156"),
    ("South Kerala", "Kochi, Kerala", "Ms. Vaidehi", "919725891156"),
]

print("==================================================")
print("  TESTING REGIONAL ENGINEER WHATSAPP ROUTING ")
print("==================================================")

for label, input_state, expected_name, expected_num in test_states:
    num, name, region = _get_engineer_whatsapp_for_state(input_state)
    pass_status = "✅ PASS" if name == expected_name and num == expected_num else "❌ FAIL"
    print(f"[{label}]: Input: '{input_state}' -> Region: {region} | Engineer: {name} ({num}) | {pass_status}")

print("==================================================")
