"""
Meta WhatsApp Cloud API Client
===============================
Handles official Meta Cloud API template messaging with per-agent credentials.
Strictly isolated: every dispatch uses the specific agent's Phone Number ID and Access Token.
"""

import logging
import requests

logger = logging.getLogger(__name__)


def normalize_whatsapp_phone(raw_phone: str) -> str:
    """
    Normalizes phone numbers to standard Meta WhatsApp recipient format (digits only with country code).
    For Indian numbers: 10 digits -> prepends '91'.
    Strips leading '+', spaces, and dashes.
    """
    if not raw_phone:
        return ""
    digits = "".join(filter(str.isdigit, str(raw_phone)))
    if len(digits) == 10:
        return f"91{digits}"
    if digits.startswith("0") and len(digits) == 11:
        return f"91{digits[1:]}"
    return digits


class MetaWhatsAppClient:
    """
    Meta WhatsApp Cloud API client configured per agent.
    """

    def __init__(self, phone_number_id: str, access_token: str, api_version: str = "v21.0"):
        self.phone_number_id = str(phone_number_id).strip()
        self.access_token = str(access_token).strip()
        self.api_version = str(api_version or "v21.0").strip()
        self.base_url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"

    def send_template_message(
        self,
        to_phone: str,
        template_name: str,
        language_code: str = "en",
        body_parameters: list = None,
        header_type: str = "NONE",
        header_media_url: str = None,
        header_filename: str = "Brochure.pdf",
        timeout: int = 8,
    ) -> dict:
        """
        Sends an approved Meta WhatsApp template message.

        Parameters:
            to_phone: Recipient phone number (e.g. +91 98765 43210)
            template_name: Approved template name in Meta
            language_code: e.g. 'en', 'hi', 'gu'
            body_parameters: List of string values for {{1}}, {{2}}, etc.
            header_type: 'NONE', 'DOCUMENT', 'IMAGE', 'VIDEO', 'TEXT'
            header_media_url: URL for document/image if header_type is media
            header_filename: Filename displayed for documents
            timeout: HTTP request timeout in seconds
        """
        clean_phone = normalize_whatsapp_phone(to_phone)
        if not clean_phone or len(clean_phone) < 10:
            return {
                "success": False,
                "error": f"Invalid recipient phone number: '{to_phone}'",
                "status_code": 400,
            }

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        # Build template components
        components = []

        # 1. Header Component (Media / Text)
        ht = str(header_type or "NONE").upper()
        if ht != "NONE" and header_media_url:
            if ht == "DOCUMENT":
                components.append({
                    "type": "header",
                    "parameters": [{
                        "type": "document",
                        "document": {
                            "link": header_media_url,
                            "filename": header_filename or "Brochure.pdf"
                        }
                    }]
                })
            elif ht == "IMAGE":
                components.append({
                    "type": "header",
                    "parameters": [{
                        "type": "image",
                        "image": {
                            "link": header_media_url
                        }
                    }]
                })
            elif ht == "VIDEO":
                components.append({
                    "type": "header",
                    "parameters": [{
                        "type": "video",
                        "video": {
                            "link": header_media_url
                        }
                    }]
                })
            elif ht == "TEXT":
                components.append({
                    "type": "header",
                    "parameters": [{
                        "type": "text",
                        "text": str(header_media_url)
                    }]
                })

        # 2. Body Component (Positional Parameters {{1}}, {{2}}, etc.)
        if body_parameters and isinstance(body_parameters, list):
            params = []
            for val in body_parameters:
                # Meta requires non-empty string for each variable
                v_str = str(val).strip() if val is not None else ""
                if not v_str:
                    v_str = "Customer"
                params.append({
                    "type": "text",
                    "text": v_str
                })
            if params:
                components.append({
                    "type": "body",
                    "parameters": params
                })

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                }
            }
        }

        if components:
            payload["template"]["components"] = components

        try:
            logger.info(f"📤 [META WHATSAPP DISPATCH] Sending '{template_name}' ({language_code}) to {clean_phone}...")
            resp = requests.post(self.base_url, json=payload, headers=headers, timeout=timeout)
            resp_data = resp.json() if resp.content else {}

            if resp.status_code in (200, 201) and "messages" in resp_data:
                msg_id = resp_data["messages"][0].get("id", "")
                logger.info(f"✅ [META WHATSAPP SUCCESS] Sent to {clean_phone} | Message ID: {msg_id}")
                return {
                    "success": True,
                    "status_code": resp.status_code,
                    "message_id": msg_id,
                    "response": resp_data,
                    "payload_sent": payload
                }
            else:
                err_detail = resp_data.get("error", {})
                err_msg = err_detail.get("message") or resp.text
                logger.error(f"❌ [META WHATSAPP ERROR] HTTP {resp.status_code} - {err_msg}")
                return {
                    "success": False,
                    "status_code": resp.status_code,
                    "error": err_msg,
                    "response": resp_data,
                    "payload_sent": payload
                }

        except requests.exceptions.Timeout:
            err_msg = f"Meta API timeout after {timeout}s"
            logger.error(f"⏳ [META WHATSAPP TIMEOUT] {err_msg}")
            return {
                "success": False,
                "status_code": 408,
                "error": err_msg,
                "payload_sent": payload
            }
        except Exception as e:
            logger.error(f"❌ [META WHATSAPP EXCEPTION]: {e}", exc_info=True)
            return {
                "success": False,
                "status_code": 500,
                "error": str(e),
                "payload_sent": payload
            }

