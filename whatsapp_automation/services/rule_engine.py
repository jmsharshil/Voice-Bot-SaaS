"""
WhatsApp Rule Engine & Variable Resolver
=========================================
Evaluates conditional trigger rules per agent for completed calls,
and dynamically extracts template variables from call records & summaries.
"""

import logging
from typing import List, Tuple, Any

logger = logging.getLogger(__name__)


def resolve_variable(key: str, call_record) -> str:
    """
    Dynamically extracts variable values from a SarvamCallRecord.
    Supports:
      - candidate_name, name, customer_name -> Customer name
      - agent_name -> Agent name
      - agent_phone -> Agent caller number
      - company_name -> Demo company name or agent name
      - phone_number, phone -> Customer phone
      - status -> Call status
      - duration -> e.g. '120s'
      - summary.<key> -> pulls directly from call_record.summary dict (e.g. summary.car_model, summary.appointment_date)
      - extra.<key> -> pulls from summary or extra_data
      - literal string -> returns key as fallback
    """
    if not key or not call_record:
        return ""

    k = str(key).strip()
    k_lower = k.lower()

    # Hospitality / Villa Booking smart aliases
    if k_lower in ("check_in_date", "check_in", "checkin", "checkin_date", "arrival_date"):
        if isinstance(call_record.summary, dict):
            for fk in ("check_in_date", "check_in", "checkin", "checkin_date", "arrival_date", "arrival", "appointment_date"):
                val = call_record.summary.get(fk)
                if val and str(val).strip() and str(val).lower() not in ("none", "null"):
                    return str(val).strip()
        return "To be confirmed"

    if k_lower in ("check_out_date", "check_out", "checkout", "checkout_date", "departure_date"):
        if isinstance(call_record.summary, dict):
            for fk in ("check_out_date", "check_out", "checkout", "checkout_date", "departure_date", "departure"):
                val = call_record.summary.get(fk)
                if val and str(val).strip() and str(val).lower() not in ("none", "null"):
                    return str(val).strip()
        return "To be confirmed"

    if k_lower in ("adults", "no_of_adults", "adult_count", "adults_count", "guests_adults"):
        if isinstance(call_record.summary, dict):
            for fk in ("adults", "no_of_adults", "adult_count", "adults_count", "guests_adults", "guests"):
                val = call_record.summary.get(fk)
                if val is not None and str(val).strip() and str(val).lower() not in ("none", "null"):
                    return str(val).strip()
        return "2"

    if k_lower in ("kids", "no_of_kids", "kids_count", "children", "child"):
        if isinstance(call_record.summary, dict):
            for fk in ("kids", "no_of_kids", "kids_count", "children", "child"):
                val = call_record.summary.get(fk)
                if val is not None and str(val).strip() and str(val).lower() not in ("none", "null"):
                    return str(val).strip()
        return "0"

    # Direct top-level attributes
    if k_lower in ("candidate_name", "name", "customer_name", "user_name"):
        val = call_record.candidate_name
        return str(val).strip() if val and val.lower() not in ("candidate", "valued customer", "customer", "none", "null") else "Valued Customer"

    if k_lower in ("agent_name", "bot_name", "agent"):
        if call_record.sarvam_agent:
            return call_record.sarvam_agent.name
        return "Voice AI Agent"

    if k_lower in ("agent_phone", "did"):
        if call_record.sarvam_agent and call_record.sarvam_agent.agent_phone:
            return call_record.sarvam_agent.agent_phone
        return ""

    if k_lower in ("company_name", "company"):
        if call_record.sarvam_agent:
            return call_record.sarvam_agent.demo_company_name or call_record.sarvam_agent.name
        return "Our Team"

    if k_lower in ("phone_number", "phone", "user_phone"):
        return str(call_record.phone_number or "")

    if k_lower in ("status", "lead_status"):
        return str(call_record.status or "")

    if k_lower in ("duration", "duration_seconds"):
        return f"{int(call_record.duration_seconds or 0)}s"

    if k_lower in ("call_summary", "summary_text"):
        if isinstance(call_record.summary, dict):
            return str(call_record.summary.get("call_summary") or call_record.summary.get("summary") or "")
        return ""

    # Dotted notation: summary.<field>
    if k_lower.startswith("summary."):
        field = k[8:].strip()
        if isinstance(call_record.summary, dict):
            val = call_record.summary.get(field)
            if val is not None and str(val).strip() != "" and str(val).lower() not in ("none", "null"):
                return str(val).strip()
        return ""

    # Dotted notation: extra.<field>
    if k_lower.startswith("extra."):
        field = k[6:].strip()
        if isinstance(call_record.summary, dict):
            val = call_record.summary.get(field)
            if val is not None and str(val).strip() != "":
                return str(val).strip()
        return ""

    # Check directly inside summary dict if key exists
    if isinstance(call_record.summary, dict):
        if k in call_record.summary and call_record.summary[k]:
            return str(call_record.summary[k]).strip()
        # Case-insensitive search in summary keys
        for sk, sv in call_record.summary.items():
            if sk.lower() == k_lower and sv:
                return str(sv).strip()

    # Fallback to string literal
    return k


