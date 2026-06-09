from django.contrib import admin
from .models import ConversationLog, ConversationSession, Conversation, Message, LeadAnalysis, CallDetailRecord


@admin.register(ConversationLog)
class ConversationLogAdmin(admin.ModelAdmin):
    list_display = ("agent", "user_message", "created_at")
    search_fields = ("agent__name", "user_message")


@admin.register(ConversationSession)
class ConversationSessionAdmin(admin.ModelAdmin):
    list_display = (
        "agent",
        "session_id",
        "current_intent",
        "stage",
        "created_at",
        "updated_at",
    )
    search_fields = ("session_id", "agent__name")
    list_filter = ("agent", "current_intent", "stage")
    readonly_fields = ("created_at", "updated_at")

from django.utils.html import format_html
from django.urls import reverse

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "user_number", "session_id", "campaign_link", "agent", "started_at", "ended_at")
    search_fields = ("user_number", "session_id", "stream_sid", "campaign_id")
    list_filter = ("agent", "started_at")
    readonly_fields = ("started_at",)

    def campaign_link(self, obj):
        if obj.campaign_id:
            try:
                url = reverse('admin:bot_campaign_change', args=[obj.campaign_id])
                return format_html('<a href="{}">Campaign #{}</a>', url, obj.campaign_id)
            except:
                return f"Campaign #{obj.campaign_id}"
        return "—"
    campaign_link.short_description = "Campaign"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "role", "text_snippet", "created_at")
    list_filter = ("role", "created_at")
    search_fields = ("conversation__user_number", "text")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

    def text_snippet(self, obj):
        return obj.text[:60] + "..." if len(obj.text) > 60 else obj.text
    text_snippet.short_description = "Message Text"


@admin.register(LeadAnalysis)
class LeadAnalysisAdmin(admin.ModelAdmin):
    list_display = (
        "lead_level",
        "user_name",
        "user_email",
        "user_phone",
        "interest_topic",
        "agent",
        "analyzed_at",
    )
    list_filter = ("lead_level", "agent")
    search_fields = ("user_name", "user_email", "user_phone", "interest_topic", "summary")
    readonly_fields = ("conversation", "agent", "raw_analysis", "analyzed_at")
    ordering = ("-analyzed_at",)


@admin.register(CallDetailRecord)
class CallDetailRecordAdmin(admin.ModelAdmin):
    list_display = (
        "phone_number",
        "did",
        "disposition",
        "duration",
        "call_type",
        "matched",
        "calldate",
        "received_at",
    )
    list_filter = ("disposition", "call_type", "matched", "did")
    search_fields = ("phone_number", "uniqueid", "recording_file_name")
    readonly_fields = ("received_at",)
    ordering = ("-received_at",)