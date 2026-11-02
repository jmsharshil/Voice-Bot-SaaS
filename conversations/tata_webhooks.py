import json
import logging
import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response

from conversations.models import SarvamAgent, SarvamCallRecord

logger = logging.getLogger(__name__)
IST_TZ = ZoneInfo("Asia/Kolkata")


def _clean_phone_number(raw_num):
    """
    Cleans phone number: strips non-digits, trims country code (+91, 91, 0),
    and returns a clean 10-digit mobile number when applicable.
    """
    if not raw_num:
        return ""
    digits = re.sub(r"\D", "", str(raw_num).strip())
    if not digits:
        return ""
    # Strip leading 91 (India) or 0
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    elif len(digits) > 10 and digits.startswith("91"):
        digits = digits[-10:]
    return digits


def _parse_timestamp(raw_ts):
    """
    Parses start_stamp or timestamp strings safely and localizes to Indian Standard Time (IST).
    """
    if not raw_ts:
        return timezone.localtime(timezone.now(), IST_TZ)
    s = str(raw_ts).strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%d-%m-%Y %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
    ):
        try:
            dt = datetime.strptime(s.split("+")[0].split("Z")[0].strip(), fmt)
            return timezone.make_aware(dt, IST_TZ)
        except Exception:
            pass
    try:
        from django.utils.dateparse import parse_datetime
        parsed = parse_datetime(s)
        if parsed:
            if parsed.tzinfo is None:
                return timezone.make_aware(parsed, IST_TZ)
            return timezone.localtime(parsed, IST_TZ)
    except Exception:
        pass
    return timezone.localtime(timezone.now(), IST_TZ)


