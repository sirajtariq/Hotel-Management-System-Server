from django.db import models
from django.utils import timezone


from django.core.exceptions import ValidationError

class PaymentAccount(models.Model):
    ACCOUNT_TYPE_CHOICES = [
        ('CASH', 'Cash Drawer'),
        ('BANK', 'Bank Account'),
        ('ONLINE', 'Online Gateway'),
        ('OTHER', 'Other'),
    ]

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='payment_accounts'
    )
    property = models.ForeignKey(
        'properties.Property',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='payment_accounts'
    )
    name = models.CharField(max_length=120)
    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPE_CHOICES,
        default='CASH'
    )
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    iban = models.CharField(max_length=50, blank=True)
    branch_name = models.CharField(max_length=100, blank=True)
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    current_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_default', 'name']
        unique_together = ('tenant', 'property', 'name')

    def clean(self):
        if self.account_type == 'CASH' and not self.property:
            raise ValidationError({"property": "Cash accounts must be assigned to a specific property."})
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.get_account_type_display()}) - Balance: PKR {self.current_balance}"


class AccountTransaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('INFLOW', 'Inflow / Credit'),
        ('OUTFLOW', 'Outflow / Debit'),
        ('TRANSFER_IN', 'Transfer In'),
        ('TRANSFER_OUT', 'Transfer Out'),
    ]

    SOURCE_MODULE_CHOICES = [
        ('BOOKING', 'Booking Payment'),
        ('POS', 'Restaurant POS'),
        ('EXPENSE', 'Expense Payment'),
        ('TRANSFER', 'Internal Transfer'),
        ('MANUAL', 'Manual Adjustment'),
    ]

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='account_transactions'
    )
    account = models.ForeignKey(
        PaymentAccount,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    balance_after = models.DecimalField(max_digits=14, decimal_places=2)
    source_module = models.CharField(max_length=30, choices=SOURCE_MODULE_CHOICES)
    reference_id = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_type} {self.amount} on {self.account.name} ({self.created_at})"


class AccountTransfer(models.Model):
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='account_transfers'
    )
    from_account = models.ForeignKey(
        PaymentAccount,
        on_delete=models.PROTECT,
        related_name='transfers_sent'
    )
    to_account = models.ForeignKey(
        PaymentAccount,
        on_delete=models.PROTECT,
        related_name='transfers_received'
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    transfer_date = models.DateField(default=timezone.now)
    reference_number = models.CharField(max_length=80, blank=True)
    notes = models.TextField(blank=True)
    receipt_image = models.FileField(upload_to='transfer_receipts/', null=True, blank=True)
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Transfer PKR {self.amount} from {self.from_account.name} to {self.to_account.name}"


class PaymentTransaction(models.Model):
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='payment_transactions'
    )
    booking = models.ForeignKey(
        'bookings.Booking',
        on_delete=models.CASCADE,
        related_name='payment_transactions',
        null=True,
        blank=True
    )
    payment_account = models.ForeignKey(
        PaymentAccount,
        on_delete=models.CASCADE,
        related_name='payment_transactions'
    )
    account_head = models.ForeignKey(
        'expenses.AccountHead',
        on_delete=models.PROTECT,
        related_name='payment_transactions',
        null=True,
        blank=True
    )
    transaction_type = models.CharField(max_length=30, default='REFUND')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    notes = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_type} PKR {self.amount} on {self.payment_account.name} ({self.created_at})"

