from django.db import models
from django.utils import timezone


class PaymentAccount(models.Model):
    ACCOUNT_TYPE_CHOICES = [
        ('CASH', 'Cash / Drawer'),
        ('BANK', 'Bank Account'),
        ('WALLET', 'POS Machine / Digital Wallet'),
    ]

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
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
        unique_together = ('tenant', 'name')

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
