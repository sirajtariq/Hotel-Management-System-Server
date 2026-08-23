from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.tenants.models import Tenant

class Role(models.Model):
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='roles'
    )
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True)
    permissions = models.JSONField(default=list, help_text="List of permission code strings")
    is_system = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'roles'
        ordering = ['name']
        unique_together = ('tenant', 'name')

    def __str__(self):
        return f"{self.name} ({self.tenant.name if self.tenant else 'Global'})"

class User(AbstractUser):
    ROLE_CHOICES = (
        ('SUPERADMIN', 'Super Admin'),
        ('TENANT_ADMIN', 'Tenant Admin'),
        ('PROPERTY_MANAGER', 'Property Manager'),
        ('STAFF', 'Staff'),
        ('GUEST', 'Guest'),
    )

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='users',
        null=True,
        blank=True
    )
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='GUEST')
    custom_role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    phone_number = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'users'
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['tenant', 'role']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f"{self.username} ({self.role})"
