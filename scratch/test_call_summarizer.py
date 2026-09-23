import os
import sys
import django

# Setup Django environment
sys.path.append("c:/DATA/Voice-Bot-SaaS")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from conversations.services.call_summarizer import analyze_call_transcript

def run_tests():
    print("=" * 60)
    print("🧪 TESTING CALL SUMMARIZER & TAG CLASSIFIER")
    print("=" * 60)

    # Test 1: User explicitly says not interested in Hindi / Hinglish
    tx_not_interested = """
BOT: Namaste sir! Mai Kia Motors se bol raha hoon. Kia Syros car launch hui hai, kya aap interested hain?
CUSTOMER: Nahi bhai, mujhe koi nayi gaadi nahi chahiye, mere paas already car hai. Phone rakho.
BOT: Theek hai sir, shukriya.
"""
    res1 = analyze_call_transcript(tx_not_interested, candidate_name="Ramesh Bhai", duration_seconds=28, agent_name="Westcoast Kia")
    print("\nTest 1 (Not Interested in Hindi):")
    print(f"Summary: {res1['call_summary']}")
    print(f"Status:  {res1['final_status']}")
    print(f"Tags:    {res1['tags']}")
    print(f"Sentiment: {res1['sentiment']}")
    assert res1['final_status'] == "NOT_INTERESTED", f"Expected NOT_INTERESTED, got {res1['final_status']}"

    # Test 2: User in Gujarati says not interested
    tx_guj_not_int = """
BOT: નમસ્તે, હું સેમસંગ સ્ટોર પરથી વાત કરું છું. ગેલેક્સી એસ24 માટે ઓફર ચાલે છે.
CUSTOMER: ના ભાઈ, મારે કોઈ ફોન નથી જોઈતો. જરૂર નથી.
BOT: સારું સાહેબ, આભાર.
"""
    res2 = analyze_call_transcript(tx_guj_not_int, candidate_name="Jignesh Patel", duration_seconds=22, agent_name="Samsung Store")
    print("\nTest 2 (Not Interested in Gujarati):")
    print(f"Summary: {res2['call_summary']}")
    print(f"Status:  {res2['final_status']}")
    print(f"Tags:    {res2['tags']}")
    print(f"Sentiment: {res2['sentiment']}")
    assert res2['final_status'] == "NOT_INTERESTED", f"Expected NOT_INTERESTED, got {res2['final_status']}"

    # Test 3: User requests Callback on WhatsApp / driving
    tx_callback = """
BOT: Hello sir, calling from Mahindra regarding the new Thar Roxx.
CUSTOMER: Haan mai abhi driving kar raha hoon, kal shaam ko call karna ya details whatsapp pe bhej dena.
BOT: Sure sir, I will send the brochure to this WhatsApp number. Have a safe drive!
"""
    res3 = analyze_call_transcript(tx_callback, candidate_name="Amit Sharma", duration_seconds=35, agent_name="Mahindra Automotive")
    print("\nTest 3 (Callback / WhatsApp Request):")
    print(f"Summary: {res3['call_summary']}")
    print(f"Status:  {res3['final_status']}")
    print(f"Tags:    {res3['tags']}")
    print(f"Sentiment: {res3['sentiment']}")
    assert res3['final_status'] == "CALLBACK", f"Expected CALLBACK, got {res3['final_status']}"

    # Test 4: User is clearly interested and wants a test drive
    tx_interested = """
BOT: Hello, Kia Motors se baat kar rahe hain. Nayi Sonet car check karni thi aapko?
CUSTOMER: Haanji! Petrol automatic ka kya price hai? Aur Saturday ko test drive mil jayegi SG Highway showroom pe?
BOT: Bilkul sir! Saturday 11 AM ko test drive book kar dete hain.
CUSTOMER: Perfect, please confirm kar dijiye.
"""
    res4 = analyze_call_transcript(tx_interested, candidate_name="Sanjay Mehta", duration_seconds=65, agent_name="Westcoast Kia")
    print("\nTest 4 (Interested with Test Drive):")
    print(f"Summary: {res4['call_summary']}")
    print(f"Status:  {res4['final_status']}")
    print(f"Tags:    {res4['tags']}")
    print(f"Sentiment: {res4['sentiment']}")
    assert res4['final_status'] == "INTERESTED", f"Expected INTERESTED, got {res4['final_status']}"

    print("\n" + "=" * 60)
    print("✅ ALL 4 TESTS PASSED ACCURATELY!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
