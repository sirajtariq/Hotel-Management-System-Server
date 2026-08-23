from django.contrib import admin
from apps.tenants.models import Tenant

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'subscription_plan', 'is_active', 'created_at')
    search_fields = ('name', 'slug', 'contact_email')
    list_filter = ('subscription_plan', 'is_active')
