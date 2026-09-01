from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.tenants.models import Tenant
from apps.expenses.models import AccountHead

DEFAULT_ACCOUNT_HEADS = [
    ("Kitchen Grocery & Food Supplies", "Food items, kitchen raw materials, produce and beverages"),
    ("Electricity, Gas & Water Utilities", "Monthly power, gas, and water utility bill payments"),
    ("Generator Fuel & Diesel", "Fuel for standby power generators and machinery"),
    ("Repairs, Plumbing & Maintenance", "Building, electrical, plumbing, HVAC and room repairs"),
    ("Staff Welfare, Tea & Meals", "Staff tea, snacks, daily meals and employee welfare"),
    ("Laundry & Cleaning Chemicals", "Linen washing, detergents, housekeeping chemicals & soaps"),
    ("Printing, Stationery & Misc", "Office stationery, receipt printing and miscellaneous expenses"),
]

@receiver(post_save, sender=Tenant)
def seed_default_account_heads(sender, instance, created, **kwargs):
    """
    Automatically provision 7 standard active Account Heads when a new tenant is created.
    """
    if created:
        for name, description in DEFAULT_ACCOUNT_HEADS:
            AccountHead.objects.get_or_create(
                tenant=instance,
                name=name,
                defaults={'description': description, 'is_active': True}
            )
