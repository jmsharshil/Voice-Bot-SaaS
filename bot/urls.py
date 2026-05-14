# from django.urls import path
# from .views import dashboard_data, dashboard_view, test_send_message,run_renewal_api, upload_file,whatsapp_webhook,get_conversations, get_messages, send_message_dashboard, upload_page_view, get_batches, get_batch_customers, get_upload_progress


# urlpatterns = [
#     path("test-send/", test_send_message),
#     path("run-renewal/", run_renewal_api),   # ✅ ADD THIS
#     path("webhook/", whatsapp_webhook),
#     path("dashboard/", dashboard_view),
#     path("dashboard/conversations/", get_conversations),
#     path("dashboard/messages/<int:customer_id>/", get_messages),
#     path("dashboard/data/", dashboard_data),
#     path("dashboard/send/", send_message_dashboard),
#     path("dashboard/batches/", get_batches),
#     path("dashboard/batches/<int:batch_id>/customers/", get_batch_customers),
#     path("upload/", upload_file),
#     path("upload/progress/", get_upload_progress),
#     path("upload-page/", upload_page_view),
# ]
















# ============================================================
#  bot/urls.py
# ============================================================

from bot.views import mark_answered
from django.urls import path
from .views import (
    # test / triggers
    test_send_message,
    run_renewal_api,
    run_new_insurance_api,
    run_all_campaigns_api,
    trigger_call,
    upload_call_file,
    upload_call_page,
    start_auto_campaign,
    auto_campaign_status,
    stop_auto_campaign,
    export_leads_excel,

    # webhook
    whatsapp_webhook,

    # upload
    upload_file,
    get_upload_progress,
    upload_page_view,

    # conversations
    get_conversations,
    get_messages,
    send_message_dashboard,

    # dashboard
    dashboard_view,
    dashboard_data,

    # batches
    get_batches,
    get_batch_customers,

    # # voice call
    # initiate_call,
)

urlpatterns = [

    # ── Test & manual triggers ──────────────────────────────
    path("test-send/",          test_send_message),
    path("run-renewal/",        run_renewal_api),
    path("run-new-insurance/",  run_new_insurance_api),   # NEW
    path("run-all-campaigns/",  run_all_campaigns_api),   # NEW

    # ── WhatsApp webhook ────────────────────────────────────
    path("webhook/",            whatsapp_webhook),  #wehbook endpoint which used in WAsender     /bot/wehbook/

    # ── File upload ─────────────────────────────────────────
    path("upload/",             upload_file),
    path("upload/progress/",    get_upload_progress),
    path("upload-page/",        upload_page_view),

    # ── Dashboard ───────────────────────────────────────────
    path("dashboard/",                                  dashboard_view),
    path("dashboard/data/",                             dashboard_data),
    path("dashboard/conversations/",                    get_conversations),
    path("dashboard/messages/<int:customer_id>/",       get_messages),
    path("dashboard/send/",                             send_message_dashboard),
    path("dashboard/batches/",                          get_batches),
    path("dashboard/batches/<int:batch_id>/customers/", get_batch_customers),
    # path("dashboard/call/",                             initiate_call),
    path("trigger-call/", trigger_call),
    path("mark-answered/", mark_answered),

    path("upload-call/", upload_call_file),
    path("upload-call-page/", upload_call_page),
    path("export/leads/", export_leads_excel),
    
    # Auto-dialer campaign
    path("auto-campaign/start/", start_auto_campaign),
    path("auto-campaign/status/", auto_campaign_status),
    path("auto-campaign/stop/", stop_auto_campaign),
]
