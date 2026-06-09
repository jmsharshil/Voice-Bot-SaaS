# # from django.contrib import admin

# # # Register your models here.
# # from django.contrib import admin
# # from .models import Customer

# # @admin.register(Customer)
# # class CustomerAdmin(admin.ModelAdmin):
# #     list_display = ("name", "phone", "policy_type", "expiry_date", "reminder_sent")
# #     search_fields = ("name", "phone")
# #     list_filter = ("policy_type", "reminder_sent")

# from django.contrib import admin
# from .models import Customer, ChatMessage, UploadedFile, UploadBatch


# # ✅ INLINE CHAT (THIS IS KEY)
# class ChatMessageInline(admin.TabularInline):
#     model = ChatMessage
#     extra = 0
#     ordering = ['timestamp']
#     readonly_fields = ("message", "sender", "timestamp")
#     can_delete = False


# # ✅ CUSTOMER ADMIN (MAIN VIEW)
# @admin.register(Customer)
# class CustomerAdmin(admin.ModelAdmin):
#     list_display = ("name", "phone", "policy_type", "expiry_date")
#     inlines = [ChatMessageInline]   # 🔥 THIS GROUPS MESSAGES

# admin.site.register(UploadedFile)
# admin.site.register(UploadBatch)















# ============================================================
#  bot/admin.py
# ============================================================

from django.contrib import admin
from bot.models import Customer, ChatMessage, UploadedFile, UploadBatch, CampaignStatus, Campaign


# ============================================================
#  UPLOAD BATCH
# ============================================================

@admin.register(UploadBatch)
class UploadBatchAdmin(admin.ModelAdmin):

    list_display  = ("id", "name", "customer_count", "uploaded_at")
    list_filter   = ("uploaded_at",)
    search_fields = ("name",)
    ordering      = ("-uploaded_at",)
    readonly_fields = ("uploaded_at",)


# ============================================================
#  CUSTOMER
# ============================================================

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):

    list_display = (
        "id", "name", "phone",
        "customer_type", "vehicle_type", "vehicle_number",
        "expiry_date", "conversation_state",
        "reminder_sent", "batch",
    )

    list_filter = (
        "customer_type",
        "vehicle_type",
        "conversation_state",
        "reminder_sent",
        "batch",
    )

    search_fields = ("name", "phone", "vehicle_number")

    ordering = ("-id",)

    readonly_fields = (
        "selected_coverage",
        "selected_addons",
        "quoted_premium",
    )

    fieldsets = (
        ("Basic Info", {
            "fields": ("name", "phone", "batch")
        }),
        ("Customer & Vehicle", {
            "fields": (
                "customer_type",
                "vehicle_type",
                "vehicle_number",
                "policy_type",
                "expiry_date",
            )
        }),
        ("Conversation", {
            "fields": (
                "conversation_state",
                "reminder_sent",
                "selected_coverage",
                "selected_addons",
                "quoted_premium",
            )
        }),
    )

    # ── Bulk actions ──────────────────────────────────────────
    actions = ["mark_reminder_sent", "mark_reminder_unsent", "reset_conversation"]

    @admin.action(description="✅ Mark selected as reminder sent")
    def mark_reminder_sent(self, request, queryset):
        updated = queryset.update(reminder_sent=True)
        self.message_user(request, f"{updated} customer(s) marked as reminder sent.")

    @admin.action(description="🔄 Mark selected as reminder NOT sent")
    def mark_reminder_unsent(self, request, queryset):
        updated = queryset.update(reminder_sent=False)
        self.message_user(request, f"{updated} customer(s) marked as reminder not sent.")

    @admin.action(description="♻️ Reset conversation to initial")
    def reset_conversation(self, request, queryset):
        updated = queryset.update(
            conversation_state="initial",
            selected_coverage=None,
            selected_addons=None,
            quoted_premium=None,
        )
        self.message_user(request, f"{updated} customer(s) conversation reset to initial.")


# ============================================================
#  CHAT MESSAGE
# ============================================================

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):

    list_display  = ("id", "customer", "sender", "short_message", "timestamp")
    list_filter   = ("sender", "timestamp")
    search_fields = ("customer__name", "customer__phone", "message")
    ordering      = ("-timestamp",)
    readonly_fields = ("timestamp",)

    def short_message(self, obj):
        return obj.message[:60] + "..." if len(obj.message) > 60 else obj.message
    short_message.short_description = "Message"


# ============================================================
#  UPLOADED FILE
# ============================================================

@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):

    list_display  = ("id", "file", "file_type", "uploaded_at")
    list_filter   = ("file_type", "uploaded_at")
    ordering      = ("-uploaded_at",)
    readonly_fields = ("uploaded_at",)


# ============================================================
#  CAMPAIGN STATUS
# ============================================================

@admin.register(CampaignStatus)
class CampaignStatusAdmin(admin.ModelAdmin):
    list_display    = ("id", "started_at", "total_count", "completed_count", "is_active")
    list_filter     = ("is_active", "started_at")
    readonly_fields = ("started_at",)
    ordering        = ("-started_at",)


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display    = ("id", "name", "created_by", "agent", "total_count", "completed_count", "answered_count", "is_active", "started_at", "ended_at")
    list_filter     = ("is_active", "started_at", "created_by", "agent")
    search_fields   = ("name", "created_by__username", "agent__name")
    readonly_fields = ("started_at", "ended_at")
    ordering        = ("-started_at",)