def match_rule_for_call(rule, call_record) -> bool:
    """
    Returns True if call_record satisfies all conditions of the rule.
    """
    # 1. Minimum duration check
    call_dur = float(call_record.duration_seconds or 0.0)
    if call_dur < float(rule.min_duration_seconds or 0):
        return False

    # 2. Status match check
    raw_trigger_statuses = rule.trigger_statuses or "ANY"
    if raw_trigger_statuses.strip().upper() != "ANY":
        trigger_list = [s.strip().upper() for s in raw_trigger_statuses.split(",") if s.strip()]
        
        # Candidate status strings from record
        record_statuses = set()
        if call_record.status:
            record_statuses.add(str(call_record.status).strip().upper())
        if hasattr(call_record, "pipeline_stage") and call_record.pipeline_stage:
            record_statuses.add(str(call_record.pipeline_stage).strip().upper())
        if isinstance(call_record.summary, dict):
            if call_record.summary.get("final_status"):
                record_statuses.add(str(call_record.summary["final_status"]).strip().upper())

        # Check for intersection or alias matches (e.g. INTERVIEW == INTERESTED)
        INTERESTED_ALIASES = {"INTERESTED", "INTERVIEW", "HIGH_INTENT", "POSITIVE", "CONFIRMED", "BOOKING_CONFIRMED"}
        CALLBACK_ALIASES = {"CALLBACK", "FOLLOW_UP", "WHATSAPP"}
        NOT_INT_ALIASES = {"NOT_INTERESTED", "DECLINED", "REJECTED"}

        matched_status = False
        for req_st in trigger_list:
            if req_st in record_statuses:
                matched_status = True
                break
            if req_st in INTERESTED_ALIASES and bool(record_statuses & INTERESTED_ALIASES):
                matched_status = True
                break
            if req_st in CALLBACK_ALIASES and bool(record_statuses & CALLBACK_ALIASES):
                matched_status = True
                break
            if req_st in NOT_INT_ALIASES and bool(record_statuses & NOT_INT_ALIASES):
                matched_status = True
                break

        if not matched_status:
            return False

    # 3. Required Tag check
    if rule.required_tag and rule.required_tag.strip():
        req_tag_clean = rule.required_tag.strip().lower()
        has_tag = False
        if isinstance(call_record.summary, dict):
            tags = call_record.summary.get("tags") or []
            if isinstance(tags, list):
                has_tag = any(req_tag_clean in str(t).lower() for t in tags)
            elif isinstance(tags, str):
                has_tag = req_tag_clean in tags.lower()
        if not has_tag:
            return False

    # 4. Required Keyword check (transcript or summary)
    if rule.required_keyword and rule.required_keyword.strip():
        req_kw = rule.required_keyword.strip().lower()
        text_corpus = f"{call_record.transcript or ''} {str(call_record.summary or '')}".lower()
        if req_kw not in text_corpus:
            return False

    return True


def evaluate_rules_for_call(call_record) -> List[Tuple[Any, list, str]]:
    """
    Evaluates all active rules for the call_record's SarvamAgent.
    Returns a list of tuples:
       (rule, resolved_body_parameters, resolved_header_media_url)
    Returns [] if agent has no WhatsApp config or if no rules match.
    """
    if not call_record or not call_record.sarvam_agent:
        return []

    agent = call_record.sarvam_agent

    # 1. Check if agent has active WhatsApp configuration
    config = getattr(agent, "whatsapp_config", None)
    if not config or not config.is_active:
        return []

    if not config.phone_number_id or not config.access_token:
        logger.warning(f"⚠️ [WHATSAPP ENGINE]: Agent '{agent.name}' has incomplete Meta credentials.")
        return []

    from whatsapp_automation.models import WhatsAppRule, WhatsAppMessageLog

    # 2. Fetch all active rules for this agent
    active_rules = WhatsAppRule.objects.filter(
        agent_config=config,
        is_active=True,
        template__is_active=True
    ).select_related("template")

    matched_dispatches = []

    for rule in active_rules:
        # Idempotency check: Don't process if already logged (Sent, Delivered, Queued)
        if WhatsAppMessageLog.objects.filter(call_record=call_record, rule=rule).exists():
            continue

        if not match_rule_for_call(rule, call_record):
            continue

        template = rule.template

        # Resolve variables: use rule variable_mappings if defined, otherwise template variables_schema
        resolved_params = []
        if rule.variable_mappings and isinstance(rule.variable_mappings, dict):
            # Sort by variable index ('1', '2', '3')
            sorted_keys = sorted(rule.variable_mappings.keys(), key=lambda x: int(x) if str(x).isdigit() else 99)
            for k in sorted_keys:
                source_key = rule.variable_mappings[k]
                resolved_params.append(resolve_variable(source_key, call_record))
        elif template.variables_schema and isinstance(template.variables_schema, list):
            for source_key in template.variables_schema:
                resolved_params.append(resolve_variable(source_key, call_record))

        # Resolve header media URL
        media_url = rule.header_media_url or template.header_media_url
        if media_url:
            media_url = resolve_variable(media_url, call_record)

        matched_dispatches.append((rule, resolved_params, media_url))

    return matched_dispatches

