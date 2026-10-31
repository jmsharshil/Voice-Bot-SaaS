from django.urls import path
from .views import meta_webhook_endpoint, test_send_whatsapp_api

urlpatterns = [
    # Meta WhatsApp Cloud API Callback (GET for verification, POST for message delivery receipts)
    path("webhook/", meta_webhook_endpoint, name="meta-whatsapp-webhook"),
    path("api/webhook/", meta_webhook_endpoint),

    # Test send endpoint (Admins only)
    path("api/test-send/", test_send_whatsapp_api, name="whatsapp-test-send"),
    path("api/<slug:agent_slug>/test-send/", test_send_whatsapp_api, name="whatsapp-agent-test-send"),
]

