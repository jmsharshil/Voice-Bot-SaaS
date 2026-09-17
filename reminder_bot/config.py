import os
from typing import List, Optional

class ReminderBotConfig:
    def __init__(
        self,
        bank_name: str = "JMS Bank",
        agent_name: str = "JMS Loan Reminder Advisor",
        agent_gender: str = "female",
        supported_languages: List[str] = None,
        intents_file: Optional[str] = None
    ):
        self.bank_name = bank_name
        self.agent_name = agent_name
        self.agent_gender = agent_gender
        self.supported_languages = supported_languages or ["gu"]
        
        # Default intents location
        self.intents_file = intents_file or os.path.join(
            os.path.dirname(__file__), "data", "reminder_intents.json"
        )
