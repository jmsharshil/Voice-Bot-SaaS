import logging
from datetime import timedelta
from django.utils import timezone
from conversations.models import SarvamCallRecord

logger = logging.getLogger("sarvam_ivr_bridge")


def correlate_ivr_log(ivr_log):
    """
    Attempts to match an incoming IVRForwardedCallLog with an existing SarvamCallRecord.
    Returns True if matched, False otherwise.
    """
    if not ivr_log.agent_config or not ivr_log.agent_config.is_active:
        ivr_log.match_status = "IGNORED"
        ivr_log.save(update_fields=["match_status"])
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
    for cand in candidates:
        # Check duration match if enabled
        if ivr_log.agent_config.match_by_duration and ivr_log.duration_seconds > 0 and cand.duration_seconds > 0:
            diff = abs(ivr_log.duration_seconds - cand.duration_seconds)
            if diff <= 20:  # Within 20 seconds tolerance
                best_match = cand
                break
        else:
            best_match = cand
            break

    if best_match:
        ivr_log.sarvam_call_record = best_match
        ivr_log.match_status = "MATCHED"
        ivr_log.matched_at = timezone.now()
        ivr_log.save(update_fields=["sarvam_call_record", "match_status", "matched_at"])

        if ivr_log.agent_config.auto_update_sarvam_record:
            old_num = best_match.phone_number
            best_match.phone_number = ivr_log.real_caller_number
            best_match.save(update_fields=["phone_number"])
            logger.info(
                "🎯 [SARVAM IVR MATCH]: Correlated IVR Log #%s with SarvamCallRecord #%s. Updated caller from '%s' to '%s'",
                ivr_log.id, best_match.id, old_num, ivr_log.real_caller_number
            )
        return True

    return False


def try_resolve_ivr_forwarded_caller(sarvam_record):
    """
    Called when a SarvamCallRecord is received/updated.
    Checks if the record's agent has an active IVR Forwarding configuration.
    If so, tries to find a matching pending IVRForwardedCallLog.
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
    for log in pending_logs:
        if config.match_by_duration and log.duration_seconds > 0 and sarvam_record.duration_seconds > 0:
            diff = abs(log.duration_seconds - sarvam_record.duration_seconds)
            if diff <= 20:
                best_log = log
                break
        else:
            best_log = log
            break

    if best_log:
        best_log.sarvam_call_record = sarvam_record
        best_log.match_status = "MATCHED"
        best_log.matched_at = timezone.now()
        best_log.save(update_fields=["sarvam_call_record", "match_status", "matched_at"])

        if config.auto_update_sarvam_record:
            old_num = sarvam_record.phone_number
            sarvam_record.phone_number = best_log.real_caller_number
            sarvam_record.save(update_fields=["phone_number"])
            logger.info(
                "🎯 [SARVAM IVR MATCH]: Resolved real caller '%s' for SarvamCallRecord #%s from IVR Log #%s",
                best_log.real_caller_number, sarvam_record.id, best_log.id
            )
        return True

    return False

