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
    custom_role = UserCustomRoleSerializer(read_only=True)
    custom_role_details = RoleSerializer(source='custom_role', read_only=True)
    custom_role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), source='custom_role', write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'custom_role', 'custom_role_id', 'custom_role_details',
            'tenant', 'tenant_details', 'phone_number',
            'is_active', 'date_joined'
        ]
        read_only_fields = ['id', 'date_joined']

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password', 'first_name',
            'last_name', 'role', 'custom_role', 'tenant', 'phone_number'
        ]

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
            user = User.objects.select_related('tenant', 'custom_role').filter(
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
        data['user'] = UserSerializer(self.user).data
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
