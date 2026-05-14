import requests
import os

AZURE_TRANSLATOR_KEY = os.getenv("AZURE_TRANSLATOR_KEY")
AZURE_TRANSLATOR_REGION = os.getenv("AZURE_TRANSLATOR_REGION", "eastus")
AZURE_TRANSLATOR_ENDPOINT =os.getenv("AZURE_TRANSLATOR_ENDPOINT")

def translate_text(text: str, from_lang: str, to_lang: str) -> str:
    """
    Translate text using Azure Translator.
    from_lang: 'en', 'hi'
    to_lang:   'en', 'hi'
    """
    if not text or from_lang == to_lang:
        return text

    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_TRANSLATOR_KEY,
        "Ocp-Apim-Subscription-Region": AZURE_TRANSLATOR_REGION,
        "Content-Type": "application/json"
    }

    params = {
        "api-version": "3.0",
        "from": from_lang,
        "to": to_lang
    }

    body = [{"text": text}]

    try:
        response = requests.post(
            AZURE_TRANSLATOR_ENDPOINT,
            headers=headers,
            params=params,
            json=body,
            timeout=5
        )
        result = response.json()
        return result[0]["translations"][0]["text"]
    except Exception as e:
        print(f"❌ Translation error: {e}")
        return text  # fallback: return original text
    


def detect_language(text: str) -> str:
    """
    Detect language of text.
    Returns: 'en', 'hi'
    """
    if not text:
        return "en"

    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_TRANSLATOR_KEY,
        "Ocp-Apim-Subscription-Region": AZURE_TRANSLATOR_REGION,
        "Content-Type": "application/json"
    }

    params = {"api-version": "3.0"}
    body = [{"text": text}]

    try:
        response = requests.post(
            AZURE_TRANSLATOR_ENDPOINT.replace("/translate", "/detect"),
            headers=headers,
            params=params,
            json=body,
            timeout=5
        )
        result = response.json()
        detected = result[0]["language"]  # returns 'hi', 'gu', 'en' etc.
        print(f"🔍 Detected language: {detected}")
        # Only support en, hi, gu — fallback to en
        if detected in ["hi", "en", "gu"]:
            return detected
        return "en"
    except Exception as e:
        print(f"❌ Detection error: {e}")
        return "en"