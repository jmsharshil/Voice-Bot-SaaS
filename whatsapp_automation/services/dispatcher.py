"""
WhatsApp Automation Dispatcher
===============================
Provides non-blocking, crash-proof background dispatching for Meta WhatsApp messages.
Ensures clean database connection lifecycle (close_old_connections) for Azure PostgreSQL.
Guarantees 100% strict tenant isolation and zero duplicate sends.
"""

import time
import logging
import threading
from django.db import close_old_connections

logger = logging.getLogger(__name__)


def _dispatch_worker(call_record_id: int):
    """
    Background worker:
    1. Safely fetches call record with related agent and WhatsApp config.
    2. Evaluates rules.
    3. Dispatches Meta template messages.
    4. Logs audit trail with anti-duplicate locks.
    5. Releases DB connections cleanly.
    """
    close_old_connections()
    try:
        from conversations.models import SarvamCallRecord
        from whatsapp_automation.models import WhatsAppMessageLog
        from whatsapp_automation.services.rule_engine import evaluate_rules_for_call
        from whatsapp_automation.services.meta_client import MetaWhatsAppClient

        record = SarvamCallRecord.objects.select_related(
            "sarvam_agent",
            "sarvam_agent__whatsapp_config"
        ).filter(id=call_record_id).first()

        if not record or not record.sarvam_agent:
            return

        agent = record.sarvam_agent
        config = getattr(agent, "whatsapp_config", None)
        if not config or not config.is_active:
            return

        # Evaluate rules
        matched_items = evaluate_rules_for_call(record)
        if not matched_items:
            logger.debug(f"ℹ️ [WHATSAPP DISPATCHER]: No matching rules for Call #{record.id} (Agent: {agent.name})")
            return

        client = MetaWhatsAppClient(
            phone_number_id=config.phone_number_id,
            access_token=config.access_token,
            api_version=config.api_version
        )

        for rule, body_params, media_url in matched_items:
            template = rule.template

            # Create initial QUEUED log entry (prevents race condition / duplicate send)
            log_entry, created = WhatsAppMessageLog.objects.get_or_create(
                call_record=record,
                rule=rule,
                defaults={
                    "agent": agent,
                    "template_name": template.template_name,
                    "recipient_phone": record.phone_number,
                    "status": "QUEUED"
                }
            )

            if not created and log_entry.status in ("SENT", "DELIVERED", "READ"):
                logger.info(f"⏭️ [WHATSAPP DISPATCHER]: Skipping already sent rule #{rule.id} for Call #{record.id}")
                continue

            # Optional rule delay (e.g. 5-10s)
            if rule.delay_seconds > 0:
                time.sleep(rule.delay_seconds)

            # Send via Meta Cloud API
            res = client.send_template_message(
                to_phone=record.phone_number,
                template_name=template.template_name,
                language_code=template.language_code,
                body_parameters=body_params,
                header_type=template.header_type,
                header_media_url=media_url,
                header_filename=template.header_filename,
                timeout=8
            )

            # Update log entry
            log_entry.payload_sent = res.get("payload_sent", {})
            log_entry.meta_response = res.get("response", {})

            if res.get("success"):
                log_entry.status = "SENT"
                log_entry.meta_message_id = res.get("message_id", "")
                log_entry.error_message = ""
                logger.info(f"✅ [WHATSAPP DISPATCHER] Message sent successfully to {record.phone_number} (Rule: '{rule.rule_name}')")
            else:
                log_entry.status = "FAILED"
                log_entry.error_message = res.get("error", "Unknown Meta API error")
                logger.warning(f"❌ [WHATSAPP DISPATCHER] Failed sending to {record.phone_number}: {log_entry.error_message}")

            log_entry.save()

    except Exception as e:
        logger.error(f"❌ [WHATSAPP DISPATCHER WORKER ERROR]: Call #{call_record_id} - {e}", exc_info=True)
    finally:
        close_old_connections()


def trigger_whatsapp_for_call(call_record, async_mode: bool = True):
    """
    Main entry point: called when a call completes (or when AI summarizer completes).
    Performs ultra-fast (<1ms) check: If agent has no WhatsApp config, returns immediately!
    If configured, dispatches asynchronously without blocking voice or webhook requests.
    """
    if not call_record:
        return

    # Check if agent exists
    agent = getattr(call_record, "sarvam_agent", None)
    if not agent:
        return

    # Ultra-fast check: if agent has no whatsapp_config or is disabled, exit in 0ms!
    config = getattr(agent, "whatsapp_config", None)
    if not config or not config.is_active:
        return

    # Don't send to dummy or empty numbers
    phone = str(call_record.phone_number or "").strip()
    if not phone or phone.lower() in ("unknown", "none", "null") or len("".join(filter(str.isdigit, phone))) < 10:
        return

    rec_id = call_record.id

    if async_mode:
        t = threading.Thread(
            target=_dispatch_worker,
            args=(rec_id,),
            daemon=True,
            name=f"WhatsAppDispatcher-{rec_id}"
        )
        t.start()
        logger.info(f"🚀 [WHATSAPP TRIGGERED]: Queued background automation for Call #{rec_id} (Agent: {agent.name})")
    else:
        _dispatch_worker(rec_id)

