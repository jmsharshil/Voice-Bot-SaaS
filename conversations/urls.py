from .views import (
    ChatAPIView, DemoChatAPIView, demo_page,
    get_conversations, get_conversation_messages, get_campaign_lead_conversation,
    call_analytics_page, call_analytics_data, call_analytics_session,
    call_analytics_per_bot,
    lead_analysis_page, lead_analysis_data, lead_analysis_detail, update_lead_level,
    telecom_cdr_webhook, telecom_cdr_list, icemake_webhook, kylas_webhook, sarvam_cdr_webhook,
    minutes_usage_api,
    icemake_dashboard_page, icemake_dashboard_data,
    proxy_audio,
    sarvam_leads_page, sarvam_leads_data, sarvam_transcript_detail, sarvam_trigger_call_api, sarvam_sync_from_api,
    public_trigger_sarvam_call_api, public_list_sarvam_agents_api,
    sarvam_upload_campaign_api, sarvam_sample_template_api,
    sarvam_user_agents_api, sarvam_campaigns_list_api, sarvam_campaign_detail_api,
    sarvam_campaign_export_full_api, sarvam_campaign_export_missed_api, sarvam_campaign_cancel_api,
    sarvam_agent_minutes_status_api, sarvam_adjust_agent_minutes_api, sarvam_toggle_agent_active_api,
)
from django.urls import path, re_path

urlpatterns = [
    # ── PUBLIC REST API FOR REACT FRONTEND INTEGRATION ────────────────
    path("v1/trigger-call/", public_trigger_sarvam_call_api, name="api-v1-trigger-call"),
    path("v1/agents/", public_list_sarvam_agents_api, name="api-v1-list-agents"),
    path("api/v1/trigger-call/", public_trigger_sarvam_call_api),
    path("api/v1/agents/", public_list_sarvam_agents_api),
    path("sarvam/public/trigger-call/", public_trigger_sarvam_call_api, name="sarvam-public-trigger-call"),
    path("sarvam/public/agents/", public_list_sarvam_agents_api, name="sarvam-public-agents"),
    path("sarvam/<slug:agent_slug>/public-call/", public_trigger_sarvam_call_api, name="sarvam-agent-public-call"),
    path("sarvam/agent/<int:agent_id>/public-call/", public_trigger_sarvam_call_api, name="sarvam-agent-id-public-call"),
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
    path("lead-analysis/update-level/<str:session_id>/", update_lead_level),

    # Sarvam AI Agent Leads Dashboard — Default (backward-compatible, uses first active SarvamAgent)
    path("sarvam/leads/", sarvam_leads_page, name="sarvam-leads"),
    path("sarvam/leads/data/", sarvam_leads_data),
    path("sarvam/leads/call/", sarvam_trigger_call_api),
    path("sarvam/leads/sync/", sarvam_sync_from_api),
    path("sarvam/leads/upload-campaign/", sarvam_upload_campaign_api, name="sarvam-upload-campaign"),
    path("sarvam/leads/sample-template/", sarvam_sample_template_api, name="sarvam-sample-template"),
    path("sarvam/leads/transcript/<path:interaction_id>/", sarvam_transcript_detail),

    # Sarvam User Agents & Multi-Agent Switcher API
    path("sarvam/agents/", sarvam_user_agents_api, name="sarvam-user-agents"),

    # Sarvam 3-Stage Campaigns APIs & Excel Downloads
    path("sarvam/campaigns/list/", sarvam_campaigns_list_api, name="sarvam-campaigns-list"),
    path("sarvam/<slug:agent_slug>/campaigns/list/", sarvam_campaigns_list_api, name="sarvam-agent-campaigns-list"),
    path("sarvam/campaigns/<int:campaign_id>/detail/", sarvam_campaign_detail_api, name="sarvam-campaign-detail"),
    path("sarvam/campaigns/<int:campaign_id>/export-full/", sarvam_campaign_export_full_api, name="sarvam-campaign-export-full"),
    path("sarvam/campaigns/<int:campaign_id>/export-missed/", sarvam_campaign_export_missed_api, name="sarvam-campaign-export-missed"),
    path("sarvam/campaigns/<int:campaign_id>/cancel/", sarvam_campaign_cancel_api, name="sarvam-campaign-cancel"),

    # Sarvam AI Agent Leads Dashboard — Per-Agent (each slug gets its own dashboard)
    path("sarvam/<slug:agent_slug>/leads/", sarvam_leads_page, name="sarvam-agent-leads"),
    path("sarvam/<slug:agent_slug>/leads/data/", sarvam_leads_data, name="sarvam-agent-leads-data"),
    path("sarvam/<slug:agent_slug>/leads/call/", sarvam_trigger_call_api, name="sarvam-agent-trigger-call"),
    path("sarvam/<slug:agent_slug>/leads/sync/", sarvam_sync_from_api, name="sarvam-agent-sync"),
    path("sarvam/<slug:agent_slug>/leads/upload-campaign/", sarvam_upload_campaign_api, name="sarvam-agent-upload-campaign"),
    path("sarvam/<slug:agent_slug>/leads/transcript/<path:interaction_id>/", sarvam_transcript_detail, name="sarvam-agent-transcript"),


    # Ice Make Support Dashboard
    path("icemake-dashboard/", icemake_dashboard_page, name="icemake-dashboard"),
    path("icemake-dashboard/data/", icemake_dashboard_data, name="icemake-dashboard-data"),
    path("proxy-audio/", proxy_audio, name="proxy-audio"),

    # Telecom CDR, Ice Make, Kylas & Sarvam Webhooks
    path("webhook/cdr/", telecom_cdr_webhook),
    path("webhook/icemake/", icemake_webhook),
    path("webhook/kylas/", kylas_webhook),
    path("webhook/sarvam/cdr/", sarvam_cdr_webhook),
    re_path(r"^webhook/sarvam/cdr/?.*$", sarvam_cdr_webhook),
    path("cdr/list/", telecom_cdr_list),

    # Minutes Usage & Quota
    path("minutes-usage/", minutes_usage_api),
    path("sarvam/minutes/", sarvam_agent_minutes_status_api, name="sarvam-minutes-status"),
    path("sarvam/<slug:agent_slug>/minutes/", sarvam_agent_minutes_status_api, name="sarvam-agent-minutes-status"),
    path("sarvam/adjust-minutes/", sarvam_adjust_agent_minutes_api, name="sarvam-adjust-minutes"),
    path("sarvam/<slug:agent_slug>/adjust-minutes/", sarvam_adjust_agent_minutes_api, name="sarvam-agent-adjust-minutes"),

    # Sarvam Agent Toggle Active Status
    path("sarvam/agents/<int:agent_id>/toggle/", sarvam_toggle_agent_active_api, name="sarvam-agent-toggle-id"),
    path("sarvam/<slug:agent_slug>/toggle/", sarvam_toggle_agent_active_api, name="sarvam-agent-toggle-slug"),
]