from django.contrib import admin
from apps.bookings.models import Booking

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'guest_name', 'property', 'room', 'check_in_date', 'check_out_date', 'total_amount', 'paid_amount', 'payment_status', 'status')
    search_fields = ('guest_name', 'guest_email', 'guest_phone')
    list_filter = ('tenant', 'property', 'status', 'payment_status')
