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

    # Automobile roles — all map to same "automobile" strategy
    "Automobile Advisor": "automobile",
}


def get_role_strategy(role_name: str):
    return ROLE_STRATEGY_MAP.get(role_name, "automobile")