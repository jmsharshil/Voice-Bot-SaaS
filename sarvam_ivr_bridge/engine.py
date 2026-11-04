import logging
from datetime import timedelta
from django.utils import timezone
from conversations.models import SarvamCallRecord

logger = logging.getLogger("sarvam_ivr_bridge")


def correlate_ivr_log(ivr_log):
    """
    Attempts to match an incoming IVRForwardedCallLog with an existing SarvamCallRecord.
    Uses multi-attribute weighted scoring (duration delta + timestamp delta) to select
    the exact matching call record, even when multiple calls occur concurrently.
    Returns True if matched, False otherwise.
    """
    if not ivr_log.agent_config or not ivr_log.agent_config.is_active:
        ivr_log.match_status = "IGNORED"
        ivr_log.save(update_fields=["match_status"])
        return False

    # Do not match mid-call events or logs missing a real phone number
    if ivr_log.disposition in ["LIVECALL", "RINGING"] or not ivr_log.real_caller_number or ivr_log.real_caller_number in ["unknown", "none", "null", ""]:
        return False

    agent = ivr_log.agent_config.sarvam_agent
    window_mins = ivr_log.agent_config.time_window_minutes or 10
    ref_time = ivr_log.call_start_time or ivr_log.created_at or timezone.now()
    start_threshold = ref_time - timedelta(minutes=window_mins)
    end_threshold = ref_time + timedelta(minutes=window_mins)

    # Search candidate SarvamCallRecords for this agent within the time window
    candidates = SarvamCallRecord.objects.filter(
        sarvam_agent=agent,
        created_at__range=(start_threshold, end_threshold),
        ivr_forwarded_log__isnull=True  # Exclude already matched records
    ).order_by("-created_at")

    best_match = None
    min_score = float("inf")
    for cand in candidates:
        cand_time = cand.start_time or cand.created_at or timezone.now()
        time_diff_sec = abs((ref_time - cand_time).total_seconds())
        dur_diff_sec = abs(ivr_log.duration_seconds - cand.duration_seconds) if (ivr_log.duration_seconds > 0 and cand.duration_seconds > 0) else 0.0

        # Reject if call duration difference is too wide when duration checking is enabled
        tolerance_sec = getattr(ivr_log.agent_config, "duration_tolerance_seconds", 60)
        if ivr_log.agent_config.match_by_duration and ivr_log.duration_seconds > 0 and cand.duration_seconds > 0:
            if dur_diff_sec > tolerance_sec:  # Configurable tolerance (default 60 seconds)
                continue

        # Weighted score: duration match weighted higher than small time differences
        score = (dur_diff_sec * 2.0) + (time_diff_sec / 5.0)
        if score < min_score:
            min_score = score
            best_match = cand

    if best_match:
        ivr_log.sarvam_call_record = best_match
        ivr_log.match_status = "MATCHED"
        ivr_log.matched_at = timezone.now()
        ivr_log.save(update_fields=["sarvam_call_record", "match_status", "matched_at"])

        update_fields = []
        if ivr_log.agent_config.auto_update_sarvam_record:
            old_num = best_match.phone_number
            best_match.phone_number = ivr_log.real_caller_number
            update_fields.append("phone_number")
            logger.info(
                "🎯 [SARVAM IVR MATCH]: Correlated IVR Log #%s with SarvamCallRecord #%s (score=%.2f). Updated caller from '%s' to '%s'",
                ivr_log.id, best_match.id, min_score, old_num, ivr_log.real_caller_number
            )

        # Attach IVR recording URL if Sarvam audio is missing
        if ivr_log.recording_url and not best_match.audio_url:
            best_match.audio_url = ivr_log.recording_url
            update_fields.append("audio_url")
            logger.info("🎙️ [SARVAM IVR AUDIO]: Attached IVR recording URL to SarvamCallRecord #%s", best_match.id)

        if update_fields:
            best_match.save(update_fields=update_fields)

        return True

    return False


def try_resolve_ivr_forwarded_caller(sarvam_record):
    """
    Called when a SarvamCallRecord is received/updated.
    Checks if the record's agent has an active IVR Forwarding configuration.
    If so, searches for a matching pending IVRForwardedCallLog using multi-attribute scoring.
    """
    if not sarvam_record or not sarvam_record.sarvam_agent:
        return False

    agent = sarvam_record.sarvam_agent
    config = getattr(agent, "ivr_forwarding_config", None)
    if not config or not config.is_active:
        return False

    # Check if this record is already matched
    if hasattr(sarvam_record, "ivr_forwarded_log") and sarvam_record.ivr_forwarded_log:
        return True

    window_mins = config.time_window_minutes or 10
    ref_time = sarvam_record.start_time or sarvam_record.created_at or timezone.now()
    start_threshold = ref_time - timedelta(minutes=window_mins)
    end_threshold = ref_time + timedelta(minutes=window_mins)

    from sarvam_ivr_bridge.models import IVRForwardedCallLog
    pending_logs = IVRForwardedCallLog.objects.filter(
        agent_config=config,
        match_status="PENDING",
        created_at__range=(start_threshold, end_threshold)
    ).order_by("-created_at")

    best_log = None
    min_score = float("inf")
    for log in pending_logs:
        # Ignore mid-call events or logs without a valid phone number
        if log.disposition in ["LIVECALL", "RINGING"]:
            continue
        if not log.real_caller_number or log.real_caller_number.lower() in ["unknown", "none", "null", ""]:
            continue

        log_time = log.call_start_time or log.created_at or timezone.now()
        time_diff_sec = abs((ref_time - log_time).total_seconds())
        dur_diff_sec = abs(log.duration_seconds - sarvam_record.duration_seconds) if (log.duration_seconds > 0 and sarvam_record.duration_seconds > 0) else 0.0

        tolerance_sec = getattr(config, "duration_tolerance_seconds", 60)
        if config.match_by_duration and log.duration_seconds > 0 and sarvam_record.duration_seconds > 0:
            if dur_diff_sec > tolerance_sec:  # Configurable tolerance (default 60 seconds)
                continue

        score = (dur_diff_sec * 2.0) + (time_diff_sec / 5.0)
        if score < min_score:
            min_score = score
            best_log = log

    if best_log:
        best_log.sarvam_call_record = sarvam_record
        best_log.match_status = "MATCHED"
        best_log.matched_at = timezone.now()
        best_log.save(update_fields=["sarvam_call_record", "match_status", "matched_at"])

        update_fields = []
        if config.auto_update_sarvam_record:
            old_num = sarvam_record.phone_number
            sarvam_record.phone_number = best_log.real_caller_number
            update_fields.append("phone_number")
            logger.info(
                "🎯 [SARVAM IVR MATCH]: Resolved real caller '%s' for SarvamCallRecord #%s from IVR Log #%s (score=%.2f)",
                best_log.real_caller_number, sarvam_record.id, best_log.id, min_score
            )

        # Attach IVR recording URL if Sarvam audio is missing
        if best_log.recording_url and not sarvam_record.audio_url:
            sarvam_record.audio_url = best_log.recording_url
            update_fields.append("audio_url")
            logger.info("🎙️ [SARVAM IVR AUDIO]: Attached IVR recording URL to SarvamCallRecord #%s", sarvam_record.id)

        if update_fields:
            sarvam_record.save(update_fields=update_fields)

        return True

    return False
