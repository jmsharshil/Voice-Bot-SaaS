"""
WhatsApp Automation Views
=========================
1. meta_webhook_endpoint: Handles Meta Cloud API webhook verification (GET)
   and real-time message status updates (POST: DELIVERED, READ, FAILED).
2. test_send_whatsapp_api: One-click testing API to verify agent Meta credentials.
"""

import json
import logging
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import AgentWhatsAppConfig, WhatsAppTemplate, WhatsAppMessageLog
from .services.meta_client import MetaWhatsAppClient

logger = logging.getLogger(__name__)

# Default verification token for Meta webhook setup (can be overridden in settings or query)
META_VERIFY_TOKEN = "naavya_whatsapp_verify_token_2026"


@csrf_exempt
def meta_webhook_endpoint(request):
    """
    Official Meta WhatsApp Webhook Callback.
    - GET: Meta verification handshake (returns hub.challenge if hub.verify_token matches).
    - POST: Message status receipts (SENT -> DELIVERED -> READ -> FAILED).
    """
    # ── 1. GET: WEBHOOK VERIFICATION HANDSHAKE ──
    if request.method == "GET":
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if mode == "subscribe" and token == META_VERIFY_TOKEN:
            logger.info("✅ [META WEBHOOK VERIFIED]: Subscription handshake successful.")
            return HttpResponse(challenge, status=200)
        else:
            logger.warning(f"⚠️ [META WEBHOOK VERIFICATION FAILED]: Invalid token '{token}' or mode '{mode}'.")
            return HttpResponse("Verification token mismatch", status=403)

    # ── 2. POST: STATUS RECEIPTS & INCOMING EVENTS ──
    elif request.method == "POST":
        try:
            body_unicode = request.body.decode("utf-8")
            data = json.loads(body_unicode) if body_unicode else {}
        except Exception:
            data = {}

        try:
            entries = data.get("entry", [])
            for entry in entries:
                changes = entry.get("changes", [])
                for change in changes:
                    val = change.get("value", {})
                    statuses = val.get("statuses", [])

                    for st in statuses:
                        msg_id = st.get("id")
                        status_str = str(st.get("status") or "").upper().strip()

                        if msg_id:
                            # Update our audit log
                            log_obj = WhatsAppMessageLog.objects.filter(meta_message_id=msg_id).first()
                            if log_obj:
                                if status_str == "DELIVERED":
                                    log_obj.status = "DELIVERED"
                                elif status_str == "READ":
                                    log_obj.status = "READ"
                                elif status_str == "FAILED":
                                    log_obj.status = "FAILED"
                                    errors = st.get("errors", [])
                                    if errors:
                                        log_obj.error_message = json.dumps(errors)

                                log_obj.save(update_fields=["status", "error_message", "updated_at"])
                                logger.info(f"📊 [META STATUS UPDATE]: Message {msg_id} -> {status_str}")

        except Exception as e:
            logger.error(f"❌ [META WEBHOOK PARSE ERROR]: {e}", exc_info=True)

        return HttpResponse("EVENT_RECEIVED", status=200)

    return HttpResponse("Method not allowed", status=405)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def test_send_whatsapp_api(request, agent_slug=None):
    """
    Test endpoint for admins to send a test template to any phone number,
    verifying Meta credentials and template formatting.
    """
    user = request.user
    from conversations.models import SarvamAgent

    agent_id = request.data.get("agent_id")
    target_slug = agent_slug or request.data.get("agent_slug")
    phone = request.data.get("phone")
    template_name = request.data.get("template_name")
    language = request.data.get("language", "en")
    body_params = request.data.get("body_params", [])
    header_url = request.data.get("header_url")

    if not phone or not template_name:
        return Response({"error": "Fields 'phone' and 'template_name' are required."}, status=400)

    # Resolve agent
    agent = None
    if agent_id:
        agent = SarvamAgent.objects.filter(id=agent_id).first()
    elif target_slug:
        agent = SarvamAgent.objects.filter(slug=target_slug).first()

    if not agent:
        return Response({"error": f"Agent not found for slug '{target_slug}' or id '{agent_id}'."}, status=404)

    config = getattr(agent, "whatsapp_config", None)
    if not config:
        return Response({
            "error": f"Agent '{agent.name}' does not have WhatsApp configuration. Please add AgentWhatsAppConfig in admin."
        }, status=400)

    client = MetaWhatsAppClient(
        phone_number_id=config.phone_number_id,
        access_token=config.access_token,
        api_version=config.api_version
    )

    template_obj = config.templates.filter(template_name=template_name).first()
    header_type = template_obj.header_type if template_obj else ("DOCUMENT" if header_url else "NONE")

    res = client.send_template_message(
        to_phone=phone,
        template_name=template_name,
        language_code=language,
        body_parameters=body_params,
        header_type=header_type,
        header_media_url=header_url or (template_obj.header_media_url if template_obj else None),
        timeout=10
    )

    return Response(res, status=200 if res.get("success") else 400)

