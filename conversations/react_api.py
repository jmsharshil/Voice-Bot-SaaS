import json
import logging
import re
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from conversations.models import SarvamAgent, SarvamCallRecord
from conversations.services.kylas_sarvam_bridge import SarvamAgentService

logger = logging.getLogger(__name__)


def _clean_phone(raw_phone: str) -> str:
    """
    Sanitizes phone number: extracts digits and formats to E.164 (+91...).
    """
    if not raw_phone:
        return ""
    digits = re.sub(r"\D", "", str(raw_phone).strip())
    if not digits:
        return ""
    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"
    elif len(digits) == 11 and digits.startswith("0"):
        return f"+91{digits[1:]}"
    elif len(digits) == 10:
        return f"+91{digits}"
    elif digits.startswith("91") and len(digits) > 10:
        return f"+91{digits[-10:]}"
    return f"+{digits}"


LANGUAGE_NAME_MAP = {
    "hi-in": "Hindi",
    "hi": "Hindi",
    "hindi": "Hindi",
    "en-in": "English",
    "en": "English",
    "english": "English",
    "gu-in": "Gujarati",
    "gu": "Gujarati",
    "gujarati": "Gujarati",
    "kn-in": "Kannada",
    "kn": "Kannada",
    "kannada": "Kannada",
    "mr-in": "Marathi",
    "mr": "Marathi",
    "marathi": "Marathi",
    "ta-in": "Tamil",
    "ta": "Tamil",
    "tamil": "Tamil",
    "te-in": "Telugu",
    "te": "Telugu",
    "telugu": "Telugu",
    "bn-in": "Bengali",
    "bn": "Bengali",
    "bengali": "Bengali",
    "ml-in": "Malayalam",
    "ml": "Malayalam",
    "malayalam": "Malayalam",
    "pa-in": "Punjabi",
    "pa": "Punjabi",
    "punjabi": "Punjabi",
    "od-in": "Odia",
    "or-in": "Odia",
    "or": "Odia",
    "odia": "Odia",
}


def _resolve_language_name(lang_input: str) -> str:
    if not lang_input:
        return "Hindi"
    clean = str(lang_input).strip().lower()
    return LANGUAGE_NAME_MAP.get(clean, str(lang_input).strip().title())


