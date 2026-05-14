from django.contrib import admin
from .models import Industry, AgentRoleTemplate, VoiceAgent

admin.site.register(Industry)
admin.site.register(AgentRoleTemplate)
admin.site.register(VoiceAgent)