from rest_framework import serializers
from apps.rooms.models import Room, RoomType

class RoomTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomType
        fields = [
            'id', 'tenant', 'property', 'name',
            'base_price_per_night', 'max_occupancy',
            'description', 'created_at'
        ]
        read_only_fields = ['id', 'tenant', 'created_at']

class AvailableRoomSelectorSerializer(serializers.ModelSerializer):
    property_id = serializers.IntegerField(source='property.id', read_only=True)
    room_type_name = serializers.CharField(source='room_type.name', read_only=True, default='Standard Room')
    max_occupancy = serializers.IntegerField(source='room_type.max_occupancy', read_only=True, default=2)
    base_price = serializers.SerializerMethodField()
    hourly_rate = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = [
            'id',
            'property_id',
            'room_number',
            'room_type_name',
            'floor',
            'max_occupancy',
            'base_price',
            'hourly_rate',
            'is_hourly_allowed',
        ]

    def get_base_price(self, obj) -> float:
        if obj.room_type and obj.room_type.base_price_per_night is not None:
            return float(obj.room_type.base_price_per_night)
        return 0.0

    def get_hourly_rate(self, obj) -> float:
        if getattr(obj, 'hourly_rate', None) is not None:
            return float(obj.hourly_rate)
        if obj.room_type and getattr(obj.room_type, 'hourly_rate', None) is not None:
            return float(obj.room_type.hourly_rate)
        base_p = self.get_base_price(obj)
        return round(base_p / 6.0, 2) if base_p > 0 else 1000.0

class RoomSerializer(serializers.ModelSerializer):
    room_type_details = RoomTypeSerializer(source='room_type', read_only=True)
    room_type_name = serializers.SerializerMethodField()
    base_price = serializers.SerializerMethodField()
    hourly_rate = serializers.SerializerMethodField()
    current_guest_name = serializers.SerializerMethodField()
    active_booking_id = serializers.SerializerMethodField()
    housekeeping_status = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = [
            'id', 'tenant', 'property', 'room_type',
            'room_type_details', 'room_type_name', 'base_price', 'hourly_rate',
            'is_hourly_allowed', 'room_number', 'floor', 'status', 'housekeeping_status',
            'current_guest_name', 'active_booking_id',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']

    def to_internal_value(self, data):
        if isinstance(data, dict):
            data = data.copy()
            if 'property_id' in data and 'property' not in data:
                data['property'] = data['property_id']
            if 'room_type_id' in data and 'room_type' not in data:
                data['room_type'] = data['room_type_id']
        return super().to_internal_value(data)

    def get_room_type_name(self, obj) -> str:
        return obj.room_type.name if obj.room_type else "Standard Room"

    def get_base_price(self, obj) -> float:
        if obj.room_type and obj.room_type.base_price_per_night is not None:
            return float(obj.room_type.base_price_per_night)
        return 0.0

    def get_hourly_rate(self, obj) -> float:
        if getattr(obj, 'hourly_rate', None) is not None:
            return float(obj.hourly_rate)
        if obj.room_type and getattr(obj.room_type, 'hourly_rate', None) is not None:
            return float(obj.room_type.hourly_rate)
        base_p = self.get_base_price(obj)
        return round(base_p / 6.0, 2) if base_p > 0 else 1000.0

    def get_current_guest_name(self, obj) -> str | None:
        active_booking = getattr(obj, '_active_booking', None)
        if active_booking is None:
            from apps.bookings.models import Booking
            active_booking = Booking.objects.filter(
                room=obj, status__in=['CHECKED_IN', 'CONFIRMED']
            ).order_by('-created_at').first()
        return active_booking.guest_name if active_booking else None

    def get_active_booking_id(self, obj):
        active_booking = getattr(obj, '_active_booking', None)
        if active_booking is None:
            from apps.bookings.models import Booking
            active_booking = Booking.objects.filter(
                room=obj, status__in=['CHECKED_IN', 'CONFIRMED']
            ).order_by('-created_at').first()
        return active_booking.id if active_booking else None

    def get_housekeeping_status(self, obj) -> str:
        return getattr(obj, 'housekeeping_status', 'CLEAN') or 'CLEAN'

