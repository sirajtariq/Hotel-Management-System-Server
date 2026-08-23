from django.contrib import admin
from apps.staff.models import StaffProfile

@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'position', 'department', 'property', 'monthly_salary', 'is_active', 'hired_date')
    search_fields = ('name', 'phone', 'email', 'position')
    list_filter = ('tenant', 'property', 'department', 'is_active')