@csrf_exempt
@api_view(["GET", "POST"])
def tata_smartflo_call_start_webhook(request, agent_slug=None):
    """
    Dedicated Webhook for Tata Smartflo Inbound Calls.
    
    Fires at the start of an inbound call from Tata Smartflo, captures the caller's phone number,
    immediately creates an 'IN_PROGRESS' SarvamCallRecord so the caller's number appears on
    the Sarvam Voice Agent dashboard in real-time.
    
    When the call completes, Sarvam AI's post-call CDR webhook seamlessly updates this same record
    with recording audio, transcript, and AI summary.

    Supported Endpoints:
    - POST /api/webhook/tata/call-start/<slug:agent_slug>/ (explicit agent)
    - POST /api/webhook/tata/call-start/ (auto-detects agent via call_to_number DID)
    """
    if request.method == "GET":
        return Response({
            "status": "active",
            "message": "Tata Smartflo Inbound Call-Start Webhook is operational.",
            "target_agent_slug": agent_slug or "Auto-detect via DID (call_to_number)",
            "supported_format": "Tata Smartflo Inbound Webhook Template"
        }, status=200)

    try:
        # Extract payload from JSON or form-encoded POST
        raw_data = {}
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
        if not raw_data and request.POST:
            raw_data = dict(request.POST.items())

        logger.info("\n" + "=" * 65)
        logger.info("📞 [TATA SMARTFLO CALL-START WEBHOOK RECEIVED]")
        logger.info(f"Target Agent Slug in URL: {agent_slug}")
        logger.info(f"Payload: {json.dumps(raw_data, indent=2)}")
        logger.info("=" * 65 + "\n")

        # 1. Extract Caller Phone Number
        # Support all field variations from Tata template (handles optional trailing spaces in keys)
        caller_number_raw = (
            raw_data.get("caller_id_number")
            or raw_data.get("customer_no_with_prefix ")
            or raw_data.get("customer_no_with_prefix")
            or raw_data.get("customer_number_with_prefix")
            or raw_data.get("cli")
            or raw_data.get("from")
            or raw_data.get("caller_number")
            or ""
        )
        clean_caller_phone = _clean_phone_number(caller_number_raw)

        # 2. Extract Destination DID (agent phone number on Tata Smartflo)
        call_to_number = (
            raw_data.get("call_to_number")
            or raw_data.get("destination_number")
            or raw_data.get("did")
            or raw_data.get("to")
            or ""
        )
        clean_did = _clean_phone_number(call_to_number)

        # 3. Resolve Target Sarvam Agent
        target_agent = None
        if agent_slug:
            target_agent = SarvamAgent.objects.filter(slug=agent_slug, is_active=True).first()
            if not target_agent:
                target_agent = SarvamAgent.objects.filter(slug__iexact=agent_slug).first()

        # Fallback to matching DID against SarvamAgent.agent_phone
        if not target_agent and clean_did:
            did_last_10 = clean_did[-10:] if len(clean_did) >= 10 else clean_did
            target_agent = SarvamAgent.objects.filter(
                agent_phone__icontains=did_last_10,
                is_active=True
            ).first()

        # Fallback to first active agent if not matched
        if not target_agent:
            target_agent = SarvamAgent.objects.filter(is_active=True).first()

        # 4. Extract Tata identifiers and metadata
        uuid_val = str(raw_data.get("uuid") or "").strip()
        call_id = str(raw_data.get("call_id") or "").strip()
        call_status = str(raw_data.get("call_status") or "ringing").strip()
        billing_circle = str(raw_data.get("billing_circle") or "").strip()
        answer_agent_number = str(raw_data.get("answer_agent_number") or "").strip()
        start_stamp = raw_data.get("start_stamp")

        call_start_dt = _parse_timestamp(start_stamp)

        # 5. Idempotency Check: prevent duplicate records for repeated webhook hits
        attempt_id = f"tata_{uuid_val}" if uuid_val else (f"tata_{call_id}" if call_id else None)
        existing = None
        if attempt_id:
            existing = SarvamCallRecord.objects.filter(attempt_id=attempt_id).first()
        if not existing and call_id:
            from datetime import timedelta
            recent_t = timezone.now() - timedelta(minutes=15)
            existing = SarvamCallRecord.objects.filter(
                summary__tata_call_id=call_id,
                created_at__gte=recent_t
            ).first()

        if existing:
            logger.info(f"🔁 [TATA SMARTFLO]: Call record #{existing.id} already exists for Tata call (UUID: {uuid_val}, CallID: {call_id}).")
            return Response({
                "status": "success",
                "message": "Call record already registered",
                "record_id": existing.id,
                "phone_number": existing.phone_number,
                "agent": existing.sarvam_agent.name if existing.sarvam_agent else None
            }, status=200)

        # 6. Create IN_PROGRESS SarvamCallRecord immediately
        summary_payload = {
            "source": "tata_smartflo",
            "tata_uuid": uuid_val,
            "tata_call_id": call_id,
            "tata_call_status": call_status,
            "tata_billing_circle": billing_circle,
            "call_to_number": str(call_to_number),
            "answer_agent_number": answer_agent_number,
            "received_payload": raw_data
        }

        rec = SarvamCallRecord.objects.create(
            sarvam_agent=target_agent,
            attempt_id=attempt_id or f"tata_{int(time.time())}",
            phone_number=clean_caller_phone or "unknown",
            candidate_name="Valued Customer",
            language="hi-IN",
            applied_position="General Inquiry",
            status="IN_PROGRESS",
            call_type="Inbound Call",
            start_time=call_start_dt,
            summary=summary_payload,
            transcript="",
            audio_url=""
        )

        logger.info(
            f"✅ [TATA SMARTFLO INBOUND CREATED]: Created CallRecord #{rec.id} | "
            f"Caller: {rec.phone_number} | Agent: {target_agent.name if target_agent else 'Unassigned'} | "
            f"DID: {call_to_number} | Status: IN_PROGRESS"
        )

        return Response({
            "status": "success",
            "message": "Tata Smartflo inbound call registered successfully",
            "record_id": rec.id,
            "phone_number": rec.phone_number,
            "agent": target_agent.name if target_agent else None
        }, status=200)

    except Exception as e:
        logger.error(f"❌ [TATA SMARTFLO WEBHOOK ERROR]: {e}", exc_info=True)
        return Response({"status": "error", "message": str(e)}, status=500)

