from .views import (
    ChatAPIView, DemoChatAPIView, demo_page,
    get_conversations, get_conversation_messages, get_campaign_lead_conversation,
    call_analytics_page, call_analytics_data, call_analytics_session,
    call_analytics_per_bot,
    lead_analysis_page, lead_analysis_data, lead_analysis_detail,
    telecom_cdr_webhook, telecom_cdr_list,
    minutes_usage_api,
)
from django.urls import path

urlpatterns = [
    path("agents/<uuid:agent_id>/chat/", ChatAPIView.as_view()),
    path("demo/chat/", DemoChatAPIView.as_view()),
    path("", demo_page, name="demo-page"),
    path("conversations/", get_conversations),
    path("conversations/campaign-lead/", get_campaign_lead_conversation),
    path("conversations/<str:session_id>/", get_conversation_messages),

    # Call Analytics Dashboard
    path("call-analytics/", call_analytics_page, name="call-analytics"),
    path("call-analytics/data/", call_analytics_data),
    path("call-analytics/per-bot/", call_analytics_per_bot),
    path("call-analytics/session/<str:session_id>/", call_analytics_session),

    # Lead Analysis Dashboard + API
    path("lead-analysis/", lead_analysis_page, name="lead-analysis"),
    path("lead-analysis/data/", lead_analysis_data),
    path("lead-analysis/detail/<str:session_id>/", lead_analysis_detail),

    # Telecom CDR Webhook
    path("webhook/cdr/", telecom_cdr_webhook),
    path("cdr/list/", telecom_cdr_list),

    # Minutes Usage
    path("minutes-usage/", minutes_usage_api),
]