from django.db import models
from django.utils import timezone
from apps.tenants.models import Tenant
from apps.properties.models import Property
from django.conf import settings

class AccountHead(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='account_heads')
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'account_heads'
        unique_together = ('tenant', 'name')
        ordering = ['name']

    def __str__(self):
        return f"{self.name}"

class ExpenseCategory(models.Model):
    """Legacy Category Model kept for backward compatibility."""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='expense_categories')
    name = models.CharField(max_length=100)

    class Meta:
        db_table = 'expense_categories'
        unique_together = ('tenant', 'name')
        ordering = ['name']

    def __str__(self):
        return f"{self.name}"

class Expense(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash / Counter Drawer'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CARD', 'Credit / Debit Card'),
        ('ONLINE', 'Online / Wallet'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='expenses')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='expenses')
    account_head = models.ForeignKey(AccountHead, on_delete=models.PROTECT, related_name='expenses', null=True, blank=True)
    category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, related_name='expenses', null=True, blank=True)
    
    item_name = models.CharField(max_length=255, blank=True, default='')
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES, default='CASH')
    vendor_name = models.CharField(max_length=150, blank=True, default='')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField(default=timezone.now, db_index=True)
    receipt_number = models.CharField(max_length=80, blank=True, default='')
    receipt_image = models.FileField(upload_to='expense_receipts/', null=True, blank=True)

    description = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'expenses'
        ordering = ['-expense_date', '-id']
        indexes = [
            models.Index(fields=['tenant', 'property', 'expense_date']),
            models.Index(fields=['account_head']),
            models.Index(fields=['payment_method']),
        ]

    def __str__(self):
        head_name = self.account_head.name if self.account_head else (self.category.name if self.category else 'Expense')
        return f"{head_name} - Rs. {self.amount} ({self.vendor_name or 'N/A'})"
