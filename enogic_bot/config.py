import os
from typing import List, Optional

class EnogicBotConfig:
    def __init__(
        self,
        company_name: str = "ENOGIC COMMERCIAL TRADE PRIVATE LIMITED",
        agent_name: str = "ZARA",
        agent_gender: str = "female",
        supported_languages: List[str] = None,
        intents_file: Optional[str] = None
    ):
        self.company_name = company_name
        self.agent_name = agent_name
        self.agent_gender = agent_gender
        self.supported_languages = supported_languages or ["hi", "en"]
