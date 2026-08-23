from decimal import Decimal
from datetime import date
from django.db import transaction
from django.db.models import Sum
from rest_framework.exceptions import ValidationError
from apps.staff.models import StaffProfile
from apps.properties.models import Property
from apps.tenants.models import Tenant
from apps.users.models import User, Role

class StaffService:
    @staticmethod
    @transaction.atomic
    def create_staff_member(
        tenant: Tenant,
        name: str,
        position: str,
        phone_number: str = '',
        property_obj: Property = None,
        monthly_salary: Decimal = Decimal('0.00'),
        department: str = '',
        hired_date: date = None,
        is_active: bool = True,
        enable_login: bool = False,
        username: str = None,
        email: str = None,
        password: str = None,
        custom_role_id: int = None,
    ) -> StaffProfile:
        """
        SSOT creation of a staff member.
        - Ground Staff: enable_login=False -> user=None, 0 max_users quota consumed.
        - Desk Staff: enable_login=True -> validates max_users quota, creates User account with custom_role.
        """
        if property_obj and property_obj.tenant_id != tenant.id:
            raise ValidationError({'property': 'Selected property does not belong to your tenant.'})

        user_obj = None

        if enable_login:
            # 1. Quota Check
            if tenant.max_users is not None:
                current_user_count = User.objects.filter(tenant=tenant, is_active=True).count()
                if current_user_count >= tenant.max_users:
                    raise ValidationError({
                        'detail': f"Login user limit reached for your plan (Max: {tenant.max_users}). Please upgrade or register as ground staff without login access."
                    })

            # 2. Field validations
            if not username or not username.strip():
                raise ValidationError({'username': 'Username is required when portal login access is enabled.'})

            clean_username = username.strip()
            clean_email = email.strip() if email else ''

            if User.objects.filter(username__iexact=clean_username).exists():
                raise ValidationError({'username': f"Username '{clean_username}' is already taken."})

            if clean_email and User.objects.filter(email__iexact=clean_email).exists():
                raise ValidationError({'email': f"Email '{clean_email}' is already registered."})

            if not password or len(password) < 6:
                raise ValidationError({'password': 'Password must be at least 6 characters long.'})

            custom_role = None
            if custom_role_id:
                try:
                    custom_role = Role.objects.get(id=custom_role_id, tenant=tenant)
                except Role.DoesNotExist:
                    raise ValidationError({'custom_role_id': 'Selected custom role does not exist.'})

            # 3. Create User account
            user_obj = User.objects.create(
                username=clean_username,
                email=clean_email,
                role='STAFF',
                custom_role=custom_role,
                tenant=tenant,
                first_name=name.split(' ')[0] if name else '',
                last_name=' '.join(name.split(' ')[1:]) if len(name.split(' ')) > 1 else '',
                phone_number=phone_number,
                is_active=is_active
            )
            user_obj.set_password(password)
            user_obj.save()

        # 4. Create StaffProfile
        staff = StaffProfile.objects.create(
            tenant=tenant,
            property=property_obj,
            user=user_obj,
            name=name.strip(),
            phone_number=phone_number.strip() if phone_number else '',
            position=position.strip(),
            department=department.strip() if department else '',
            monthly_salary=monthly_salary,
            hired_date=hired_date,
            is_active=is_active
        )
        return staff

    @staticmethod
    @transaction.atomic
    def update_staff_member(
        staff_profile: StaffProfile,
        name: str = None,
        position: str = None,
        phone_number: str = None,
        property_obj: Property = None,
        monthly_salary: Decimal = None,
        department: str = None,
        hired_date: date = None,
        is_active: bool = None,
        enable_login: bool = None,
        username: str = None,
        email: str = None,
        password: str = None,
        custom_role_id: int = None,
    ) -> StaffProfile:
        """
        SSOT update of a staff member & linked portal login account.
        """
        tenant = staff_profile.tenant

        if property_obj is not None:
            if property_obj and property_obj.tenant_id != tenant.id:
                raise ValidationError({'property': 'Selected property does not belong to your tenant.'})
            staff_profile.property = property_obj

        if name is not None:
            staff_profile.name = name.strip()
        if position is not None:
            staff_profile.position = position.strip()
        if phone_number is not None:
            staff_profile.phone_number = phone_number.strip()
        if monthly_salary is not None:
            staff_profile.monthly_salary = monthly_salary
        if department is not None:
            staff_profile.department = department.strip()
        if hired_date is not None:
            staff_profile.hired_date = hired_date
        if is_active is not None:
            staff_profile.is_active = is_active
            if staff_profile.user:
                staff_profile.user.is_active = is_active
                staff_profile.user.save()

        # Handle portal login access toggle
        if enable_login is True:
            custom_role = None
            if custom_role_id:
                try:
                    custom_role = Role.objects.get(id=custom_role_id, tenant=tenant)
                except Role.DoesNotExist:
                    raise ValidationError({'custom_role_id': 'Selected custom role does not exist.'})

            if staff_profile.user:
                user_obj = staff_profile.user
                if username and username.strip():
                    clean_user = username.strip()
                    if User.objects.filter(username__iexact=clean_user).exclude(id=user_obj.id).exists():
                        raise ValidationError({'username': f"Username '{clean_user}' is already taken."})
                    user_obj.username = clean_user

                if email is not None:
                    clean_email = email.strip()
                    if clean_email and User.objects.filter(email__iexact=clean_email).exclude(id=user_obj.id).exists():
                        raise ValidationError({'email': f"Email '{clean_email}' is already registered."})
                    user_obj.email = clean_email

                if custom_role_id is not None:
                    user_obj.custom_role = custom_role

                if password and len(password) >= 6:
                    user_obj.set_password(password)

                if is_active is not None:
                    user_obj.is_active = is_active

                user_obj.save()
            else:
                # Enabling login now -> check quota
                if tenant.max_users is not None:
                    current_user_count = User.objects.filter(tenant=tenant, is_active=True).count()
                    if current_user_count >= tenant.max_users:
                        raise ValidationError({
                            'detail': f"Login user limit reached for your plan (Max: {tenant.max_users}). Please upgrade or register as ground staff without login access."
                        })

                if not username or not username.strip():
                    raise ValidationError({'username': 'Username is required when enabling portal login.'})
                clean_user = username.strip()
                if User.objects.filter(username__iexact=clean_user).exists():
                    raise ValidationError({'username': f"Username '{clean_user}' is already taken."})

                if not password or len(password) < 6:
                    raise ValidationError({'password': 'Password must be at least 6 characters long.'})

                new_user = User.objects.create(
                    username=clean_user,
                    email=email.strip() if email else '',
                    role='STAFF',
                    custom_role=custom_role,
                    tenant=tenant,
                    first_name=staff_profile.name.split(' ')[0],
                    last_name=' '.join(staff_profile.name.split(' ')[1:]) if len(staff_profile.name.split(' ')) > 1 else '',
                    phone_number=staff_profile.phone_number,
                    is_active=staff_profile.is_active
                )
                new_user.set_password(password)
                new_user.save()
                staff_profile.user = new_user

        elif enable_login is False:
            if staff_profile.user:
                linked_user = staff_profile.user
                staff_profile.user = None
                staff_profile.save()
                linked_user.delete()

        staff_profile.save()
        return staff_profile

    @staticmethod
    @transaction.atomic
    def delete_staff_member(staff_profile: StaffProfile) -> None:
        """
        SSOT deletion of staff member & linked login user account.
        """
        user_obj = staff_profile.user
        staff_profile.delete()
        if user_obj:
            user_obj.delete()

    @staticmethod
    def calculate_monthly_payroll(tenant_id: int, property_id: int = None) -> Decimal:
        """
        SSOT calculation of total active staff payroll per month.
        """
        query = StaffProfile.objects.filter(tenant_id=tenant_id, is_active=True)
        if property_id:
            query = query.filter(property_id=property_id)

        total = query.aggregate(total=Sum('monthly_salary'))['total']
        return total or Decimal('0.00')
