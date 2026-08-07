# kia_syros_bot/config.py

from typing import List, Optional

class KiaSyrosBotConfig:
    def __init__(
        self,
        company_name: str = "Westcoast Kia",
        agent_name: str = "Kia Syros Advisor",
        agent_gender: str = "female",
        supported_languages: List[str] = None,
        intents_file: Optional[str] = None
    ):
        self.company_name = company_name
        self.agent_name = agent_name
        self.agent_gender = agent_gender
        self.supported_languages = supported_languages or ["hi"]
        self.intents_file = intents_file
