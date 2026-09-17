import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

from conversations.models import Conversation, Session
from samsung_llm_bot.strategy import samsung_llm_prepare, samsung_llm_finalize
from samsung_llm_bot.prompts import SAMSUNG_LLM_SYSTEM_PROMPT

class DummyAgent:
    name = "Navya"
    company_name = "VTech Samsung Cafe"
    agent_type = "samsung_llm_strategy"

def test_exclamation_diversity():
    print("--- TESTING EXCLAMATION DIVERSITY ACROSS MULTI-TURN DIALOGUE ---")
    
    agent = DummyAgent()
    session = Session(session_id="test_exclamation_session_123", state={"customer_name": "હર્ષિલ"})
    
    dialogue_turns = [
        "હા, હું સેમસંગનો ફોન વાપરું છું.",
        "મારો ફોન ૨ વર્ષ જૂનો થયો છે.",
        "હા, મારે નવો ફોન લેવો છે.",
        "તમારા સ્ટોરનો ટાઇમિંગ શું છે?",
        "મારું બજેટ ૩૦,૦૦૦ રૂપિયા છે.",
        "હું આ અઠવાડિયે જ લેવા માગું છું.",
        "હું બોડકદેવ વિસ્તારમાં રહું છું."
    ]

    # Greeting turn
    prep_0 = samsung_llm_prepare(agent, "", session)
    print(f"Agent Initial Greeting: {prep_0.get('static_reply')}\n")

    # Turn 1: Confirm identity / ask if use Samsung
    prep_1 = samsung_llm_prepare(agent, "હા બોલો", session)
    print(f"User: હા બોલો")
    print(f"Agent: {prep_1.get('static_reply')}\n")

    exclamations_used = []

    for turn_idx, user_input in enumerate(dialogue_turns, start=1):
        prep = samsung_llm_prepare(agent, user_input, session)
        if "static_reply" in prep:
            resp = prep["static_reply"]
        else:
            from conversations.services.azure_openai_service import generate_response
            llm_resp = generate_response(prep["system_prompt"], prep["user_message"])
            resp = samsung_llm_finalize(llm_resp, prep)
        
        print(f"Turn {turn_idx} | User: {user_input}")
        print(f"Turn {turn_idx} | Agent: {resp}\n")
        
        # Check first word/exclamation
        first_part = resp.split()[0] if resp else ""
        exclamations_used.append(first_part)

    print("--- EXCLAMATION SUMMARY ---")
    for i, ex in enumerate(exclamations_used, 1):
        print(f"Turn {i}: {ex}")

if __name__ == "__main__":
    test_exclamation_diversity()
