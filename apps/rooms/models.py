from django.db import models
from django.core.cache import cache
from apps.tenants.models import Tenant
from apps.properties.models import Property

class RoomType(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='room_types')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='room_types')
    name = models.CharField(max_length=100)
    base_price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Rate per hour for short stay")
    is_hourly_allowed = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    max_occupancy = models.PositiveIntegerField(default=2)
    description = models.TextField(blank=True, null=True)
    amenities = models.JSONField(default=list, blank=True, help_text="Room type default amenities list")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'room_types'
        unique_together = ('property', 'name')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'property'], name='idx_rtype_tenant_prop'),
            models.Index(fields=['tenant', 'is_active'], name='idx_rtype_tenant_active'),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        tenant_id = self.tenant_id or 'global'
        cache.delete(f"tenant_{tenant_id}_room_type_selector_all")
        if self.property_id:
            cache.delete(f"tenant_{tenant_id}_room_type_selector_{self.property_id}")

    def delete(self, *args, **kwargs):
        tenant_id = self.tenant_id or 'global'
        prop_id = self.property_id
        super().delete(*args, **kwargs)
        cache.delete(f"tenant_{tenant_id}_room_type_selector_all")
        if prop_id:
            cache.delete(f"tenant_{tenant_id}_room_type_selector_{prop_id}")

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
    base_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Room specific base price override per night")
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Rate per hour for short stay")
    is_hourly_allowed = models.BooleanField(default=True)
    amenities = models.JSONField(default=list, blank=True, help_text="Room specific amenities override")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rooms'
        unique_together = ('property', 'room_number')
        ordering = ['room_number']
        indexes = [
            models.Index(fields=['tenant', 'property', 'status'], name='idx_room_tenant_prop_stat'),
            models.Index(fields=['tenant', 'room_type'], name='idx_room_tenant_type'),
            models.Index(fields=['tenant', 'room_number'], name='idx_room_tenant_num'),
        ]

    def save(self, *args, **kwargs):
        if self.room_type:
            if (self.base_price is None or float(self.base_price) <= 0) and self.room_type.base_price_per_night is not None:
                self.base_price = self.room_type.base_price_per_night
            if (self.hourly_rate is None or float(self.hourly_rate) <= 0) and self.room_type.hourly_rate is not None:
                self.hourly_rate = self.room_type.hourly_rate
            if self.is_hourly_allowed is None and self.room_type.is_hourly_allowed is not None:
                self.is_hourly_allowed = self.room_type.is_hourly_allowed
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Room {self.room_number} ({self.property.name}) - {self.status}"
