from django.contrib import admin
from .models import Customer, ChatMessage, UploadBatch, UploadedFile


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "customer_type", "vehicle_type", "source", "conversation_state")
    search_fields = ("name", "phone", "vehicle_number")
    list_filter = ("customer_type", "vehicle_type", "source", "conversation_state")
    ordering = ("-id",)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("customer", "sender", "message", "timestamp")
    search_fields = ("message", "customer__phone")
    list_filter = ("sender",)
    ordering = ("-timestamp",)


@admin.register(UploadBatch)
class UploadBatchAdmin(admin.ModelAdmin):
    list_display = ("name", "customer_count", "uploaded_at")


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ("file", "uploaded_at")