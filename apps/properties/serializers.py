from rest_framework import serializers
from apps.properties.models import Property

class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = [
            'id', 'tenant', 'name', 'address', 'city',
            'country', 'phone', 'email', 'monthly_rent',
            'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']
