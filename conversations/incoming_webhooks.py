import uuid
import time
import json
import logging
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response

from conversations.models import SarvamAgent, SarvamCallRecord
from conversations.services.kylas_sarvam_bridge import SarvamAgentService

logger = logging.getLogger(__name__)


def _extract_lead_fields(raw_data):
    """
    Smart Parser: Handles flat JSON payloads as well as deeply nested CRM payloads
    (e.g., Kylas CRM lead events: entity.phoneNumbers, entity.firstName, entity.city, entity.campaign).
    """
    entity = raw_data.get("entity") if isinstance(raw_data.get("entity"), dict) else raw_data
    if not isinstance(entity, dict):
        entity = raw_data

    # 1. Extract Phone Number
    phone = None
    
    # Case A: Array of phone objects (e.g., Kylas: phoneNumbers: [{"value": "8742970212", "dialCode": "+91"}])
    phone_numbers_list = entity.get("phoneNumbers") or entity.get("phone_numbers") or raw_data.get("phoneNumbers")
    if isinstance(phone_numbers_list, list) and len(phone_numbers_list) > 0:
        primary_phone = next((p for p in phone_numbers_list if isinstance(p, dict) and p.get("primary")), phone_numbers_list[0])
        if isinstance(primary_phone, dict):
            val = primary_phone.get("value") or primary_phone.get("number") or primary_phone.get("phone")
            dial_code = primary_phone.get("dialCode") or primary_phone.get("dial_code") or ""
            if val:
                val_str = str(val).strip()
                if dial_code and not val_str.startswith("+"):
                    phone = f"{dial_code}{val_str}"
                else:
                    phone = val_str

    # Case B: Flat keys
    if not phone:
        phone = (
            entity.get("phone_number")
            or entity.get("phone")
            or entity.get("mobile")
            or entity.get("contact_number")
            or entity.get("user_phone")
            or entity.get("number")
            or raw_data.get("phone_number")
            or raw_data.get("phone")
            or raw_data.get("mobile")
        )

    # 2. Extract Candidate Name (supports firstName + lastName, or single name fields)
    first_name = entity.get("firstName") or entity.get("first_name") or ""
    last_name = entity.get("lastName") or entity.get("last_name") or ""
    
    full_name_parts = [str(p).strip() for p in [first_name, last_name] if p and str(p).strip() and str(p).lower() != "null"]
    if full_name_parts:
        candidate_name = " ".join(full_name_parts)
    else:
        candidate_name = (
            entity.get("customer_name")
            or entity.get("candidate_name")
            or entity.get("name")
            or entity.get("user_name")
            or entity.get("full_name")
            or raw_data.get("customer_name")
            or raw_data.get("name")
            or "Valued Customer"
        )
    candidate_name = str(candidate_name).strip()

    # 3. Language & Position
    language = entity.get("language") or raw_data.get("language") or "hi-IN"
    applied_position = entity.get("applied_position") or entity.get("position") or "Admission Counselor"

    # 4. Extract Dynamic Extra Prompt Variables for Sarvam Agent (city, campaign, company, etc.)
    extra_vars = {}
    if entity.get("city"):
        extra_vars["city"] = str(entity["city"])
    if entity.get("state"):
        extra_vars["state"] = str(entity["state"])
    if entity.get("companyName"):
        extra_vars["company_name"] = str(entity["companyName"])
    
    campaign_obj = entity.get("campaign")
    if isinstance(campaign_obj, dict) and campaign_obj.get("value"):
        extra_vars["campaign_name"] = str(campaign_obj["value"])
    elif entity.get("utmCampaign"):
        extra_vars["campaign_name"] = str(entity["utmCampaign"])

    if entity.get("utmSource"):
        extra_vars["source"] = str(entity["utmSource"])

    custom_fields = entity.get("customFieldValues") or {}
    if isinstance(custom_fields, dict):
        for k, v in custom_fields.items():
            if v is not None and str(v).strip() != "":
                extra_vars[k] = str(v)

    for source_dict in [raw_data, entity]:
        for k, v in source_dict.items():
            if k not in ["entity", "phoneNumbers", "emails", "customFieldValues", "campaign", "ownerId", "createdBy", "updatedBy"] and not isinstance(v, (dict, list)):
                if v is not None and str(v).strip() != "" and str(v).lower() not in ["null", "none", "nan"]:
                    extra_vars[k] = str(v)

    return phone, candidate_name, language, applied_position, extra_vars


