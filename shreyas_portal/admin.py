from django.contrib import admin
from .models import ShreyasDepartment, ShreyasUserProfile, ShreyasCallLead


@admin.register(ShreyasDepartment)
class ShreyasDepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "badge_color", "is_active", "order", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "keywords", "description")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(ShreyasUserProfile)
class ShreyasUserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "is_master_admin", "get_departments", "created_at")
    list_filter = ("is_master_admin",)
    search_fields = ("user__username", "user__email", "phone_number")
    filter_horizontal = ("assigned_departments",)

    def get_departments(self, obj):
        if obj.is_master_admin:
            return "ALL (Master Admin)"
        return ", ".join([d.name for d in obj.assigned_departments.all()]) or "None"
    get_departments.short_description = "Assigned Departments"


@admin.register(ShreyasCallLead)
class ShreyasCallLeadAdmin(admin.ModelAdmin):
    list_display = ("caller_name", "phone_number", "department", "lead_sentiment", "pipeline_stage", "duration_seconds", "status", "created_at")
    list_filter = ("department", "lead_sentiment", "pipeline_stage", "status")
    search_fields = ("caller_name", "phone_number", "transcript", "summary", "detected_intent")
    readonly_fields = ("created_at", "updated_at")
