from django.urls import path
from .views import (
    shreyas_login_view,
    shreyas_logout_view,
    shreyas_master_dashboard_view,
    shreyas_subuser_dashboard_view,
    api_get_leads,
    api_update_lead,
    api_manage_department,
    api_manage_subuser,
    api_create_test_lead,
    api_trigger_outbound_call,
    shreyas_cdr_webhook,
)

urlpatterns = [
    path("", shreyas_master_dashboard_view, name="shreyas-master-dashboard"),
    path("login/", shreyas_login_view, name="shreyas-login"),
    path("logout/", shreyas_logout_view, name="shreyas-logout"),
    path("department/", shreyas_subuser_dashboard_view, name="shreyas-subuser-dashboard"),
    
    # JSON APIs
    path("api/leads/", api_get_leads, name="shreyas-api-leads"),
    path("api/leads/<int:lead_id>/update/", api_update_lead, name="shreyas-api-update-lead"),
    path("api/department/", api_manage_department, name="shreyas-api-manage-dept"),
    path("api/subuser/", api_manage_subuser, name="shreyas-api-manage-subuser"),
    path("api/test-lead/", api_create_test_lead, name="shreyas-api-test-lead"),
    path("api/trigger-call/", api_trigger_outbound_call, name="shreyas-api-trigger-call"),
    path("webhook/cdr/", shreyas_cdr_webhook, name="shreyas-cdr-webhook"),
]
