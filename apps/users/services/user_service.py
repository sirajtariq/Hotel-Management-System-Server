from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.password_validation import validate_password
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework_simplejwt.tokens import RefreshToken
from apps.users.models import User
from apps.tenants.models import Tenant

class UserService:
    @staticmethod
    def create_user(username: str, email: str, password: str, role: str = 'GUEST', tenant_id: int = None, first_name: str = '', last_name: str = '', phone_number: str = '') -> User:
        """
        SSOT function to register and create a user.
        """
        if User.objects.filter(username=username).exists():
            raise ValidationError({'username': 'A user with this username already exists.'})

        if email and User.objects.filter(email=email).exists():
            raise ValidationError({'email': 'A user with this email already exists.'})

        tenant = None
        if tenant_id:
            try:
                tenant = Tenant.objects.get(id=tenant_id)
            except Tenant.DoesNotExist:
                raise ValidationError({'tenant_id': 'Invalid tenant ID.'})

        if role == 'SUPERADMIN':
            tenant = None  # Superadmins are global
        elif tenant and tenant.max_users is not None:
            current_users = User.objects.filter(tenant=tenant, is_active=True).count()
            if current_users >= tenant.max_users:
                raise ValidationError(f"User account limit reached for this subscription plan (Limit: {tenant.max_users}). Please contact SuperAdmin to upgrade.")

        user = User.objects.create_user(

            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=role,
            tenant=tenant,
            phone_number=phone_number
        )
        return user

    @staticmethod
    def update_user_profile(user: User, data: dict) -> User:
        """
        Updates personal profile details for a user.
        """
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'email' in data:
            new_email = data['email']
            if new_email and new_email != user.email and User.objects.filter(email=new_email).exclude(id=user.id).exists():
                raise ValidationError({'email': 'This email address is already in use by another account.'})
            user.email = new_email
        if 'phone_number' in data:
            user.phone_number = data['phone_number']

        user.save()
        return user

    @staticmethod
    def change_user_password(user: User, old_password: str, new_password: str) -> None:
        """
        Validates old password, validates new password requirements, and changes user password.
        """
        if not user.check_password(old_password):
            raise ValidationError({'old_password': 'Current password is incorrect.'})

        if old_password == new_password:
            raise ValidationError({'new_password': 'New password must be different from current password.'})

        try:
            validate_password(new_password, user=user)
        except (DjangoValidationError, ValidationError) as err:
            msgs = list(err.messages) if hasattr(err, 'messages') else [str(err)]
            raise ValidationError({'new_password': msgs})

        user.set_password(new_password)
        user.save()

    @staticmethod
    def admin_reset_user_password(request_user: User, target_user: User, new_password: str) -> None:
        """
        Enforces role boundaries and resets target user's password without old password verification.
        - SuperAdmin can reset any user.
        - TenantAdmin can only reset users in their own tenant, excluding SuperAdmins.
        """
        is_sa = request_user.is_superuser or getattr(request_user, 'role', '') == 'SUPERADMIN'
        is_ta = getattr(request_user, 'role', '') == 'TENANT_ADMIN'

        if not is_sa:
            if not is_ta:
                raise PermissionDenied('Permission denied: Only Admins can reset other users\' passwords.')

            if target_user.tenant_id != request_user.tenant_id:
                raise PermissionDenied('Permission denied: You can only reset passwords for users in your own tenant.')

            if target_user.is_superuser or getattr(target_user, 'role', '') == 'SUPERADMIN':
                raise PermissionDenied('Permission denied: Tenant Admins cannot reset SuperAdmin passwords.')

        try:
            validate_password(new_password, user=target_user)
        except (DjangoValidationError, ValidationError) as err:
            msgs = list(err.messages) if hasattr(err, 'messages') else [str(err)]
            raise ValidationError({'new_password': msgs})

        target_user.set_password(new_password)
        target_user.save()


    @staticmethod
    def generate_tokens_for_user(user: User) -> dict:
        """
        Generates JWT refresh and access tokens with custom tenant and role claims.
        """
        refresh = RefreshToken.for_user(user)
        refresh['tenant_id'] = user.tenant_id if user.tenant else None
        refresh['role'] = user.role
        refresh['username'] = user.username
        refresh['email'] = user.email

        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

