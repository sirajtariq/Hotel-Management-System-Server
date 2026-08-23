from decimal import Decimal
from django.db import models
from django.conf import settings
from apps.tenants.models import Tenant
from apps.properties.models import Property

class StaffProfile(models.Model):
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='staff_profiles',
        db_index=True
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_members',
        db_index=True
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_profile'
    )
    name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=50, blank=True, default='')
    position = models.CharField(max_length=100)
    department = models.CharField(max_length=100, blank=True, default='')
    monthly_salary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    hired_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'staff_profiles'
        ordering = ['name']
        indexes = [
            models.Index(fields=['tenant', 'property', 'is_active']),
            models.Index(fields=['tenant', 'is_active']),
            models.Index(fields=['position']),
        ]


    def __str__(self):
        prop_name = self.property.name if self.property else 'All Properties'
        return f"{self.name} - {self.position} ({prop_name})"
