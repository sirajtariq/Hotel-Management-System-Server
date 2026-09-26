from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from apps.users.models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'tenant', 'is_staff', 'is_active')
    list_filter = ('role', 'tenant', 'is_staff', 'is_active')
    fieldsets = tuple(BaseUserAdmin.fieldsets or ()) + (
        ('Tenant & Role Info', {'fields': ('tenant', 'role', 'phone_number')}),
    )
    add_fieldsets = tuple(BaseUserAdmin.add_fieldsets or ()) + (
        ('Tenant & Role Info', {'fields': ('tenant', 'role', 'phone_number')}),
    )
