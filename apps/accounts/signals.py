from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.tenants.models import Tenant
from apps.accounts.models import PaymentAccount

DEFAULT_ACCOUNTS = [
    {
        'name': 'Main Cash Drawer / Counter',
        'account_type': 'CASH',
        'is_default': True,
        'opening_balance': 0.00,
        'current_balance': 0.00,
    },
    {
        'name': 'Primary Bank Account',
        'account_type': 'BANK',
        'is_default': False,
        'opening_balance': 0.00,
        'current_balance': 0.00,
    },
]


@receiver(post_save, sender=Tenant)
def create_default_payment_accounts(sender, instance, created, **kwargs):
    if created:
        for acc in DEFAULT_ACCOUNTS:
            PaymentAccount.objects.get_or_create(
                tenant=instance,
                name=acc['name'],
                defaults={
                    'account_type': acc['account_type'],
                    'is_default': acc['is_default'],
                    'opening_balance': acc['opening_balance'],
                    'current_balance': acc['current_balance'],
                }
            )
