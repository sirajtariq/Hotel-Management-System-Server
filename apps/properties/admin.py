from django.contrib import admin
from apps.properties.models import Property

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'city', 'monthly_rent', 'status', 'created_at')
    search_fields = ('name', 'city', 'address')
    list_filter = ('tenant', 'status', 'city')
