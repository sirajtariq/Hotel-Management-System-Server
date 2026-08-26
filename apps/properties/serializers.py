from rest_framework import serializers
from apps.properties.models import Property

class PropertyListSerializer(serializers.ModelSerializer):
    total_rooms = serializers.IntegerField(read_only=True)
    booked_rooms = serializers.IntegerField(read_only=True)
    cleaning_rooms = serializers.IntegerField(read_only=True)
    available_rooms = serializers.IntegerField(read_only=True)
    occupancy_rate = serializers.SerializerMethodField()
    est_monthly_revenue = serializers.SerializerMethodField()
    property_type = serializers.SerializerMethodField()

    # camelCase field aliases for frontend safe data binding
    totalRooms = serializers.IntegerField(source='total_rooms', read_only=True)
    bookedRooms = serializers.IntegerField(source='booked_rooms', read_only=True)
    cleaningRooms = serializers.IntegerField(source='cleaning_rooms', read_only=True)
    availableRooms = serializers.IntegerField(source='available_rooms', read_only=True)
    occupancyRate = serializers.SerializerMethodField()
    estMonthlyRevenue = serializers.SerializerMethodField()
    propertyType = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            'id',
            'name',
            'property_type',
            'propertyType',
            'city',
            'address',
            'phone',
            'email',
            'monthly_rent',
            'status',
            'total_rooms',
            'booked_rooms',
            'cleaning_rooms',
            'available_rooms',
            'totalRooms',
            'bookedRooms',
            'cleaningRooms',
            'availableRooms',
            'occupancy_rate',
            'occupancyRate',
            'est_monthly_revenue',
            'estMonthlyRevenue',
            'created_at',
        ]

    def get_occupancy_rate(self, obj):
        total = getattr(obj, 'total_rooms', 0) or 0
        booked = getattr(obj, 'booked_rooms', 0) or 0
        return round((booked / total) * 100, 1) if total > 0 else 0.0

    def get_occupancyRate(self, obj):
        return self.get_occupancy_rate(obj)

    def get_est_monthly_revenue(self, obj):
        rent = float(getattr(obj, 'monthly_rent', 0.0) or 0.0)
        return rent if rent > 0 else 0.0

    def get_estMonthlyRevenue(self, obj):
        return self.get_est_monthly_revenue(obj)

    def get_property_type(self, obj):
        return getattr(obj, 'property_type', 'Hotel Branch')

    def get_propertyType(self, obj):
        return self.get_property_type(obj)


class PropertyDetailSerializer(serializers.ModelSerializer):
    """Full detail view for single property modal/editing"""
    class Meta:
        model = Property
        fields = '__all__'


class PropertySelectorSerializer(serializers.ModelSerializer):
    """Ultra-lightweight selector for global dropdowns (~30 bytes per row)"""
    class Meta:
        model = Property
        fields = ['id', 'name', 'city']
