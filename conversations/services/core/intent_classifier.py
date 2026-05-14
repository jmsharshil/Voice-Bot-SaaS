# conversations/services/core/intent_classifier.py

from conversations.services.azure_openai_service import generate_response
import json
import re


def classify_intent(message: str):
    """
    AI-based intent classification.
    Returns structured intent data.
    """

    system_prompt = """
You are an AI intent classifier.

Classify the user message into one of these categories:
- greeting
- information_request
- booking_request
- pricing_request
- complaint
- emergency
- lead_interest
- small_talk
- general_query
- unknown

Rules:
- Return ONLY valid JSON.
- Do NOT explain.
- Do NOT add text.
- Output must be parseable JSON.

Format:
{
  "intent": "",
  "confidence": 0.0
}
"""

    response = generate_response(system_prompt, message)

    try:
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass

    return {
        "intent": "unknown",
        "confidence": 0.0
    }