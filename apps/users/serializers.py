from django.db import models
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from apps.users.models import User, Role
from apps.tenants.serializers import TenantSerializer

class RoleSerializer(serializers.ModelSerializer):
    users_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ['id', 'tenant', 'name', 'description', 'permissions', 'is_system', 'users_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'tenant', 'is_system', 'users_count', 'created_at', 'updated_at']

    def get_users_count(self, obj) -> int:
        if hasattr(obj, 'users_count'):
            return obj.users_count
        return obj.users.count()

class UserCustomRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name', 'permissions', 'is_system']

class UserSerializer(serializers.ModelSerializer):
    tenant_details = TenantSerializer(source='tenant', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', default='Global Platform', read_only=True)
    full_name = serializers.SerializerMethodField()
    custom_role = UserCustomRoleSerializer(read_only=True)
    custom_role_details = RoleSerializer(source='custom_role', read_only=True)
    custom_role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), source='custom_role', write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'custom_role', 'custom_role_id', 'custom_role_details',
            'tenant', 'tenant_name', 'tenant_details', 'phone_number',
            'is_active', 'date_joined'
        ]
        read_only_fields = ['id', 'date_joined']

    def get_full_name(self, obj):
        name = f"{obj.first_name or ''} {obj.last_name or ''}".strip()
        return name if name else obj.username

class SuperAdminUserListSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.name', default='Global Platform', read_only=True)
    full_name = serializers.SerializerMethodField()
    assigned_properties_count = serializers.SerializerMethodField()

    fullName = serializers.SerializerMethodField()
    tenantName = serializers.CharField(source='tenant.name', default='Global Platform', read_only=True)
    phoneNumber = serializers.CharField(source='phone_number', default='', read_only=True)
    isActive = serializers.BooleanField(source='is_active', read_only=True)
    dateJoined = serializers.DateTimeField(source='date_joined', read_only=True)
    assignedPropertiesCount = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'full_name',
            'role',
            'tenant_name',
            'phone_number',
            'is_active',
            'date_joined',
            'assigned_properties_count',
            'fullName',
            'tenantName',
            'phoneNumber',
            'isActive',
            'dateJoined',
            'assignedPropertiesCount',
        ]

    def get_full_name(self, obj):
        name = f"{obj.first_name or ''} {obj.last_name or ''}".strip()
        return name if name else obj.username

    def get_fullName(self, obj):
        return self.get_full_name(obj)

    def get_assigned_properties_count(self, obj):
        try:
            if hasattr(obj, 'assigned_properties'):
                return obj.assigned_properties.count()
        except Exception:
            pass
        return 0

    def get_assignedPropertiesCount(self, obj):
        return self.get_assigned_properties_count(obj)


class SuperAdminUserDetailSerializer(serializers.ModelSerializer):
    tenant_details = serializers.SerializerMethodField()
    assigned_properties_details = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()

    fullName = serializers.SerializerMethodField()
    phoneNumber = serializers.CharField(source='phone_number', default='', read_only=True)
    isActive = serializers.BooleanField(source='is_active', read_only=True)
    dateJoined = serializers.DateTimeField(source='date_joined', read_only=True)
    lastLogin = serializers.DateTimeField(source='last_login', read_only=True)
    tenantDetails = serializers.SerializerMethodField()
    assignedPropertiesDetails = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'role',
            'phone_number',
            'is_active',
            'is_superuser',
            'tenant',
            'tenant_details',
            'assigned_properties_details',
            'date_joined',
            'last_login',
            'fullName',
            'phoneNumber',
            'isActive',
            'dateJoined',
            'lastLogin',
            'tenantDetails',
            'assignedPropertiesDetails',
        ]

    def get_full_name(self, obj):
        name = f"{obj.first_name or ''} {obj.last_name or ''}".strip()
        return name if name else obj.username

    def get_fullName(self, obj):
        return self.get_full_name(obj)

    def get_tenant_details(self, obj):
        if obj.tenant:
            return {'id': obj.tenant.id, 'name': obj.tenant.name, 'slug': obj.tenant.slug}
        return None

    def get_tenantDetails(self, obj):
        return self.get_tenant_details(obj)

    def get_assigned_properties_details(self, obj):
        try:
            if hasattr(obj, 'assigned_properties'):
                return list(obj.assigned_properties.values('id', 'name', 'city'))
        except Exception:
            pass
        return []

    def get_assignedPropertiesDetails(self, obj):
        return self.get_assigned_properties_details(obj)

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password', 'first_name',
            'last_name', 'role', 'custom_role', 'tenant', 'phone_number'
        ]

class UserSessionSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    tenant_name = serializers.CharField(source='tenant.name', default=None, read_only=True)
    assigned_properties = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    fullName = serializers.SerializerMethodField()
    isSuperuser = serializers.BooleanField(source='is_superuser', read_only=True)
    tenantName = serializers.CharField(source='tenant.name', default=None, read_only=True)
    assignedProperties = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'full_name',
            'role',
            'is_superuser',
            'tenant',
            'tenant_name',
            'assigned_properties',
            'permissions',
            'fullName',
            'isSuperuser',
            'tenantName',
            'assignedProperties',
        ]

    def get_full_name(self, obj):
        name = f"{obj.first_name or ''} {obj.last_name or ''}".strip()
        return name if name else obj.username

    def get_fullName(self, obj):
        return self.get_full_name(obj)

    def get_assigned_properties(self, obj):
        if obj.is_superuser or obj.role == 'SUPERADMIN':
            return []
        if hasattr(obj, 'assigned_properties') and obj.assigned_properties.exists():
            return list(obj.assigned_properties.values('id', 'name', 'city'))
        if getattr(obj, 'assigned_property_id', None):
            return [{'id': obj.assigned_property.id, 'name': obj.assigned_property.name, 'city': obj.assigned_property.city}]
        return []

    def get_assignedProperties(self, obj):
        return self.get_assigned_properties(obj)

    def get_permissions(self, obj):
        if obj.is_superuser or obj.role == 'SUPERADMIN' or obj.role == 'TENANT_ADMIN':
            return ['*']
        if getattr(obj, 'custom_role', None) and obj.custom_role and obj.custom_role.permissions:
            return list(obj.custom_role.permissions)
        if obj.role == 'PROPERTY_MANAGER':
            from core.permissions_registry import get_all_permission_codes
            return [p for p in get_all_permission_codes() if p != 'roles:manage']
        if obj.role == 'STAFF':
            return ['properties:view', 'rooms:view', 'rooms:change_status', 'bookings:view', 'bookings:create', 'expenses:view', 'expenses:create', 'staff:view']
        if hasattr(obj, 'get_all_permissions'):
            return list(obj.get_all_permissions())
        return []


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['tenant_id'] = user.tenant_id if user.tenant else None
        token['role'] = user.role
        token['username'] = user.username
        token['email'] = user.email
        token['custom_role_permissions'] = list(user.custom_role.permissions) if getattr(user, 'custom_role', None) else []
        return token

    def validate(self, attrs):
        username_or_email = attrs.get('username') or attrs.get('email')
        if username_or_email:
            user = User.objects.select_related('tenant', 'custom_role').prefetch_related('assigned_properties').filter(
                models.Q(username__iexact=username_or_email) | models.Q(email__iexact=username_or_email)
            ).first()
            if user:
                attrs['username'] = user.username

        data = super().validate(attrs)
        if self.user and self.user.tenant and not self.user.tenant.is_active:
            if not (self.user.is_superuser or getattr(self.user, 'role', '') == 'SUPERADMIN'):
                raise serializers.ValidationError({
                    'detail': 'Your tenant account is suspended or inactive. Please contact SuperAdmin support.'
                })
        data['user'] = UserSessionSerializer(self.user).data
        return data

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone_number']
        read_only_fields = ['id', 'username']

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    new_password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'New password and confirm password do not match.'})
        return data

class AdminResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'New password and confirm password do not match.'})
        return data
