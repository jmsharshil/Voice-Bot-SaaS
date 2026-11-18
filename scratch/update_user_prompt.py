file_path = "icemake_v2_bot/strategy.py"
with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

target = """Classify caller's intent into ONE of:
- PROVIDE_SERIAL: customer stated an alphanumeric serial number (contains letters and/or numbers) or model code."""

replacement = """Classify caller's intent into ONE of:
- PROVIDE_SERIAL: customer stated a valid alphanumeric serial number containing BOTH letters and numbers (e.g. VCB2502116, DF25008959, CIM305B501-25030653).
- INVALID_SERIAL: customer stated a number that is ONLY digits (e.g. 2502116) or ONLY letters (e.g. VCB), lacking the required alphanumeric combination of both letters and numbers."""

target_json = '"intent": "PROVIDE_SERIAL" | "CONFIRM_YES"'
replacement_json = '"intent": "PROVIDE_SERIAL" | "INVALID_SERIAL" | "CONFIRM_YES"'

text = text.replace(target, replacement).replace(target_json, replacement_json)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(text)

print("Updated user_prompt intent definitions successfully!")
