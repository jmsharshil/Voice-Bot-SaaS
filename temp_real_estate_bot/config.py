import os
from typing import List, Optional

class TempRealEstateBotConfig:
    def __init__(
        self,
        company_name: str = "JMS Real Estate",
        agent_name: str = "Naavya",
        agent_gender: str = "female",
        supported_languages: List[str] = None,
        intents_file: Optional[str] = None
    ):
        self.company_name = company_name
        self.agent_name = agent_name
        self.agent_gender = agent_gender
        self.supported_languages = supported_languages or ["gu"]
        
        # Default intents location
        self.intents_file = intents_file or os.path.join(
            os.path.dirname(__file__), "data", "real_estate_intents.json"
        )
