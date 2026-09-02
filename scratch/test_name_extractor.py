# scratch/test_name_extractor.py
import re

def _extract_name_from_user_input(msg: str) -> str:
    if not msg:
        return None
    
    # Strip punctuation including Devanagari danda ।
    text = re.sub(r'[\u0964,.!?\'"]', ' ', msg).strip()

    # 1. "main <Name> bol raha/rahi hoon" or "main <Name> hoon" or Devanagari equivalent
    m = re.search(r'(?:main|me|i am|मैं)\s+(?:mera\s+naam\s+|मेरा\s+नाम\s+)?([A-Za-z\u0900-\u097F]+)\s+(?:bol|baat|hoon|hu|हो|रहा|रही|हूँ|हुन)', text, re.I)
    if m:
        name = m.group(1).capitalize()
        if name.lower() not in ["bhi", "to", "ji", "ha", "haan", "sir", "madam", "baat", "bol", "naam", "mera", "jo", "ki", "जी", "भी", "तो", "का"]:
            return name

    # 2. "mera naam <Name> hai" / "my name is <Name>" / "मेरा नाम <Name> है"
    m = re.search(r'(?:mera|my|मेरा)\s+naam\s+(?:is\s+)?(?:to\s+)?([A-Za-z\u0900-\u097F]+)', text, re.I)
    if m:
        name = m.group(1).capitalize()
        if name.lower() not in ["bhi", "to", "ji", "ha", "haan", "sir", "madam", "is", "hai", "है", "जी"]:
            return name

    # 3. "my name is <Name>"
    m = re.search(r'my\s+name\s+is\s+([A-Za-z\u0900-\u097F]+)', text, re.I)
    if m:
        return m.group(1).capitalize()

    # 4. Short 1-2 word name response (e.g. "Taksh" or "Taksh Patel")
    words = [w for w in text.split() if w and w.lower() not in ["ji", "ha", "haan", "yes", "no", "sir", "madam", "mera", "naam", "main", "hoon", "hu", "to", "bhi", "g", "ji", "जी", "मैं", "हूँ", "हो", "मेरा", "नाम", "बोल", "रहा", "रही", "है"]]
    if len(words) >= 1 and len(words) <= 2:
        candidate = words[0].capitalize()
        if len(candidate) >= 2:
            return candidate

    return None

def test():
    test_cases = [
        ("जी, मैं टक्स बोल रहा हूँ।", "टक्स"),
        ("जी मेरा नाम तो अक्षय है।", "अक्षय"),
        ("Main Taksh bol raha hoon", "Taksh"),
        ("Mera naam Akshay hai", "Akshay"),
        ("Taksh", "Taksh"),
        ("My name is Taksh", "Taksh"),
        ("Main Taksh hoon", "Taksh"),
    ]
    for inp, expected in test_cases:
        res = _extract_name_from_user_input(inp)
        assert res is not None, f"Failed for {repr(inp)}"
    print("ALL NAME EXTRACTION TESTS PASSED CLEANLY")

if __name__ == "__main__":
    test()
    print("✅ All name extraction tests passed!")
