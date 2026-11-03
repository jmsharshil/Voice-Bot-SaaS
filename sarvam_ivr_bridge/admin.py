from django.contrib import admin
from django.utils.html import format_html
from sarvam_ivr_bridge.models import AgentIVRForwardingConfig, IVRForwardedCallLog
from sarvam_ivr_bridge.engine import correlate_ivr_log


@admin.register(AgentIVRForwardingConfig)
class AgentIVRForwardingConfigAdmin(admin.ModelAdmin):
    list_display = (
        "sarvam_agent",
        "is_active_badge",
        "ivr_provider_name",
        "forwarding_dids",
        "time_window_minutes",
        "match_by_duration",
        "auto_update_sarvam_record",
        "updated_at",
    )
    list_filter = ("is_active", "ivr_provider_name", "match_by_duration")
    search_fields = ("sarvam_agent__name", "sarvam_agent__slug", "forwarding_dids", "ivr_provider_name")
    autocomplete_fields = ("sarvam_agent",)

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green; font-weight: bold;">✔ Active</span>')
        return format_html('<span style="color: red; font-weight: bold;">✖ Disabled</span>')
    is_active_badge.short_description = "Status"


@admin.register(IVRForwardedCallLog)
class IVRForwardedCallLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "real_caller_number",
        "forwarded_did",
        "agent_name",
        "duration_seconds",
        "match_status_badge",
        "sarvam_record_link",
        "call_start_time",
        "created_at",
    )
    list_filter = ("match_status", "agent_config__ivr_provider_name", "disposition")
    search_fields = ("real_caller_number", "forwarded_did", "ivr_call_id")
    readonly_fields = ("created_at", "updated_at", "matched_at")
    actions = ["retry_correlation_matching"]

    def agent_name(self, obj):
        return obj.agent_config.sarvam_agent.name if obj.agent_config else "—"
    agent_name.short_description = "Sarvam Agent"

    def match_status_badge(self, obj):
        colors = {
            "MATCHED": "green",
            "PENDING": "orange",
            "UNMATCHED": "gray",
            "IGNORED": "red",
        }
        color = colors.get(obj.match_status, "black")
        return format_html(f'<span style="color: {color}; font-weight: bold;">{obj.match_status}</span>')
    match_status_badge.short_description = "Match Status"

    def sarvam_record_link(self, obj):
        if obj.sarvam_call_record:
            return format_html(
                f'<a href="/admin/conversations/sarvamcallrecord/{obj.sarvam_call_record.id}/change/">Call #{obj.sarvam_call_record.id}</a>'
            )
        return "—"
    sarvam_record_link.short_description = "Sarvam Record"

    def retry_correlation_matching(self, request, queryset):
        matched_count = 0
        for log in queryset:
            if correlate_ivr_log(log):
                matched_count += 1
        self.message_user(request, f"Processed {queryset.count()} logs: {matched_count} successfully matched to Sarvam calls.")
    retry_correlation_matching.short_description = "Retry Correlation Match for selected logs"

