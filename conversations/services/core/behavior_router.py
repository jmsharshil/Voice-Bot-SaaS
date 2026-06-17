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
    "Hospital Appointment Advisor": "hospital_minimal",
    "JMS Loan Advisor": "loan_strategy",
    "JMS Loan Reminder Advisor": "reminder_strategy",
}


def get_role_strategy(role_name: str):
    return ROLE_STRATEGY_MAP.get(role_name, "automobile")