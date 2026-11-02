from django.urls import path
from .views import meta_webhook_endpoint, test_send_whatsapp_api, in_call_whatsapp_trigger_webhook

urlpatterns = [
    # Meta WhatsApp Cloud API Callback (GET for verification, POST for message delivery receipts)
    path("webhook/", meta_webhook_endpoint, name="meta-whatsapp-webhook"),
    path("api/webhook/", meta_webhook_endpoint),

    # Live In-Call Webhook / Tool Trigger (Fires mid-call from Sarvam voice agent)
    path("in-call-trigger/", in_call_whatsapp_trigger_webhook, name="whatsapp-in-call-trigger-default"),
    path("in-call-trigger/<slug:agent_slug>/", in_call_whatsapp_trigger_webhook, name="whatsapp-in-call-trigger-slug"),
    path("api/in-call-trigger/", in_call_whatsapp_trigger_webhook),
    path("api/in-call-trigger/<slug:agent_slug>/", in_call_whatsapp_trigger_webhook),
    path("api/<slug:agent_slug>/in-call-trigger/", in_call_whatsapp_trigger_webhook),
    path("tool/send-whatsapp/", in_call_whatsapp_trigger_webhook),
    path("tool/send-whatsapp/<slug:agent_slug>/", in_call_whatsapp_trigger_webhook),
    path("api/tool/send-whatsapp/<slug:agent_slug>/", in_call_whatsapp_trigger_webhook),

    # Test send endpoint (Admins only)
    path("api/test-send/", test_send_whatsapp_api, name="whatsapp-test-send"),
    path("api/<slug:agent_slug>/test-send/", test_send_whatsapp_api, name="whatsapp-agent-test-send"),
]

