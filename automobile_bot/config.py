import os
from typing import List, Optional

class AutomobileBotConfig:
    def __init__(
        self,
        dealership_name: str = "Premium Showroom",
        brand: str = "Multi-brand",
        model: str = "Cars",
        agent_name: str = "Naavya",
        agent_gender: str = "female",
        supported_languages: List[str] = None,
        intents_file: Optional[str] = None
    ):
        self.dealership_name = dealership_name
        self.brand = brand
        self.model = model
        self.agent_name = agent_name
        self.agent_gender = agent_gender
        self.supported_languages = supported_languages or ["hi", "en", "gu"]
        
        # Default intents location
        self.intents_file = intents_file or os.path.join(
            os.path.dirname(__file__), "data", "Naavya_intents.json"
        )
