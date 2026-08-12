from django.contrib import admin
from .models import Industry, AgentRoleTemplate, VoiceAgent

class VoiceAgentAdmin(admin.ModelAdmin):
    list_display = ('name', 'industry', 'role_template', 'is_active', 'used_minutes_display', 'minutes_quota', 'extra_used_minutes', 'max_concurrent_calls', 'owner', 'created_at')
    fields = ('name', 'company_name', 'owner', 'industry', 'role_template', 'summary', 'inbound_phone_number', 'is_demo', 'is_active', 'minutes_quota', 'extra_used_minutes', 'used_minutes_display', 'max_concurrent_calls')
    readonly_fields = ('used_minutes_display',)

    def used_minutes_display(self, obj):
        return f"{obj.used_minutes} min"
    used_minutes_display.short_description = "Used Minutes (Total)"

admin.site.register(Industry)
admin.site.register(AgentRoleTemplate)
admin.site.register(VoiceAgent, VoiceAgentAdmin)