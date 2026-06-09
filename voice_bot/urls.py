"""
URL configuration for voice_bot project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# from django.contrib import admin
# from django.urls import path, include
# from django.views.generic import RedirectView
# from conversations.views import demo_page
# from conversations.views import call_analytics_page, lead_analysis_page, lead_analysis_data, lead_analysis_detail
# from chat_channels.whatsapp.webhook import whatsapp_webhook

# urlpatterns = [
#     path("admin/", admin.site.urls),
#     path("", RedirectView.as_view(url="/bot/dashboard/", permanent=False), name="home"),
#     path("voicebot/", demo_page, name="voicebot"),
#     path("navya-analytics/", call_analytics_page, name="navya-analytics"),
#     path("navya-analytics/lead-analysis/", lead_analysis_page, name="lead-analysis"),
#     path("navya-analytics/lead-analysis/data/", lead_analysis_data, name="lead-analysis-data"),
#     path("navya-analytics/lead-analysis/detail/<str:session_id>/", lead_analysis_detail, name="lead-analysis-detail"),
#     path("api/accounts/", include("accounts.urls")),
#     path("api/agents/", include("agents.urls")),
#     path("api/", include("conversations.urls")),
#     path("api/knowledge/", include("knowledge.urls")),
#     path("webhook/whatsapp/", whatsapp_webhook),
#     path('', include('assistant.urls')),
#     path('bot/', include('bot.urls')),
# ]




from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from conversations.views import demo_page
from conversations.views import call_analytics_page, lead_analysis_page, lead_analysis_data, lead_analysis_detail
# from chat_channels.whatsapp.webhook import whatsapp_webhook

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(url="/accounts/login/", permanent=False), name="home"),
    path("voicebot/", demo_page, name="voicebot"),
    path("analytics/", call_analytics_page, name="navya-analytics"),
    path("dashboard/", lead_analysis_page, name="lead-analysis"),
    path("navya-analytics/lead-analysis/data/", lead_analysis_data, name="lead-analysis-data"),
    path("navya-analytics/lead-analysis/detail/<str:session_id>/", lead_analysis_detail, name="lead-analysis-detail"),
    path("accounts/", include("accounts.urls")),
    path("api/accounts/", include("accounts.urls")),
    path("api/agents/", include("agents.urls")),
    path("api/", include("conversations.urls")),
    path("api/knowledge/", include("knowledge.urls")),
    # path("webhook/whatsapp/", whatsapp_webhook),
    path('', include('assistant.urls')),
    path('bot/', include('bot.urls')),
]