from django.urls import path
from .views import home, dashboard_view, dashboard_data, get_messages, send_message_dashboard, upload_view, whatsapp_webhook

urlpatterns = [
    path('', home),

    path('dashboard/', dashboard_view),
    path('upload/', upload_view), 

    path('dashboard/data/', dashboard_data),
    path('dashboard/messages/<int:customer_id>/', get_messages),
    path('dashboard/send/', send_message_dashboard),
    path('webhook/', whatsapp_webhook),
]