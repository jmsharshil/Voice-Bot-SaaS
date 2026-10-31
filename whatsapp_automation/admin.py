from django.contrib import admin
from django.utils.html import format_html
from .models import AgentWhatsAppConfig, WhatsAppTemplate, WhatsAppRule, WhatsAppMessageLog


class WhatsAppTemplateInline(admin.TabularInline):
    model = WhatsAppTemplate
    extra = 0
    fields = ('template_name', 'language_code', 'category', 'header_type', 'is_active')
    show_change_link = True


class WhatsAppRuleInline(admin.TabularInline):
    model = WhatsAppRule
    extra = 0
    fields = ('rule_name', 'template', 'trigger_statuses', 'min_duration_seconds', 'is_active')
    show_change_link = True


@admin.register(AgentWhatsAppConfig)
class AgentWhatsAppConfigAdmin(admin.ModelAdmin):
    list_display = ('agent', 'phone_display_number', 'phone_number_id', 'is_active_badge', 'template_count', 'rule_count', 'updated_at')
    list_filter = ('is_active', 'api_version')
    search_fields = ('agent__name', 'phone_number_id', 'phone_display_number', 'waba_id')
    inlines = [WhatsAppTemplateInline, WhatsAppRuleInline]

    fieldsets = (
        ("Voice Agent Association", {
            "fields": ("agent", "is_active"),
            "description": "Select the Voice Agent that owns these credentials. If deactivated, no WhatsApp messages will ever be sent for this agent."
        }),
        ("Meta WhatsApp Cloud API Credentials", {
            "fields": ("phone_number_id", "waba_id", "access_token", "phone_display_number", "api_version"),
            "description": "Credentials from your Meta for Developers App -> WhatsApp -> API Setup."
        }),
    )

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green; font-weight: bold;">● Active</span>')
        return format_html('<span style="color: red; font-weight: bold;">○ Inactive</span>')
    is_active_badge.short_description = "Status"

    def template_count(self, obj):
        return obj.templates.count()
    template_count.short_description = "Templates"

    def rule_count(self, obj):
        return obj.rules.count()
    rule_count.short_description = "Rules"


@admin.register(WhatsAppTemplate)
class WhatsAppTemplateAdmin(admin.ModelAdmin):
    list_display = ('template_name', 'agent_name', 'language_code', 'category', 'header_type', 'is_active', 'updated_at')
    list_filter = ('category', 'header_type', 'is_active', 'language_code', 'agent_config__agent')
    search_fields = ('template_name', 'agent_config__agent__name', 'description')

    fieldsets = (
        ("Agent Configuration", {
            "fields": ("agent_config", "is_active"),
        }),
        ("Meta Template Details", {
            "fields": ("template_name", "language_code", "category", "description"),
            "description": "Must match the approved template name in Meta Business Manager exactly."
        }),
        ("Header Attachment (Optional)", {
            "fields": ("header_type", "header_media_url", "header_filename"),
            "description": "If your Meta template includes a Document, Image, Video, or Text header."
        }),
        ("Body Variables Schema", {
            "fields": ("variables_schema",),
            "description": "JSON array of default variable keys for {{1}}, {{2}}, etc. E.g. ['candidate_name', 'summary.car_model']"
        }),
    )

    def agent_name(self, obj):
        return obj.agent_config.agent.name
    agent_name.short_description = "Agent"


@admin.register(WhatsAppRule)
class WhatsAppRuleAdmin(admin.ModelAdmin):
    list_display = ('rule_name', 'agent_name', 'template_display', 'trigger_statuses', 'min_duration_seconds', 'is_active_badge', 'created_at')
    list_filter = ('is_active', 'agent_config__agent')
    search_fields = ('rule_name', 'agent_config__agent__name', 'template__template_name', 'required_tag', 'required_keyword')

    fieldsets = (
        ("Rule Info & Target Agent", {
            "fields": ("agent_config", "rule_name", "template", "is_active"),
        }),
        ("Trigger Conditions (When to Send)", {
            "fields": ("trigger_statuses", "min_duration_seconds", "required_tag", "required_keyword"),
            "description": "Configure when this message should be sent. Use 'ANY' or comma-separated statuses like 'INTERESTED,CALLBACK,CONFIRMED'."
        }),
        ("Dynamic Variable Customization", {
            "fields": ("variable_mappings", "header_media_url", "delay_seconds"),
            "description": (
                "Define template variables as JSON.<br>"
                "Example: <code>{\"1\": \"candidate_name\", \"2\": \"summary.car_model\", \"3\": \"agent_name\"}</code><br>"
                "Available keys: <code>candidate_name</code>, <code>agent_name</code>, <code>company_name</code>, "
                "<code>summary.car_model</code>, <code>summary.appointment_date</code>, <code>summary.product_interest</code>, "
                "<code>summary.call_summary</code>, or literal text."
            )
        }),
    )

    def agent_name(self, obj):
        return obj.agent_config.agent.name
    agent_name.short_description = "Agent"

    def template_display(self, obj):
        return f"{obj.template.template_name} ({obj.template.language_code})"
    template_display.short_description = "Template"

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green; font-weight: bold;">● Active</span>')
        return format_html('<span style="color: gray; font-weight: bold;">○ Disabled</span>')
    is_active_badge.short_description = "Status"


@admin.register(WhatsAppMessageLog)
class WhatsAppMessageLogAdmin(admin.ModelAdmin):
    list_display = ('recipient_phone', 'agent_name', 'template_name', 'status_badge', 'meta_message_id_short', 'call_record_link', 'created_at')
    list_filter = ('status', 'agent', 'template_name', 'created_at')
    search_fields = ('recipient_phone', 'agent__name', 'meta_message_id', 'template_name', 'error_message')
    readonly_fields = ('agent', 'call_record', 'rule', 'template_name', 'recipient_phone', 'status', 'meta_message_id', 'payload_sent', 'meta_response', 'error_message', 'created_at', 'updated_at')

    def agent_name(self, obj):
        return obj.agent.name if obj.agent else "—"
    agent_name.short_description = "Agent"

    def meta_message_id_short(self, obj):
        if obj.meta_message_id:
            return obj.meta_message_id[:16] + "..." if len(obj.meta_message_id) > 16 else obj.meta_message_id
        return "—"
    meta_message_id_short.short_description = "Meta Msg ID"

    def call_record_link(self, obj):
        if obj.call_record:
            return format_html('<a href="/admin/conversations/sarvamcallrecord/{}/change/">Call #{} ({})</a>', obj.call_record.id, obj.call_record.id, obj.call_record.candidate_name)
        return "—"
    call_record_link.short_description = "Call Record"

    def status_badge(self, obj):
        colors = {
            'QUEUED': '#f59e0b',
            'SENT': '#3b82f6',
            'DELIVERED': '#10b981',
            'READ': '#059669',
            'FAILED': '#ef4444',
            'SKIPPED': '#6b7280',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html('<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;">{}</span>', color, obj.status)
    status_badge.short_description = "Status"

