from django.db import models
from apps.tenants.models import Tenant
from apps.properties.models import Property
from apps.rooms.models import Room

class Booking(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CHECKED_IN', 'Checked In'),
        ('CHECKED_OUT', 'Checked Out'),
        ('CANCELLED', 'Cancelled'),
    )

    PAYMENT_STATUS_CHOICES = (
        ('UNPAID', 'Unpaid'),
        ('PARTIAL', 'Partial'),
        ('PAID', 'Paid'),
    )

    BOOKING_TYPE_CHOICES = (
        ('NIGHTLY', 'Nightly Stay'),
        ('HOURLY', 'Hourly / Short Stay'),
    )

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='bookings')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='bookings')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='bookings')

    guest_name = models.CharField(max_length=255)
    guest_email = models.EmailField(blank=True, null=True)
    guest_phone = models.CharField(max_length=50)

    booking_type = models.CharField(max_length=20, choices=BOOKING_TYPE_CHOICES, default='NIGHTLY', db_index=True)
    check_in_date = models.DateField(db_index=True)
    check_out_date = models.DateField(db_index=True)
    check_in = models.DateTimeField(null=True, blank=True, db_index=True)
    check_out = models.DateTimeField(null=True, blank=True, db_index=True)

    total_nights = models.PositiveIntegerField(default=1)
    total_duration = models.CharField(max_length=50, blank=True, default='')

    DISCOUNT_TYPE_CHOICES = (
        ('FLAT', 'Flat Amount (PKR)'),
        ('PERCENTAGE', 'Percentage (%)'),
    )

    nightly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    rate_applied = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    subtotal_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES, default='FLAT')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text="Tax percentage e.g. 15.00 for 15%")
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    booking_reference = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='UNPAID', db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bookings'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'property', 'status'], name='idx_bk_tenant_prop_stat'),
            models.Index(fields=['tenant', 'check_in_date', 'check_out_date'], name='idx_bk_tenant_dates'),
            models.Index(fields=['tenant', 'booking_reference'], name='idx_bk_tenant_ref'),
            models.Index(fields=['tenant', 'status', 'check_in_date']),
            models.Index(fields=['room', 'check_in_date', 'check_out_date']),
            models.Index(fields=['payment_status']),
        ]


    def __str__(self):
        return f"Booking #{self.id} - {self.guest_name} ({self.room.room_number})"
