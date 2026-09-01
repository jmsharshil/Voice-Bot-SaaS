# # conversations/services/core/behavior_router.py

# ROLE_STRATEGY_MAP = {
#     "AI Voice Bot Consultant": "ai_voice_bot",
#     "Insurance Advisor": "insurance",
#     "Admission Counselor": "education",
#     "Property Inquiry Agent": "real_estate",
#     "Accountant Interviewer": "interview_bot",
#     "Food Store Assistant": "food_store",

# }


# def get_role_strategy(role_name: str):
#     return ROLE_STRATEGY_MAP.get(role_name, "ai_voice_bot")




# conversations/services/core/behavior_router.py

ROLE_STRATEGY_MAP = {

    # Automobile roles
    "Automobile Advisor": "automobile",
    "Naavya Automobile Advisor": "automobile_Naavya",
    "Kia Syros EV Advisor": "kia_syros_strategy",
    "Hospital Appointment Advisor": "hospital_minimal",
    "JMS Loan Advisor": "loan_strategy",
    "JMS Loan Reminder Advisor": "reminder_strategy",
    "Naavya JMS Real Estate Advisor": "temp_real_estate_strategy",
    "Enogic ZED Advisor": "enogic_strategy",
    "Naavya Samsung Store Advisor": "samsung_store_strategy",
    "Naavya Samsung LLM Advisor": "samsung_llm_strategy",
    "Galaxy Z Fold8 Pre-Reserve Advisor": "fold8_prereserve_strategy",
    "Carekay Insurance Advisor": "carekay_strategy",
    "Carekay Gujarati Insurance Renewal Advisor": "carekay_strategy",
    "Shreyas Sports Advisor": "shreyas_strategy",
    "Shreyas Sports Advisor Gujarati": "shreyas_gu_strategy",
    "Raahi iiiEM Export Advisor": "raahi_iiiem_strategy",
    "Raahi Triple iEM Advisor": "raahi_iiiem_strategy",
    "Priya Naavya AI Advisor": "priya_naavya_strategy",
    "Priya Naavya Advisor": "priya_naavya_strategy",
    "Naavya.ai MSME Advisor": "priya_naavya_strategy",
}


def get_role_strategy(role_name: str):
    if not role_name:
        return "automobile"
    if "raahi" in role_name.lower():
        return "raahi_iiiem_strategy"
    if "priya" in role_name.lower():
        return "priya_naavya_strategy"
    return ROLE_STRATEGY_MAP.get(role_name, "automobile")