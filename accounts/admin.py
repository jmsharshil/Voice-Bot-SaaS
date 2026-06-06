from django.contrib import admin
from .models import Role, UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'assigned_agent')
    list_filter = ('role', 'assigned_agent')
    search_fields = ('user__username', 'user__email')

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')