@csrf_exempt
@api_view(["GET", "POST"])
def incoming_trigger_webhook(request, agent_slug=None, agent_id=None):
    """
    Standalone Inbound Webhook Endpoint.
    Receives JSON webhooks from external systems (Kylas CRM, HubSpot, Web Forms, Zapier, Make.com),
    parses customer details & dynamic variables, initiates an outbound call via Sarvam AI,
    and creates a SarvamCallRecord so the call automatically displays on the Sarvam Dashboard.

    Supported URLs:
    - POST /api/webhook/trigger-call/ (uses default active Sarvam agent)
    - POST /api/webhook/trigger-call/<slug:agent_slug>/ (uses specified agent by slug)
    - POST /api/webhook/trigger-call/agent/<int:agent_id>/ (uses specified agent by ID)
    """
    if request.method == "GET":
        return Response({
            "status": "active",
            "message": "Sarvam AI Voice Agent Incoming Webhook Endpoint is ready.",
            "supported_payloads": ["Flat JSON", "Kylas CRM Lead Webhooks", "HubSpot / Form Webhooks"],
            "sample_kylas_payload_supported": True
        }, status=200)

    try:
        raw_data = {}
        # Try parsing JSON from body directly first (bypasses DRF Content-Type restrictions)
        if request.body:
            try:
                raw_data = json.loads(request.body.decode("utf-8"))
            except Exception:
                pass

        if not raw_data:
            try:
                raw_data = getattr(request, "data", {}) or {}
            except Exception:
                raw_data = {}

        print("\n" + "="*60)
        print("📥 [INCOMING TRIGGER WEBHOOK RECEIVED]")
        print(f"Target Agent Slug: {agent_slug} | Agent ID: {agent_id}")
        print(f"Payload: {json.dumps(raw_data, indent=2)}")
        print("="*60 + "\n")

        phone, candidate_name, language, applied_position, extra_variables = _extract_lead_fields(raw_data)

        if not phone:
            return Response({
                "status": "error",
                "code": "MISSING_PHONE_NUMBER",
                "message": "Missing required phone number in webhook payload."
            }, status=400)

        clean_phone = str(phone).strip()

        target_agent = None
        if agent_slug:
            target_agent = SarvamAgent.objects.filter(slug=agent_slug, is_active=True).first()
        elif agent_id:
            target_agent = SarvamAgent.objects.filter(id=agent_id, is_active=True).first()
        
        if not target_agent:
            target_agent = SarvamAgent.objects.filter(is_active=True).first()

        if not target_agent:
            return Response({
                "status": "error",
                "code": "NO_ACTIVE_AGENT",
                "message": "No active Sarvam Voice Agent configured in the system."
            }, status=400)

        if target_agent.is_minutes_exhausted:
            logger.warning(f"🛑 [INCOMING WEBHOOK BLOCKED]: Agent '{target_agent.name}' is out of minutes.")
            return Response({
                "status": "error",
                "code": "MINUTES_EXHAUSTED",
                "message": f"Call minutes limit reached for agent '{target_agent.name}'. Remaining: {target_agent.remaining_minutes}m.",
                "remaining_minutes": target_agent.remaining_minutes
            }, status=400)

        attempt_id = f"wh_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        event_name = raw_data.get("event") or raw_data.get("event_type") or "CRM Webhook"
        call_record = SarvamCallRecord.objects.create(
            sarvam_agent=target_agent,
            attempt_id=attempt_id,
            phone_number=clean_phone,
            candidate_name=candidate_name,
            language=language,
            applied_position=applied_position,
            call_type=f"Webhook: {event_name}",
            status="DIALING",
            summary={"received_payload": raw_data, "extra_variables": extra_variables}
        )

        logger.info(f"📱 [INCOMING WEBHOOK]: Initiating call for '{candidate_name}' ({clean_phone}) via Agent '{target_agent.name}' (Record #{call_record.id})")

        sarvam_response = SarvamAgentService.trigger_outbound_call(
            phone_number=clean_phone,
            lead_id=call_record.id,
            customer_name=candidate_name,
            language=language,
            sarvam_agent=target_agent,
            extra_variables=extra_variables
        )

        is_call_success = True
        sarvam_error_msg = None
        if isinstance(sarvam_response, dict):
            interaction_id = sarvam_response.get("interaction_id") or sarvam_response.get("id")
            sarvam_attempt_id = sarvam_response.get("attempt_id") or sarvam_response.get("attemptId")
            
            update_fields = []
            if interaction_id:
                call_record.interaction_id = str(interaction_id)
                update_fields.append("interaction_id")
            if sarvam_attempt_id:
                call_record.attempt_id = str(sarvam_attempt_id)
                update_fields.append("attempt_id")
            
            if update_fields:
                call_record.save(update_fields=update_fields)

            if sarvam_response.get("error") or sarvam_response.get("code") in [401, 403, 404, 422, 500]:
                is_call_success = False
                call_record.status = "FAILED"
                call_record.save(update_fields=["status"])
                err_dict = sarvam_response.get("error")
                if isinstance(err_dict, dict):
                    sarvam_error_msg = err_dict.get("message") or str(err_dict)
                else:
                    sarvam_error_msg = str(sarvam_response)

        status_flag = "success" if is_call_success else "api_auth_error"
        msg = f"Sarvam voice agent call initiated to {candidate_name} ({clean_phone})" if is_call_success else f"Webhook parsed successfully, but Sarvam API returned error: {sarvam_error_msg}. Please check Agent '{target_agent.name}' API Key in Django Admin."

        return Response({
            "status": status_flag,
            "message": msg,
            "data": {
                "call_record_id": call_record.id,
                "attempt_id": attempt_id,
                "agent": target_agent.name,
                "agent_slug": target_agent.slug,
                "candidate_name": candidate_name,
                "phone_number": clean_phone,
                "status": call_record.status,
                "extracted_variables": extra_variables,
                "sarvam_response": sarvam_response
            }
        }, status=200 if is_call_success else 400)

    except Exception as e:
        logger.error(f"❌ [INCOMING WEBHOOK ERROR]: {str(e)}", exc_info=True)
        return Response({
            "status": "error",
            "code": "INTERNAL_SERVER_ERROR",
            "message": str(e)
        }, status=500)
