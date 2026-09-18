from django.db import models
from django.core.cache import cache
from apps.tenants.models import Tenant

class Property(models.Model):
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('MAINTENANCE', 'Maintenance'),
        ('INACTIVE', 'Inactive'),
    )

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='properties')
    name = models.CharField(max_length=255)
    address = models.TextField()
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='USA')
    phone = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    monthly_rent = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='ACTIVE', db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        db_table = 'properties'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status'], name='idx_prop_tenant_stat'),
            models.Index(fields=['tenant', 'city'], name='idx_prop_tenant_city'),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        tenant_id = self.tenant_id or 'global'
        cache.delete(f"tenant_{tenant_id}_property_selector")

    def delete(self, using=None, keep_parents=False):
        tenant_id = self.tenant_id or 'global'
        result = super().delete(using=using, keep_parents=keep_parents)
        cache.delete(f"tenant_{tenant_id}_property_selector")
        return result

    def __str__(self):
        return f"{self.name} - {self.city}"
