import datetime
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.exceptions import ValidationError
from apps.tenants.models import Tenant
from apps.users.models import User

class TenantService:
    @staticmethod
    def calculate_subscription_status(tenant: Tenant) -> str:
        """
        Dynamically computes tenant subscription status based on current date vs next_due_date and grace period.
        """
        if tenant.billing_type == 'ONE_TIME':
            return 'PAID'

        if not tenant.next_due_date:
            return 'PAID'

        today = timezone.now().date()
        due_date = tenant.next_due_date
        grace_end = due_date + datetime.timedelta(days=tenant.grace_period_days)
        warning_start = due_date - datetime.timedelta(days=7)

        if today > grace_end:
            status = 'OVERDUE'
        elif due_date < today <= grace_end:
            status = 'GRACE_PERIOD'
        elif warning_start <= today <= due_date:
            status = 'DUE_SOON'
        else:
            status = 'PAID'

        if tenant.subscription_status != status:
            tenant.subscription_status = status
            tenant.save(update_fields=['subscription_status'])

        return status

    @staticmethod
    @transaction.atomic
    def create_tenant(
        name: str,
        slug: str = None,
        subscription_plan: str = 'BASIC',
        billing_type: str = 'MONTHLY',
        price_amount: float = 0.00,
        contact_email: str = '',
        contact_phone: str = '',
        notes: str = '',
        next_due_date=None,
        grace_period_days: int = 3,
        admin_username: str = None,
        admin_password: str = None,
        admin_email: str = None,
        admin_first_name: str = '',
        admin_last_name: str = '',
        is_active: bool = True,
        max_properties: int = None,
        max_rooms: int = None,
        max_users: int = None
    ) -> Tenant:
        """
        SSOT function to create a new tenant company account wrapped in an atomic transaction.
        Optionally creates the initial Tenant Admin user account with first/last name.
        """
        if not slug:
            slug = slugify(name)

        if Tenant.objects.filter(slug=slug).exists():
            raise ValidationError({'slug': f'Tenant with slug "{slug}" already exists.'})

        if Tenant.objects.filter(name=name).exists():
            raise ValidationError({'name': f'Tenant with name "{name}" already exists.'})

        today = timezone.now().date()
        if not next_due_date:
            if billing_type == 'ONE_TIME':
                next_due_date = None
            elif billing_type == 'ANNUAL':
                next_due_date = today + datetime.timedelta(days=365)
            else:
                next_due_date = today + datetime.timedelta(days=30)

        tenant = Tenant.objects.create(
            name=name,
            slug=slug,
            subscription_plan=subscription_plan,
            billing_type=billing_type,
            price_amount=price_amount,
            contact_email=contact_email,
            contact_phone=contact_phone,
            notes=notes,
            subscription_start_date=today,
            next_due_date=next_due_date,
            grace_period_days=grace_period_days,
            subscription_status='PAID',
            is_active=is_active,
            max_properties=max_properties,
            max_rooms=max_rooms,
            max_users=max_users
        )

        TenantService.calculate_subscription_status(tenant)

        if admin_username and admin_password:
            admin_email_to_use = admin_email or contact_email or f"admin@{slug}.com"
            if User.objects.filter(username=admin_username).exists():
                raise ValidationError({'admin_username': f'User with username "{admin_username}" already exists.'})
            if User.objects.filter(email=admin_email_to_use).exists():
                raise ValidationError({'admin_email': f'User with email "{admin_email_to_use}" already exists.'})

            User.objects.create_user(
                username=admin_username,
                email=admin_email_to_use,
                password=admin_password,
                first_name=admin_first_name or '',
                last_name=admin_last_name or '',
                role='TENANT_ADMIN',
                tenant=tenant,
                phone_number=contact_phone
            )

        return tenant


    @staticmethod
    @transaction.atomic
    def update_tenant(tenant: Tenant, **kwargs) -> Tenant:
        """
        Updates tenant fields with validation inside an atomic transaction.
        """
        if 'name' in kwargs and kwargs['name'] != tenant.name:
            if Tenant.objects.filter(name=kwargs['name']).exclude(pk=tenant.pk).exists():
                raise ValidationError({'name': 'Tenant with this name already exists.'})
            tenant.name = kwargs['name']

        if 'subscription_plan' in kwargs:
            tenant.subscription_plan = kwargs['subscription_plan']

        if 'billing_type' in kwargs:
            tenant.billing_type = kwargs['billing_type']

        if 'price_amount' in kwargs:
            tenant.price_amount = kwargs['price_amount']

        if 'contact_email' in kwargs:
            tenant.contact_email = kwargs['contact_email']

        if 'contact_phone' in kwargs:
            tenant.contact_phone = kwargs['contact_phone']

        if 'notes' in kwargs:
            tenant.notes = kwargs['notes']

        if 'is_active' in kwargs:
            tenant.is_active = kwargs['is_active']

        if 'next_due_date' in kwargs:
            tenant.next_due_date = kwargs['next_due_date']

        if 'grace_period_days' in kwargs:
            tenant.grace_period_days = kwargs['grace_period_days']

        for quota_field in ['max_properties', 'max_rooms', 'max_users']:
            if quota_field in kwargs:
                setattr(tenant, quota_field, kwargs[quota_field])

        tenant.save()
        TenantService.calculate_subscription_status(tenant)
        return tenant


    @staticmethod
    @transaction.atomic
    def record_payment(tenant: Tenant, amount_paid: float, payment_method: str = 'BANK_TRANSFER', months_to_extend: int = 1) -> Tenant:
        """
        Records a subscription payment and extends next_due_date accordingly.
        """
        today = timezone.now().date()
        base_date = tenant.next_due_date if tenant.next_due_date and tenant.next_due_date >= today else today
        
        # Extend by months (approx 30 days per month or calendar timedelta)
        days_to_add = months_to_extend * 30
        new_due_date = base_date + datetime.timedelta(days=days_to_add)

        tenant.next_due_date = new_due_date
        tenant.subscription_status = 'PAID'
        tenant.save()

        TenantService.calculate_subscription_status(tenant)
        return tenant


