import json
import logging
import numpy as np
from typing import Optional, Dict, List, Tuple
from sentence_transformers import SentenceTransformer, util

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AutomobileMatcher")

class AutomobileMatcher:
    def __init__(self, intents_file: str):
        self.intents_file = intents_file
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        self.global_intents = []
        self.phase_intents = {} # {phase_name: [intents]}
        self.load_data()

    def load_data(self):
        with open(self.intents_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.global_intents = data.get("global_intents", [])
            
            # Precompute Global Embeddings
            for intent in self.global_intents:
                intent['embeddings'] = self.model.encode(intent['triggers'], convert_to_tensor=True)

            # Precompute Flow/Phase Embeddings
            for phase_data in data.get("flow_intents", []):
                phase_name = phase_data['phase']
                intents = phase_data['intents']
                for intent in intents:
                    intent['embeddings'] = self.model.encode(intent['triggers'], convert_to_tensor=True)
                self.phase_intents[phase_name] = intents
        
        logger.info("Automobile Matcher Data Loaded & Embedded.")

    def find_match(self, user_text: str, current_phase: Optional[str] = None, threshold: float = 0.60) -> Dict:
        """
        1. Check Global Intents (Higher Priority)
        2. Check Current Phase Intents
        """
        user_embedding = self.model.encode(user_text, convert_to_tensor=True)

        # 1. GLOBAL CHECK
        best_global = self._get_best_in_list(user_embedding, self.global_intents)
        if best_global and best_global['score'] >= threshold:
            return {
                "match_type": "GLOBAL",
                "intent": best_global['intent'],
                "score": best_global['score'],
                "action": "play_audio",
                "mp3": best_global['intent']['mp3_file']
            }

        # 2. CONTEXTUAL CHECK (Only if phase is provided)
        if current_phase and current_phase in self.phase_intents:
            best_context = self._get_best_in_list(user_embedding, self.phase_intents[current_phase])
            if best_context and best_context['score'] >= threshold:
                return {
                    "match_type": "CONTEXTUAL",
                    "intent": best_context['intent'],
                    "score": best_context['score'],
                    "action": "play_audio",
                    "mp3": best_context['intent']['mp3_file'],
                    "next_phase": best_context['intent'].get('next_phase')
                }

        # 3. FALLBACK TO LLM
        return {"match_type": "NONE", "action": "call_llm"}

    def _get_best_in_list(self, user_embedding, intent_list):
        overall_best = None
        for intent in intent_list:
            scores = util.cos_sim(user_embedding, intent['embeddings'])[0]
            max_score = float(np.max(scores.cpu().numpy()))
            if overall_best is None or max_score > overall_best['score']:
                overall_best = {"score": max_score, "intent": intent}
        return overall_best
