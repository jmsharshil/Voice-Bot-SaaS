# shreyas_bot/config.py

import os
from typing import List, Optional

class ShreyasBotConfig:
    def __init__(
        self,
        company_name: str = "Shreyas Foundation",
        agent_name: str = "Shreya",
        agent_gender: str = "female",
        supported_languages: List[str] = None,
        intents_file: Optional[str] = None
    ):
        self.company_name = company_name
        self.agent_name = agent_name
        self.agent_gender = agent_gender
        self.supported_languages = supported_languages or ["en"]
        self.intents_file = intents_file