@csrf_exempt
@api_view(["POST", "OPTIONS"])
@permission_classes([AllowAny])
def react_trigger_call_api(request, agent_slug=None):
    """
    Dedicated Standalone API for React Frontend Call Triggering.
    
    Expected Request Payload (JSON):
    {
        "vehicle_type": "4 Wheeler",
        "brand": "Skoda",
        "use_case": "Service Reminder",
        "language": "hi-IN",
        "dealership_name": "Stellar Skoda",
        "city": "Ahmedabad",
        "phone": "9876543210",
        "user_name": "Ayushi Patel",
        "agent_slug": "skoda"   // optional (overrides default/URL agent)
    }
    """
    # ── CORS Preflight Support ──
    if request.method == "OPTIONS":
        response = Response(status=200)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
        return response

    try:
        # Extract payload from request data (DRF parses JSON automatically)
        data = request.data if isinstance(request.data, dict) else {}
        if not data:
            try:
                import json
                data = json.loads(request._request.body.decode("utf-8")) if hasattr(request, "_request") else {}
            except Exception:
                data = {}

        # ── 1. Extract the 8 Requested Fields ──
        phone_raw = data.get("phone") or data.get("phone_number")
        user_name = str(data.get("user_name") or data.get("name") or "").strip()
        vehicle_type = str(data.get("vehicle_type") or "").strip()
        brand = str(data.get("brand") or "").strip()
        use_case = str(data.get("use_case") or "").strip()
        dealership_name = str(data.get("dealership_name") or data.get("dealership") or "").strip()
        city = str(data.get("city") or "").strip()

        # Resolve language to clean title (e.g. "Kannada", "Hindi", "Gujarati")
        raw_lang = str(data.get("language") or "").strip()
        language_name = _resolve_language_name(raw_lang) if raw_lang else "Hindi"

        # Prepare app_overrides to explicitly set initial_language_name for Sarvam voice engine
        custom_overrides = data.get("app_overrides") if isinstance(data.get("app_overrides"), dict) else {}
        initial_lang = custom_overrides.get("initial_language_name") or language_name
        app_overrides = {
            "initial_language_name": initial_lang
        }
        for opt_key in ["initial_state_name", "initial_bot_message"]:
            if opt_key in custom_overrides and custom_overrides[opt_key]:
                app_overrides[opt_key] = custom_overrides[opt_key]

        # ── 2. Validate Required Fields ──
        if not phone_raw:
            return Response({
                "status": "error",
                "message": "Phone number is required."
            }, status=400)

        clean_phone = _clean_phone(phone_raw)
        if len(re.sub(r"\D", "", clean_phone)) < 10:
            return Response({
                "status": "error",
                "message": f"Invalid phone number '{phone_raw}'. Please provide a valid 10-digit mobile number."
            }, status=400)

        if not user_name:
            user_name = "Valued Customer"

        # ── 3. Resolve Target Sarvam Agent ──
        # Priority: URL slug > Payload agent_slug > Match by brand > First active automotive agent
        target_slug = agent_slug or data.get("agent_slug") or data.get("agent")
        sarvam_agent = None

        if target_slug:
            sarvam_agent = (
                SarvamAgent.objects.filter(slug=target_slug, is_active=True).first()
                or SarvamAgent.objects.filter(slug__iexact=target_slug, is_active=True).first()
            )

        if not sarvam_agent and brand:
            # Smart match by brand name (e.g. "Skoda" -> stellar_skoda, "Honda" -> daksh-honda)
            b_lower = brand.lower()
            for ag in SarvamAgent.objects.filter(is_active=True):
                ag_name_l = (ag.name or "").lower()
                ag_slug_l = (ag.slug or "").lower()
                if b_lower in ag_slug_l or b_lower in ag_name_l or ag_slug_l in b_lower:
                    sarvam_agent = ag
                    break

        if not sarvam_agent:
            # Fallback to 'car' agent or first active SarvamAgent
            sarvam_agent = (
                SarvamAgent.objects.filter(slug__in=["car", "skoda", "daksh-honda"], is_active=True).first()
                or SarvamAgent.objects.filter(is_active=True).first()
            )

        if not sarvam_agent:
            return Response({
                "status": "error",
                "message": "No active Sarvam Agent found in the system. Please configure an agent in Admin."
            }, status=404)

        # ── 4. Check Call Minutes Quota ──
        if getattr(sarvam_agent, "is_minutes_exhausted", False):
            return Response({
                "status": "error",
                "code": "MINUTES_EXHAUSTED",
                "message": f"Call minutes limit reached for agent '{sarvam_agent.name}'. Please recharge minutes."
            }, status=400)

        # ── 5. Prepare Variables to Send to Sarvam Agent ──
        # Send strictly the requested fields without unnecessary aliases
        # (Sarvam validates app variable schemas strictly and rejects undeclared aliases with HTTP 422)
        raw_variables = {
            "user_name": user_name,
            "vehicle_type": vehicle_type,
            "brand": brand,
            "use_case": use_case,
            "language": language_name,
            "dealership_name": dealership_name,
            "city": city,
        }
        extra_variables = {
            k: str(v).strip()
            for k, v in raw_variables.items()
            if v is not None and str(v).strip() != "" and str(v).lower() not in ["nan", "none", "null"]
        }

        # ── 6. Create Call Record in Database ──
        call_rec = SarvamCallRecord.objects.create(
            sarvam_agent=sarvam_agent,
            phone_number=clean_phone[-10:],
            candidate_name=user_name,
            applied_position=f"{brand} {vehicle_type} ({use_case})" if brand else "React Triggered Call",
            language=language_name,
            status="DIALING",
            call_type="React Outbound Call",
            summary={
                "source": "react_frontend_api",
                "vehicle_type": vehicle_type,
                "brand": brand,
                "use_case": use_case,
                "language": language_name,
                "dealership_name": dealership_name,
                "city": city,
                "app_overrides": app_overrides,
                "received_payload": data,
            }
        )

        logger.info(
            f"\n🚀 [REACT TRIGGER CALL]: Initiating outbound call via Sarvam Agent '{sarvam_agent.name}'\n"
            f"   Phone: {clean_phone} | Name: {user_name}\n"
            f"   Details: {vehicle_type} | {brand} | {use_case} | {language_name} | {dealership_name} | {city}\n"
            f"   App Overrides: {app_overrides}\n"
        )

        # ── 7. Dispatch Outbound Call via Sarvam AI API ──
        res = SarvamAgentService.trigger_outbound_call(
            phone_number=clean_phone,
            lead_id=call_rec.id,
            customer_name=user_name,
            language=language_name,
            extra_variables=extra_variables,
            sarvam_agent=sarvam_agent,
            app_overrides=app_overrides,
        )

        attempt_id = res.get("attempt_id") if isinstance(res, dict) else None
        if attempt_id:
            call_rec.attempt_id = attempt_id
            call_rec.save(update_fields=["attempt_id"])

        response = Response({
            "status": "success",
            "message": f"Call initiated successfully to {clean_phone}",
            "call_id": call_rec.id,
            "attempt_id": attempt_id,
            "agent": {
                "id": sarvam_agent.id,
                "name": sarvam_agent.name,
                "slug": sarvam_agent.slug,
            },
            "payload_sent": {
                "phone": clean_phone,
                "agent_vars": extra_variables,
                "app_overrides": app_overrides,
                "user_name": user_name,
                "vehicle_type": vehicle_type,
                "brand": brand,
                "use_case": use_case,
                "language": language_name,
                "dealership_name": dealership_name,
                "city": city,
            }
        }, status=200)

        response["Access-Control-Allow-Origin"] = "*"
        return response

    except Exception as e:
        logger.error(f"❌ [REACT TRIGGER CALL ERROR]: {e}", exc_info=True)
        response = Response({
            "status": "error",
            "message": str(e)
        }, status=500)
        response["Access-Control-Allow-Origin"] = "*"
        return response
