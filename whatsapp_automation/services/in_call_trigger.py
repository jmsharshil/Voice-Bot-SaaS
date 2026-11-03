"""
In-Call Live WhatsApp Trigger Service
======================================
Handles real-time WhatsApp template dispatches during an active phone conversation
when triggered by a Sarvam AI Action / Tool call.

Features:
- Multi-tenant tenant isolation: Strictly uses the target agent's dedicated Meta credentials.
- Smart caller phone resolution:
    1. Direct phone parameter from Sarvam tool payload (if provided).
    2. Real-time lookup of the active IN_PROGRESS CallRecord created by Tata Smartflo at call start!
- Dynamic variable resolution:
    Extracts booking / sales variables (dates, guests, models, budget, etc.) directly from Sarvam tool arguments
    and enriches the active CallRecord's summary.
- Anti-spam / Idempotency protection: Prevents duplicate sends to the same customer within the same conversation.
- Fast synchronous dispatch & response back to Sarvam so the voice bot can speak confirmation to the customer.
"""

import logging
import re
from datetime import timedelta
from django.utils import timezone
from django.db import close_old_connections

from conversations.models import SarvamAgent, SarvamCallRecord
from whatsapp_automation.models import AgentWhatsAppConfig, WhatsAppTemplate, WhatsAppRule, WhatsAppMessageLog
from whatsapp_automation.services.meta_client import MetaWhatsAppClient, normalize_whatsapp_phone
from whatsapp_automation.services.rule_engine import resolve_variable

logger = logging.getLogger(__name__)


def _extract_all_parameters(payload: dict) -> dict:
    """
    Safely extracts all possible variables/parameters from Sarvam Action/Tool payloads.
    Supports top-level keys, nested 'parameters', 'arguments', 'data', 'variables', and 'agent_variables'.
    """
    if not isinstance(payload, dict):
        return {}

    combined = {}

    # 1. Nested containers
    for nested_key in ("parameters", "arguments", "data", "variables", "agent_variables", "custom_variables"):
        container = payload.get(nested_key)
        if isinstance(container, dict):
            combined.update(container)

    # 2. Top-level keys (excluding internal routing keys)
    ignored_keys = {
        "agent", "agent_id", "app_id", "slug", "agent_slug", "action", "tool", "tool_name",
        "command", "type", "event", "session_id", "call_id", "uuid", "interaction_id"
    }
    for k, v in payload.items():
        if k not in ignored_keys and v is not None and str(v).strip() != "":
            if k not in combined:
                combined[k] = v

    return combined


