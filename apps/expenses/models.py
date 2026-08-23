from django.db import models
from apps.tenants.models import Tenant
from apps.properties.models import Property
from django.conf import settings

class ExpenseCategory(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='expense_categories')
    name = models.CharField(max_length=100)

    class Meta:
        db_table = 'expense_categories'
        unique_together = ('tenant', 'name')
        ordering = ['name']

    def __str__(self):
        return f"{self.name}"

class Expense(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='expenses')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='expenses')
    category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE, related_name='expenses')
    
    item_name = models.CharField(max_length=255)
    vendor_name = models.CharField(max_length=255, blank=True, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField(db_index=True)

    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'expenses'
        ordering = ['-expense_date']
        indexes = [
            models.Index(fields=['tenant', 'property', 'expense_date']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.item_name} - ${self.amount} ({self.vendor_name or 'N/A'})"
