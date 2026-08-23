from django.db import models
from apps.tenants.models import Tenant
from apps.properties.models import Property

class RoomType(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='room_types')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='room_types')
    name = models.CharField(max_length=100)
    base_price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Rate per hour for short stay")
    is_hourly_allowed = models.BooleanField(default=True)
    max_occupancy = models.PositiveIntegerField(default=2)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'room_types'
        unique_together = ('property', 'name')
        ordering = ['name']
        indexes = [
            models.Index(fields=['tenant', 'property']),
        ]

    def __str__(self):
        return f"{self.name} ({self.property.name}) - ${self.base_price_per_night}/night"

class Room(models.Model):
    STATUS_CHOICES = (
        ('AVAILABLE', 'Available'),
        ('OCCUPIED', 'Occupied'),
        ('RESERVED', 'Reserved'),
        ('CLEANING', 'Cleaning'),
        ('MAINTENANCE', 'Maintenance'),
    )

    HOUSEKEEPING_STATUS_CHOICES = (
        ('CLEAN', 'Clean'),
        ('DIRTY', 'Dirty'),
        ('IN_PROGRESS', 'In Progress'),
        ('INSPECTED', 'Inspected'),
    )

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='rooms')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='rooms')
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name='rooms')
    room_number = models.CharField(max_length=50)
    floor = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='AVAILABLE', db_index=True)
    housekeeping_status = models.CharField(max_length=50, choices=HOUSEKEEPING_STATUS_CHOICES, default='CLEAN', db_index=True)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Rate per hour for short stay")
    is_hourly_allowed = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rooms'
        unique_together = ('property', 'room_number')
        ordering = ['room_number']
        indexes = [
            models.Index(fields=['tenant', 'property', 'status']),
            models.Index(fields=['room_number']),
        ]

    def __str__(self):
        return f"Room {self.room_number} ({self.property.name}) - {self.status}"
