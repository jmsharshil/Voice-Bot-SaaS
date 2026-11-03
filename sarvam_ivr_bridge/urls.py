from django.urls import path
from sarvam_ivr_bridge.views import ivr_webhook_receiver

urlpatterns = [
    # Global generic webhook: POST /api/sarvam-ivr/webhook/
    path("webhook/", ivr_webhook_receiver, name="sarvam-ivr-webhook-global"),
    # Agent-scoped webhook: POST /api/sarvam-ivr/<agent_slug>/webhook/
    path("<slug:agent_slug>/webhook/", ivr_webhook_receiver, name="sarvam-ivr-webhook-agent"),
]

