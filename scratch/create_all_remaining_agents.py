# scratch/create_all_remaining_agents.py

import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voice_bot.settings")
django.setup()

# Import and run each creation script
try:
    print("--- Setting up Samsung Agent ---")
    from scratch.create_samsung_agent import setup_samsung
    setup_samsung()
except Exception as e:
    print(f"Error setting up Samsung agent: {e}")

try:
    print("\n--- Setting up Samsung LLM Agent ---")
    from scratch.create_samsung_llm_agent import setup_samsung_llm
    setup_samsung_llm()
except Exception as e:
    print(f"Error setting up Samsung LLM agent: {e}")

try:
    print("\n--- Setting up Loan Agent ---")
    from scratch.create_loan_agent import setup_loan_agent
    setup_loan_agent()
except Exception as e:
    print(f"Error setting up Loan agent: {e}")

try:
    print("\n--- Setting up Reminder Agent ---")
    from scratch.create_reminder_agent import main as setup_reminder
    setup_reminder()
except Exception as e:
    print(f"Error setting up Reminder agent: {e}")

try:
    print("\n--- Setting up Real Estate Agent ---")
    from scratch.create_real_estate_agent import create_agent as setup_real_estate
    setup_real_estate()
except Exception as e:
    print(f"Error setting up Real Estate agent: {e}")

try:
    print("\n--- Setting up Naavya Automobile Agent ---")
    from scratch.create_naavya_agent import setup_naavya
    setup_naavya()
except Exception as e:
    print(f"Error setting up Naavya agent: {e}")

try:
    print("\n--- Setting up Enogic Agent ---")
    from scratch.setup_enogic import setup_enogic
    setup_enogic()
except Exception as e:
    print(f"Error setting up Enogic agent: {e}")

try:
    print("\n--- Setting up Fold8 Agent ---")
    from scratch.create_fold8_agent import setup_fold8
    setup_fold8()
except Exception as e:
    print(f"Error setting up Fold8 agent: {e}")
