import logging
import json
import urllib.request
import re

logger = logging.getLogger(__name__)

# In-memory lookup cache to minimize external network latency
_PINCODE_CACHE = {
    "382421": {"area": "Dantali", "district": "Gandhinagar", "state": "Gujarat", "formatted": "Dantali, Gandhinagar, Gujarat"},
    "382418": {"area": "GIDC Naroda", "district": "Ahmedabad", "state": "Gujarat", "formatted": "GIDC Naroda, Ahmedabad, Gujarat"},
    "380001": {"area": "Bhadra", "district": "Ahmedabad", "state": "Gujarat", "formatted": "Bhadra, Ahmedabad, Gujarat"},
    "516355": {"area": "Kallur", "district": "Cuddapah", "state": "Andhra Pradesh", "formatted": "Kallur, Cuddapah, Andhra Pradesh"},
}

def lookup_pincode(pincode: str) -> dict:
    """
    Looks up Indian postal pincode (6 digits) and returns area, district, and state.
    Uses cached records first, then api.postalpincode.in, with an Azure OpenAI fallback.
    """
    clean_pin = "".join(filter(str.isdigit, str(pincode or "")))
    if len(clean_pin) != 6:
        return {"area": "", "district": "", "state": "", "formatted": ""}

    if clean_pin in _PINCODE_CACHE:
        return _PINCODE_CACHE[clean_pin]

    # 1. Primary: Indian Postal Pincode API
    try:
        url = f"https://api.postalpincode.in/pincode/{clean_pin}"
        req = urllib.request.Request(url, headers={"User-Agent": "IceMakeVoiceAgent/2.0"})
        with urllib.request.urlopen(req, timeout=3.5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                if data and isinstance(data, list) and data[0].get("Status") == "Success":
                    post_offices = data[0].get("PostOffice", [])
                    if post_offices:
                        po = post_offices[0]
                        area = po.get("Name") or ""
                        district = po.get("District") or ""
                        state = po.get("State") or ""
                        
                        parts = [p for p in [area, district, state] if p]
                        formatted = ", ".join(parts)
                        
                        res = {
                            "area": area,
                            "district": district,
                            "state": state,
                            "formatted": formatted
                        }
                        _PINCODE_CACHE[clean_pin] = res
                        logger.info(f"[PINCODE SUCCESS] {clean_pin} -> {formatted}")
                        return res
    except Exception as e:
        logger.warning(f"[PINCODE API NOTICE] Postal API error for {clean_pin}: {e}")

    # 2. Secondary: Fallback with Azure OpenAI
    try:
        from conversations.services.azure_openai_service import client
        from django.conf import settings

        prompt = f"""
Identify the Indian District and State for postal pincode "{clean_pin}".
Return ONLY a valid JSON object with keys: "area", "district", "state".
Example: {{"area": "Dantali", "district": "Gandhinagar", "state": "Gujarat"}}
JSON:"""

        response = client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are an Indian geographical postal code lookup directory."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=50,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        area = data.get("area", "")
        district = data.get("district", "")
        state = data.get("state", "")
        formatted = ", ".join([p for p in [area, district, state] if p])
        res = {
            "area": area,
            "district": district,
            "state": state,
            "formatted": formatted
        }
        if state:
            _PINCODE_CACHE[clean_pin] = res
            return res
    except Exception as e_ai:
        logger.warning(f"[PINCODE AI FALLBACK NOTICE]: {e_ai}")

    return {"area": "", "district": "", "state": "", "formatted": ""}
