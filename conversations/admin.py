from django.contrib import admin
from django.utils.html import format_html
from .models import (
    ConversationLog, ConversationSession, Conversation, Message,
    LeadAnalysis, CallDetailRecord, SarvamCallRecord, SarvamAgent,
    SarvamCampaign, SarvamCampaignLead, SarvamAgentMinuteAdjustment
)


@admin.register(SarvamAgentMinuteAdjustment)
class SarvamAgentMinuteAdjustmentAdmin(admin.ModelAdmin):
    list_display = ("agent", "action", "minutes_amount", "previous_allocated_minutes", "new_allocated_minutes", "adjusted_by", "note", "created_at")
    list_filter = ("action", "agent", "created_at")
    search_fields = ("agent__name", "note")
    readonly_fields = ("previous_allocated_minutes", "new_allocated_minutes", "adjusted_by", "created_at")

    fieldsets = (
        ("Minute Adjustment Details", {
            "fields": ("agent", "action", "minutes_amount", "note"),
            "description": "Select an agent and action (Add, Subtract, or Set). Saving will instantly update the agent's live call minutes quota."
        }),
        ("Audit Metadata (Auto-calculated)", {
            "fields": ("previous_allocated_minutes", "new_allocated_minutes", "adjusted_by", "created_at"),
            "classes": ("collapse",),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.adjusted_by = request.user if request.user.is_authenticated else None
            old_allocated = obj.agent.allocated_minutes
            obj.previous_allocated_minutes = old_allocated

            if obj.action == "ADD":
                obj.agent.allocated_minutes += float(obj.minutes_amount)
            elif obj.action == "SUBTRACT":
                obj.agent.allocated_minutes = max(0.0, float(obj.agent.allocated_minutes) - float(obj.minutes_amount))
            elif obj.action == "SET":
                obj.agent.allocated_minutes = max(0.0, float(obj.minutes_amount))

            obj.new_allocated_minutes = obj.agent.allocated_minutes
            obj.agent.save(update_fields=["allocated_minutes"])

            if not obj.note:
                obj.note = f"Manual adjustment via Admin by {request.user.username if request.user else 'Admin'}: {obj.action} {obj.minutes_amount} mins"

        super().save_model(request, obj, form, change)


@admin.register(SarvamAgent)
class SarvamAgentAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "allocated_minutes_display", "used_minutes_display", "remaining_minutes_display", "status_badge", "agent_phone", "is_active")
    search_fields = ("name", "slug", "app_id", "agent_phone")
    list_filter = ("is_active",)
    readonly_fields = ("used_minutes_display", "remaining_minutes_display", "created_at", "updated_at")
    actions = ["add_500_minutes", "add_1000_minutes", "add_5000_minutes", "deduct_500_minutes", "reset_5000_minutes"]

    def save_model(self, request, obj, form, change):
        if change and "allocated_minutes" in form.changed_data:
            old_allocated = form.initial.get("allocated_minutes", obj.allocated_minutes)
            new_allocated = obj.allocated_minutes
            diff = new_allocated - old_allocated
            action = "ADD" if diff > 0 else ("SUBTRACT" if diff < 0 else "SET")
            SarvamAgentMinuteAdjustment.objects.create(
                agent=obj,
                action=action,
                minutes_amount=abs(diff),
                previous_allocated_minutes=old_allocated,
                new_allocated_minutes=new_allocated,
                adjusted_by=request.user if request.user.is_authenticated else None,
                note=f"Direct edit on SarvamAgent page by {request.user.username if request.user else 'Admin'}: {old_allocated}m -> {new_allocated}m"
            )
        super().save_model(request, obj, form, change)

    fieldsets = (
        ("Identity", {
            "fields": ("name", "slug", "description", "is_active")
        }),
        ("Call Minutes & Quota (SuperAdmin)", {
            "fields": ("allocated_minutes", "extra_used_seconds", "used_minutes_display", "remaining_minutes_display"),
            "description": "Exclusively configured by SuperAdmin. Controls outbound call & campaign limits."
        }),
        ("Sarvam Platform Credentials", {
            "fields": ("org_id", "workspace_id", "app_id", "api_key", "connection_id", "agent_phone", "webhook_domain"),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )

    def allocated_minutes_display(self, obj):
        return f"{obj.allocated_minutes:,.1f} mins"
    allocated_minutes_display.short_description = "Allocated"

    def used_minutes_display(self, obj):
        return f"{obj.total_used_minutes:,.2f} mins ({obj.total_used_seconds:,.0f}s)"
    used_minutes_display.short_description = "Used (30s Pulse)"

    def remaining_minutes_display(self, obj):
        rem = obj.remaining_minutes
        if rem <= 0:
            return format_html('<span style="color:#dc2626; font-weight:700;">0.0 mins (Exhausted)</span>')
        return format_html('<span style="color:#16a34a; font-weight:700;">{} mins</span>', f"{rem:,.2f}")
    remaining_minutes_display.short_description = "Remaining"

    def status_badge(self, obj):
        if obj.is_minutes_exhausted:
            return format_html('<span style="background:#fee2e2; color:#b91c1c; padding:3px 8px; border-radius:12px; font-weight:600; font-size:11px;">🔴 Limit Over</span>')
        pct = obj.usage_percentage
        return format_html('<span style="background:#dcfce7; color:#15803d; padding:3px 8px; border-radius:12px; font-weight:600; font-size:11px;">🟢 Active ({}% used)</span>', f"{pct:.1f}")
    status_badge.short_description = "Balance Status"

    # SuperAdmin Bulk Actions
    def add_500_minutes(self, request, queryset):
        for agent in queryset:
            old = agent.allocated_minutes
            agent.allocated_minutes += 500.0
            agent.save(update_fields=["allocated_minutes"])
            SarvamAgentMinuteAdjustment.objects.create(
                agent=agent, action="ADD", minutes_amount=500.0,
                previous_allocated_minutes=old, new_allocated_minutes=agent.allocated_minutes,
                adjusted_by=request.user, note="Bulk Action: Added 500 minutes via Django Admin"
            )
        self.message_user(request, "Added 500 minutes to selected agent(s).")
    add_500_minutes.short_description = "⚡ Add 500 Minutes to selected agents"

    def add_1000_minutes(self, request, queryset):
        for agent in queryset:
            old = agent.allocated_minutes
            agent.allocated_minutes += 1000.0
            agent.save(update_fields=["allocated_minutes"])
            SarvamAgentMinuteAdjustment.objects.create(
                agent=agent, action="ADD", minutes_amount=1000.0,
                previous_allocated_minutes=old, new_allocated_minutes=agent.allocated_minutes,
                adjusted_by=request.user, note="Bulk Action: Added 1,000 minutes via Django Admin"
            )
        self.message_user(request, "Added 1,000 minutes to selected agent(s).")
    add_1000_minutes.short_description = "⚡ Add 1,000 Minutes to selected agents"

    def add_5000_minutes(self, request, queryset):
        for agent in queryset:
            old = agent.allocated_minutes
            agent.allocated_minutes += 5000.0
            agent.save(update_fields=["allocated_minutes"])
            SarvamAgentMinuteAdjustment.objects.create(
                agent=agent, action="ADD", minutes_amount=5000.0,
                previous_allocated_minutes=old, new_allocated_minutes=agent.allocated_minutes,
                adjusted_by=request.user, note="Bulk Action: Added 5,000 minutes via Django Admin"
            )
        self.message_user(request, "Added 5,000 minutes to selected agent(s).")
    add_5000_minutes.short_description = "⚡ Add 5,000 Minutes to selected agents"

    def deduct_500_minutes(self, request, queryset):
        for agent in queryset:
            old = agent.allocated_minutes
            agent.allocated_minutes = max(0.0, agent.allocated_minutes - 500.0)
            agent.save(update_fields=["allocated_minutes"])
            SarvamAgentMinuteAdjustment.objects.create(
                agent=agent, action="SUBTRACT", minutes_amount=500.0,
                previous_allocated_minutes=old, new_allocated_minutes=agent.allocated_minutes,
                adjusted_by=request.user, note="Bulk Action: Deducted 500 minutes via Django Admin"
            )
        self.message_user(request, "Deducted 500 minutes from selected agent(s).")
    deduct_500_minutes.short_description = "🔻 Subtract 500 Minutes from selected agents"

    def reset_5000_minutes(self, request, queryset):
        for agent in queryset:
            old = agent.allocated_minutes
            agent.allocated_minutes = 5000.0
            agent.save(update_fields=["allocated_minutes"])
            SarvamAgentMinuteAdjustment.objects.create(
                agent=agent, action="SET", minutes_amount=5000.0,
                previous_allocated_minutes=old, new_allocated_minutes=5000.0,
                adjusted_by=request.user, note="Bulk Action: Reset quota to 5,000 minutes via Django Admin"
            )
        self.message_user(request, "Reset quota to 5,000 minutes for selected agent(s).")
    reset_5000_minutes.short_description = "🔄 Reset Quota to 5,000 Minutes"


@admin.register(SarvamCallRecord)
class SarvamCallRecordAdmin(admin.ModelAdmin):
    list_display = (
        "candidate_name", "phone_number", "sarvam_agent", "campaign", "campaign_stage", "status",
        "duration_seconds", "billed_seconds", "call_type", "created_at",
    )
    list_filter = ("status", "call_type", "language", "sarvam_agent", "campaign_stage")
    search_fields = ("candidate_name", "phone_number", "attempt_id", "interaction_id")
    readonly_fields = ("billed_seconds", "created_at", "updated_at")
    ordering = ("-created_at",)



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