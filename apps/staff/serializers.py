from rest_framework import serializers
from apps.staff.models import StaffProfile

class StaffProfileSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source='property.name', read_only=True)
    has_login_access = serializers.SerializerMethodField()
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    custom_role = serializers.SerializerMethodField()

    # Write fields for login creation/update
    enable_login = serializers.BooleanField(write_only=True, required=False, default=False)
    login_username = serializers.CharField(write_only=True, required=False, allow_blank=True)
    login_email = serializers.CharField(write_only=True, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, style={'input_type': 'password'})
    custom_role_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = StaffProfile
        fields = [
            'id', 'tenant', 'property', 'property_name', 'name', 'phone_number',
            'position', 'department', 'monthly_salary', 'hired_date', 'is_active',
            'has_login_access', 'user_id', 'username', 'email', 'custom_role',
            'enable_login', 'login_username', 'login_email', 'password', 'custom_role_id',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']

    def get_has_login_access(self, obj) -> bool:
        return bool(obj.user_id and obj.user and obj.user.is_active)

    def get_custom_role(self, obj):
        if obj.user and obj.user.custom_role:
            return {
                'id': obj.user.custom_role.id,
                'name': obj.user.custom_role.name,
            }
        return None
