from django.db import models
from django.utils import timezone

class Tenant(models.Model):
    PLAN_CHOICES = (
        ('BASIC', 'Basic'),
        ('STANDARD', 'Standard'),
        ('PREMIUM', 'Premium'),
    )

    BILLING_TYPE_CHOICES = (
        ('MONTHLY', 'Monthly Subscription'),
        ('ONE_TIME', 'One-Time License'),
        ('ANNUAL', 'Annual Subscription'),
    )

    SUBSCRIPTION_STATUS_CHOICES = (
        ('PAID', 'Paid'),
        ('DUE_SOON', 'Due Soon'),
        ('GRACE_PERIOD', 'In Grace Period'),
        ('OVERDUE', 'Overdue'),
    )

    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    subscription_plan = models.CharField(max_length=50, choices=PLAN_CHOICES, default='BASIC')
    billing_type = models.CharField(max_length=50, choices=BILLING_TYPE_CHOICES, default='MONTHLY')
    price_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Subscription Lifecycle Fields
    subscription_start_date = models.DateField(default=timezone.now)
    next_due_date = models.DateField(null=True, blank=True)
    grace_period_days = models.IntegerField(default=3)
    subscription_status = models.CharField(max_length=30, choices=SUBSCRIPTION_STATUS_CHOICES, default='PAID', db_index=True)

    is_active = models.BooleanField(default=True, db_index=True)

    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    # Quotas & Limits (null = Unlimited)
    max_properties = models.PositiveIntegerField(null=True, blank=True, help_text="Max properties allowed. Null = Unlimited.")
    max_rooms = models.PositiveIntegerField(null=True, blank=True, help_text="Max rooms allowed. Null = Unlimited.")
    max_users = models.PositiveIntegerField(null=True, blank=True, help_text="Max login user accounts allowed. Null = Unlimited.")

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tenants'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
            models.Index(fields=['subscription_status']),
        ]

    def __str__(self):
        return f"{self.name} ({self.slug})"