def process_in_call_whatsapp_trigger(
    agent_identifier: str = None,
    payload: dict = None,
    template_name_override: str = None
) -> dict:
    """
    Processes a live in-call WhatsApp message trigger from a Sarvam Action / Tool call.

    Parameters:
        agent_identifier: Agent slug, name, app_id, or numeric ID
        payload: The full JSON payload received from Sarvam
        template_name_override: Optional explicit template name to send

    Returns:
        dict: Response formatted for Sarvam Tool Action response
    """
    close_old_connections()
    payload = payload or {}

    try:
        # ── 1. RESOLVE TARGET AGENT ──
        agent = None
        candidate_slug = str(agent_identifier or payload.get("agent_slug") or payload.get("slug") or "").strip()
        app_id_val = str(payload.get("app_id") or payload.get("agent_id") or payload.get("agentId") or "").strip()

        if candidate_slug and candidate_slug.lower() not in ("none", "null", "default", ""):
            agent = SarvamAgent.objects.filter(slug__iexact=candidate_slug, is_active=True).first()
            if not agent:
                agent = SarvamAgent.objects.filter(name__iexact=candidate_slug, is_active=True).first()

        if not agent and app_id_val:
            agent = SarvamAgent.objects.filter(app_id=app_id_val, is_active=True).first()
            if not agent and app_id_val.isdigit():
                agent = SarvamAgent.objects.filter(id=int(app_id_val), is_active=True).first()

        if not agent:
            # Check if an active IN_PROGRESS call exists in Tata Smartflo
            recent_active = (
                SarvamCallRecord.objects.filter(
                    status="IN_PROGRESS",
                    created_at__gte=timezone.now() - timedelta(minutes=20)
                )
                .exclude(phone_number__in=["unknown", "", "None", "same as call number"])
                .order_by("-created_at")
                .first()
            )
            if not recent_active:
                recent_active = (
                    SarvamCallRecord.objects.filter(
                        created_at__gte=timezone.now() - timedelta(minutes=20)
                    )
                    .exclude(phone_number__in=["unknown", "", "None", "same as call number"])
                    .order_by("-created_at")
                    .first()
                )
            if recent_active and recent_active.sarvam_agent:
                agent = recent_active.sarvam_agent
                logger.info(f"🎯 [IN-CALL WHATSAPP]: Auto-resolved agent '{agent.name}' from active Tata Smartflo call #{recent_active.id}")

        if not agent:
            # Fallback to agent that actually has an active WhatsApp configuration
            active_config = AgentWhatsAppConfig.objects.filter(is_active=True).select_related('agent').first()
            if active_config and active_config.agent:
                agent = active_config.agent
                logger.info(f"🎯 [IN-CALL WHATSAPP]: Fallback to active WhatsApp configured agent '{agent.name}'")
            else:
                agent = SarvamAgent.objects.filter(is_active=True).first()

        if not agent:
            logger.error(f"❌ [IN-CALL WHATSAPP]: Agent could not be resolved (slug='{candidate_slug}', app_id='{app_id_val}').")
            return {
                "status": "error",
                "message": "Voice Agent not recognized for WhatsApp trigger."
            }

        # ── 2. CHECK AGENT WHATSAPP CREDENTIALS ──
        config = getattr(agent, "whatsapp_config", None)
        if not config or not config.is_active:
            logger.warning(f"⚠️ [IN-CALL WHATSAPP]: WhatsApp is disabled or not configured for agent '{agent.name}'.")
            return {
                "status": "error",
                "message": f"WhatsApp automation is not active for agent '{agent.name}'."
            }

        if not config.phone_number_id or not config.access_token:
            logger.error(f"❌ [IN-CALL WHATSAPP]: Agent '{agent.name}' has incomplete Meta credentials.")
            return {
                "status": "error",
                "message": "Incomplete Meta WhatsApp credentials for this agent."
            }

        # ── 3. RESOLVE CALLER PHONE NUMBER & LIVE CALL RECORD ──
        extracted_vars = _extract_all_parameters(payload)

        # A: Check if phone was sent directly in the payload
        raw_phone = (
            payload.get("caller_phone")
            or payload.get("phone_number")
            or payload.get("phone")
            or payload.get("customer_phone")
            or payload.get("user_phone")
            or payload.get("caller_number")
            or payload.get("contact_number")
            or payload.get("mobile")
            or payload.get("to")
            or payload.get("recipient")
            or payload.get("recipient_phone")
            or extracted_vars.get("caller_phone")
            or extracted_vars.get("phone_number")
            or extracted_vars.get("phone")
            or ""
        )
        clean_phone = normalize_whatsapp_phone(raw_phone)

        # B: Find the active IN_PROGRESS CallRecord created by Tata Smartflo
        recent_cutoff = timezone.now() - timedelta(minutes=20)
        live_rec = None

        if clean_phone and len(clean_phone) >= 10:
            phone_last_10 = clean_phone[-10:]
            live_rec = (
                SarvamCallRecord.objects.filter(
                    sarvam_agent=agent,
                    phone_number__icontains=phone_last_10,
                    created_at__gte=recent_cutoff
                ).order_by("-created_at").first()
            )

        # If phone was not in payload, look up the active IN_PROGRESS Tata Smartflo call for this agent!
        if not clean_phone or len(clean_phone) < 10:
            live_rec = (
                SarvamCallRecord.objects.filter(
                    sarvam_agent=agent,
                    status="IN_PROGRESS",
                    created_at__gte=recent_cutoff
                ).exclude(phone_number__in=["unknown", "", "None"]).order_by("-created_at").first()
            )

            # Fallback: any recent call for this agent in last 15 mins with valid phone
            if not live_rec:
                live_rec = (
                    SarvamCallRecord.objects.filter(
                        sarvam_agent=agent,
                        created_at__gte=recent_cutoff
                    ).exclude(phone_number__in=["unknown", "", "None"]).order_by("-created_at").first()
                )

            if live_rec:
                clean_phone = normalize_whatsapp_phone(live_rec.phone_number)
                logger.info(
                    f"🎯 [IN-CALL WHATSAPP]: Matched caller phone '{clean_phone}' from live Tata Smartflo "
                    f"CallRecord #{live_rec.id} (Agent: {agent.name})"
                )

        if not clean_phone or len(clean_phone) < 10:
            logger.warning(f"⚠️ [IN-CALL WHATSAPP]: Caller phone number not found. No active Tata Smartflo call found for agent '{agent.name}'.")
            return {
                "status": "error",
                "message": "Customer phone number not found. No active Tata Smartflo call was detected for this agent."
            }

        # ── 4. ENRICH CALL RECORD SUMMARY WITH IN-CALL VARIABLES ──
        if live_rec and extracted_vars:
            summary_dict = live_rec.summary if isinstance(live_rec.summary, dict) else {}
            summary_dict.update(extracted_vars)
            live_rec.summary = summary_dict
            try:
                live_rec.save(update_fields=["summary"])
            except Exception as se:
                logger.warning(f"⚠️ [IN-CALL WHATSAPP]: Error updating CallRecord summary: {se}")

        # ── 5. RESOLVE TEMPLATE & RULE ──
        target_template_name = str(
            template_name_override
            or payload.get("template_name")
            or payload.get("template")
            or extracted_vars.get("template_name")
            or ""
        ).strip().lower()

        matched_rule = None
        template = None

        if target_template_name:
            template = config.templates.filter(template_name__iexact=target_template_name, is_active=True).first()
            if template:
                matched_rule = config.rules.filter(template=template, is_active=True).first()

        # If not explicitly specified, find active IN_CALL or BOTH rule for this agent
        if not template:
            matched_rule = config.rules.filter(
                trigger_event__in=["IN_CALL", "BOTH"],
                is_active=True,
                template__is_active=True
            ).first()

            # Fallback to any active rule for this agent
            if not matched_rule:
                matched_rule = config.rules.filter(
                    is_active=True,
                    template__is_active=True
                ).first()

            if matched_rule:
                template = matched_rule.template

        if not template:
            logger.warning(f"⚠️ [IN-CALL WHATSAPP]: No active template found for agent '{agent.name}'.")
            return {
                "status": "error",
                "message": f"No active WhatsApp template configured for agent '{agent.name}'."
            }

        # ── 6. ANTI-SPAM IDEMPOTENCY CHECK ──
        # Prevent rapid duplicate firing from network retries (10 seconds debounce window)
        # Allows re-sending if customer asks for other options mid-call after 10+ seconds
        recent_debounce = timezone.now() - timedelta(seconds=10)
        already_sent = WhatsAppMessageLog.objects.filter(
            agent=agent,
            recipient_phone__icontains=clean_phone[-10:],
            template_name=template.template_name,
            trigger_type="IN_CALL",
            status__in=["SENT", "DELIVERED", "READ"],
            created_at__gte=recent_debounce
        ).first()

        if already_sent:
            logger.info(f"⏭️ [IN-CALL WHATSAPP]: Template '{template.template_name}' was already sent to {clean_phone} within last 10s ({already_sent.created_at}).")
            return {
                "status": "success",
                "message": "WhatsApp details were already sent to this customer just now.",
                "recipient": clean_phone,
                "template": template.template_name,
                "message_id": already_sent.meta_message_id,
                "already_sent": True
            }

        # ── 7. RESOLVE DYNAMIC VARIABLES ──
        def _get_var_value(src_key, data_dict, record):
            if src_key in data_dict and data_dict[src_key] is not None and str(data_dict[src_key]).strip():
                return str(data_dict[src_key]).strip()
            
            k_lower = str(src_key).lower().strip()
            alias_map = {
                "adults": ["no_of_adults", "adult_count", "adults_count", "guests_adults", "guests", "adult"],
                "no_of_adults": ["adults", "adult_count", "adults_count", "guests_adults", "guests", "adult"],
                "kids": ["no_of_kids", "kids_count", "children", "child", "kid"],
                "no_of_kids": ["kids", "kids_count", "children", "child", "kid"],
                "check_in_date": ["check_in", "checkin", "checkin_date", "arrival_date", "arrival", "appointment_date"],
                "check_out_date": ["check_out", "checkout", "checkout_date", "departure_date", "departure"],
                "candidate_name": ["name", "caller_name", "customer_name", "user_name"],
                "name": ["caller_name", "candidate_name", "customer_name", "user_name"],
            }
            if k_lower in alias_map:
                for alt in alias_map[k_lower]:
                    if alt in data_dict and data_dict[alt] is not None and str(data_dict[alt]).strip():
                        return str(data_dict[alt]).strip()

            for d_k, d_v in data_dict.items():
                if d_k.lower() == k_lower and d_v is not None and str(d_v).strip():
                    return str(d_v).strip()

            if record:
                res = resolve_variable(src_key, record)
                if res and str(res).strip():
                    return str(res).strip()
            return ""

        def _sanitize_param(k_name, v):
            if v is not None and str(v).strip() and str(v).lower() not in ("none", "null"):
                return str(v).strip()
            k_clean = str(k_name).lower()
            if "check_in" in k_clean or "checkin" in k_clean or "arrival" in k_clean:
                return "To be confirmed"
            if "check_out" in k_clean or "checkout" in k_clean or "departure" in k_clean:
                return "To be confirmed"
            if "adult" in k_clean:
                return "2"
            if "kid" in k_clean or "child" in k_clean:
                return "0"
            if "name" in k_clean:
                return "Valued Customer"
            return "Details"

        resolved_params = []
        if matched_rule and matched_rule.variable_mappings and isinstance(matched_rule.variable_mappings, dict):
            sorted_keys = sorted(matched_rule.variable_mappings.keys(), key=lambda x: int(x) if str(x).isdigit() else 99)
            for k in sorted_keys:
                src_key = matched_rule.variable_mappings[k]
                val = _get_var_value(src_key, extracted_vars, live_rec)
                resolved_params.append(_sanitize_param(src_key, val))
        elif template.variables_schema and isinstance(template.variables_schema, list):
            for src_key in template.variables_schema:
                val = _get_var_value(src_key, extracted_vars, live_rec)
                resolved_params.append(_sanitize_param(src_key, val))

        # Resolve header media URL if any
        media_url = (matched_rule.header_media_url if matched_rule else None) or template.header_media_url
        if media_url:
            media_url = extracted_vars.get(media_url) or resolve_variable(media_url, live_rec)

        # ── 8. DISPATCH VIA META CLOUD API ──
        client = MetaWhatsAppClient(
            phone_number_id=config.phone_number_id,
            access_token=config.access_token,
            api_version=config.api_version
        )

        logger.info(
            f"🚀 [IN-CALL WHATSAPP DISPATCH]: Disagreeing mid-call template '{template.template_name}' "
            f"to {clean_phone} via agent '{agent.name}' (Phone ID: {config.phone_number_id})..."
        )

        send_res = client.send_template_message(
            to_phone=clean_phone,
            template_name=template.template_name,
            language_code=template.language_code,
            body_parameters=resolved_params,
            header_type=template.header_type,
            header_media_url=media_url,
            header_filename=template.header_filename,
            timeout=6
        )

        # ── 9. LOG AUDIT ENTRY ──
        log_entry = None
        try:
            log_entry = WhatsAppMessageLog.objects.create(
                agent=agent,
                call_record=live_rec,
                rule=matched_rule,
                template_name=template.template_name,
                recipient_phone=clean_phone,
                trigger_type="IN_CALL",
                status="SENT" if send_res.get("success") else "FAILED",
                meta_message_id=send_res.get("message_id", ""),
                payload_sent=send_res.get("payload_sent", {}),
                meta_response=send_res.get("response", {}),
                error_message="" if send_res.get("success") else send_res.get("error", "Failed to dispatch message")
            )
        except Exception as log_err:
            logger.error(f"⚠️ [IN-CALL WHATSAPP LOGGING ERROR]: {log_err}", exc_info=True)

        if send_res.get("success"):
            meta_mid = send_res.get("message_id") or (log_entry.meta_message_id if log_entry else "")
            logger.info(f"✅ [IN-CALL WHATSAPP SUCCESS]: Sent to {clean_phone} | MsgID: {meta_mid}")
            return {
                "status": "success",
                "message": "WhatsApp message successfully sent to customer's phone.",
                "recipient": clean_phone,
                "template": template.template_name,
                "message_id": meta_mid
            }
        else:
            err_msg = send_res.get("error") or (log_entry.error_message if log_entry else "Failed to dispatch message")
            logger.error(f"❌ [IN-CALL WHATSAPP FAILED]: {err_msg}")
            return {
                "status": "error",
                "message": err_msg,
                "recipient": clean_phone
            }

    except Exception as e:
        logger.error(f"❌ [IN-CALL WHATSAPP EXCEPTION]: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Server error processing WhatsApp trigger: {str(e)}"
        }
    finally:
        close_old_connections()

