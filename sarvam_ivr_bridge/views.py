import json
import logging
from datetime import datetime
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from conversations.models import SarvamAgent
from sarvam_ivr_bridge.models import AgentIVRForwardingConfig, IVRForwardedCallLog
from sarvam_ivr_bridge.engine import correlate_ivr_log

logger = logging.getLogger("sarvam_ivr_bridge")


def _clean_phone(raw_num):
    if not raw_num:
        return ""
    digits = "".join(filter(str.isdigit, str(raw_num)))
    if len(digits) > 10:
        return digits[-10:]
    return digits


@csrf_exempt
@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def ivr_webhook_receiver(request, agent_slug=None):
    """
    Generic webhook receiver for external client IVR systems forwarding calls to Sarvam Voice Agents.
    Endpoints:
      - POST /api/sarvam-ivr/webhook/
      - POST /api/sarvam-ivr/<slug:agent_slug>/webhook/
    """
    raw_data = getattr(request, "data", {}) or {}
    if not raw_data and request.body:
        try:
            raw_data = json.loads(request.body.decode("utf-8"))
        except Exception:
            raw_data = request.POST.dict()

    logger.info("📥 [SARVAM IVR WEBHOOK RECEIVED]: agent_slug=%s | Payload: %s", agent_slug, raw_data)

    # 1. Resolve Target Agent & IVR Config
    target_config = None
    if agent_slug:
        agent = SarvamAgent.objects.filter(slug__iexact=agent_slug, is_active=True).first()
        if agent:
            target_config = AgentIVRForwardingConfig.objects.filter(sarvam_agent=agent, is_active=True).first()

    # 2. Build case-insensitive and whitespace-stripped normalized dictionary
    norm_data = {str(k).strip().lower().replace(" ", "_"): v for k, v in raw_data.items()}
    # Also merge direct raw_data so original keys are accessible
    combined_lookup = dict(raw_data)
    combined_lookup.update(norm_data)

    # Extract standard fields from payload (supports IVRManager, Voicelink, Tata, Twilio, and Generic formats)
    caller_raw = (
        combined_lookup.get("phone_number")
        or combined_lookup.get("caller_id")
        or combined_lookup.get("callercli")
        or combined_lookup.get("caller_number")
        or combined_lookup.get("caller")
        or combined_lookup.get("cli")
        or combined_lookup.get("from")
        or combined_lookup.get("From")
        or combined_lookup.get("mobile")
        or combined_lookup.get("mobilenumber")
        or ""
    )
    real_caller = _clean_phone(caller_raw)

    # Fallback 1: If phone_number is not set, check if call_id holds the caller's phone number (e.g. '+919104142402')
    if not real_caller or real_caller.lower() in ["unknown", "none", "null"]:
        cid_candidate = str(combined_lookup.get("call_id") or combined_lookup.get("calluniqueid") or "").strip()
        cid_digits = "".join(filter(str.isdigit, cid_candidate))
        if len(cid_digits) >= 10:
            real_caller = cid_digits[-10:]

    # Fallback 2: Check if resource_url / recording URL contains the phone number (e.g. '...-+919104142402.mp3')
    if not real_caller or real_caller.lower() in ["unknown", "none", "null"]:
        import re
        rec_url = str(combined_lookup.get("resource_url") or combined_lookup.get("recordings_location") or "")
        match_num = re.search(r'(\+?91)?[6-9]\d{9}', rec_url)
        if match_num:
            real_caller = "".join(filter(str.isdigit, match_num.group(0)))[-10:]

    did_raw = (
        combined_lookup.get("did")
        or combined_lookup.get("forwarded_did")
        or combined_lookup.get("called_number")
        or combined_lookup.get("destination")
        or combined_lookup.get("to")
        or combined_lookup.get("To")
        or ""
    )
    clean_did = "".join(filter(str.isdigit, str(did_raw)))

    # Fallback resolution of config by DID if agent_slug was not provided
    if not target_config and clean_did:
        for cfg in AgentIVRForwardingConfig.objects.filter(is_active=True):
            if any(kd in clean_did for kd in cfg.get_did_list()):
                target_config = cfg
                break

    if not target_config:
        logger.warning(
            "⚠️ [SARVAM IVR WEBHOOK]: No active AgentIVRForwardingConfig found for slug='%s', DID='%s'. Logging as ignored.",
            agent_slug, clean_did
        )

    # Extract call duration
    raw_dur = (
        combined_lookup.get("call_duration")
        or combined_lookup.get("duration")
        or combined_lookup.get("duration_in_seconds")
        or combined_lookup.get("callduration")
        or 0
    )
    try:
        duration_sec = float(raw_dur)
    except Exception:
        duration_sec = 0.0

    # Extract disposition / status
    disposition = str(
        combined_lookup.get("callstatus")
        or combined_lookup.get("call_status")
        or combined_lookup.get("disposition")
        or combined_lookup.get("status")
        or "ANSWERED"
    ).upper()

    # Extract recording url
    recording_url = str(
        combined_lookup.get("recordings_location")
        or combined_lookup.get("recording_location")
        or combined_lookup.get("resource_url")
        or combined_lookup.get("recording_url")
        or combined_lookup.get("recordingurl")
        or ""
    )

    # Extract external call id
    call_id = str(
        combined_lookup.get("calluniqueid")
        or combined_lookup.get("call_id")
        or combined_lookup.get("uniqueid")
        or combined_lookup.get("callsid")
        or ""
    )

    # Parse timestamps
    start_time_str = (
        combined_lookup.get("datetime")
        or combined_lookup.get("call_date")
        or combined_lookup.get("calldate")
        or combined_lookup.get("start_time")
        or combined_lookup.get("created_at")
        or combined_lookup.get("endtime")
    )
    parsed_start_time = None
    if start_time_str:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
            try:
                parsed_start_time = datetime.strptime(str(start_time_str).split(".")[0], fmt)
                break
            except Exception:
                pass

    if not parsed_start_time:
        parsed_start_time = timezone.now()

    # 3. Create IVRForwardedCallLog
    ivr_log = IVRForwardedCallLog.objects.create(
        agent_config=target_config,
        real_caller_number=real_caller or "unknown",
        forwarded_did=clean_did,
        ivr_call_id=call_id,
        call_start_time=parsed_start_time,
        duration_seconds=duration_sec,
        disposition=disposition,
        recording_url=recording_url,
        raw_payload=raw_data,
        match_status="PENDING" if target_config else "IGNORED"
    )

    # 4. Trigger correlation engine if config is active
    matched = False
    if target_config and target_config.is_active:
        if disposition in ["LIVECALL", "RINGING"] or duration_sec <= 0 or real_caller in ["unknown", "none", "null", ""]:
            ivr_log.match_status = "PENDING"
            ivr_log.save(update_fields=["match_status"])
        else:
            matched = correlate_ivr_log(ivr_log)

    return Response({
        "status": "success",
        "log_id": ivr_log.id,
        "matched": matched,
        "agent": target_config.sarvam_agent.name if target_config else None,
        "real_caller": real_caller
    }, status=201)

