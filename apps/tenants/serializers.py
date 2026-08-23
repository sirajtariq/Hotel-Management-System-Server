from rest_framework import serializers
from apps.tenants.models import Tenant

class TenantSerializer(serializers.ModelSerializer):
    current_users_count = serializers.SerializerMethodField()
    current_properties_count = serializers.SerializerMethodField()
    current_rooms_count = serializers.SerializerMethodField()

    admin_username = serializers.CharField(write_only=True, required=False, allow_blank=True)
    admin_password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    admin_email = serializers.CharField(write_only=True, required=False, allow_blank=True)
    admin_first_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    admin_last_name = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Tenant
        fields = [
            'id', 'name', 'slug', 'subscription_plan', 'billing_type',
            'price_amount', 'subscription_start_date', 'next_due_date',
            'grace_period_days', 'subscription_status',
            'is_active', 'contact_email', 'contact_phone',
            'notes', 'created_at', 'updated_at',
            'max_properties', 'max_rooms', 'max_users',
            'current_properties_count', 'current_rooms_count', 'current_users_count',
            'admin_username', 'admin_password', 'admin_email',
            'admin_first_name', 'admin_last_name'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'current_properties_count', 'current_rooms_count', 'current_users_count'
        ]

    def get_current_users_count(self, obj) -> int:
        if hasattr(obj, 'current_users_count'):
            return obj.current_users_count
        return obj.users.count()

    def get_current_properties_count(self, obj) -> int:
        if hasattr(obj, 'current_properties_count'):
            return obj.current_properties_count
        return obj.properties.count()

    def get_current_rooms_count(self, obj) -> int:
        if hasattr(obj, 'current_rooms_count'):
            return obj.current_rooms_count
        from apps.rooms.models import Room
        return Room.objects.filter(tenant=obj).count()




