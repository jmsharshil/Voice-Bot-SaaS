from django.contrib import admin
from .models import IcemakeTicket

@admin.register(IcemakeTicket)
class IcemakeTicketAdmin(admin.ModelAdmin):
    list_display = ("ticket_number", "customer_name", "registered_mobile", "issue_type", "city_state", "google_sheet_synced", "created_at")
    search_fields = ("ticket_number", "customer_name", "registered_mobile", "city_state", "issue_description")
    list_filter = ("issue_type", "google_sheet_synced", "created_at")
