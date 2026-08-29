from rest_framework import serializers
from apps.rooms.models import Room, RoomType

class RoomTypeSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source='property.name', read_only=True)
    base_price = serializers.DecimalField(source='base_price_per_night', max_digits=10, decimal_places=2)
    is_hourly_allowed = serializers.SerializerMethodField()

    class Meta:
        model = RoomType
        fields = [
            'id',
            'property',
            'property_name',
            'name',
            'base_price',
            'hourly_rate',
            'is_hourly_allowed',
            'max_occupancy',
            'amenities',
            'description',
            'created_at',
        ]
        read_only_fields = ['id', 'tenant', 'created_at']

    def to_internal_value(self, data):
        if isinstance(data, dict):
            data = data.copy()
            if 'property_id' in data and 'property' not in data and data['property_id']:
                data['property'] = data['property_id']
            if 'propertyId' in data and 'property' not in data and data['propertyId']:
                data['property'] = data['propertyId']
            if 'base_price' in data and 'base_price_per_night' not in data:
                data['base_price_per_night'] = data['base_price']
            if 'basePricePerNight' in data and 'base_price_per_night' not in data:
                data['base_price_per_night'] = data['basePricePerNight']
            if 'basePrice' in data and 'base_price_per_night' not in data:
                data['base_price_per_night'] = data['basePrice']
            if 'maxOccupancy' in data and 'max_occupancy' not in data:
                data['max_occupancy'] = data['maxOccupancy']
            if 'capacity' in data and 'max_occupancy' not in data:
                data['max_occupancy'] = data['capacity']
            if 'isHourlyAllowed' in data and 'is_hourly_allowed' not in data:
                data['is_hourly_allowed'] = data['isHourlyAllowed']
            if 'hourlyRate' in data and 'hourly_rate' not in data:
                data['hourly_rate'] = data['hourlyRate']
        return super().to_internal_value(data)

    def get_is_hourly_allowed(self, obj):
        # Strict evaluation: hourly is only allowed if flag is True AND hourly_rate > 0
        if not obj.is_hourly_allowed:
            return False
        return bool(obj.hourly_rate and float(obj.hourly_rate) > 0)

class RoomTypeSelectorSerializer(serializers.ModelSerializer):
    base_price = serializers.DecimalField(source='base_price_per_night', max_digits=10, decimal_places=2, read_only=True)
    baseRate = serializers.DecimalField(source='base_price_per_night', max_digits=10, decimal_places=2, read_only=True)
    hourlyRate = serializers.DecimalField(source='hourly_rate', max_digits=10, decimal_places=2, read_only=True, allow_null=True)
    maxOccupancy = serializers.IntegerField(source='max_occupancy', read_only=True)

    class Meta:
        model = RoomType
        fields = [
            'id',
            'name',
            'base_price_per_night',
            'base_price',
            'baseRate',
            'hourly_rate',
            'hourlyRate',
            'is_hourly_allowed',
            'max_occupancy',
            'maxOccupancy',
            'amenities',
        ]

class AvailableRoomSelectorSerializer(serializers.ModelSerializer):
    property_id = serializers.IntegerField(source='property.id', read_only=True)
    property_name = serializers.CharField(source='property.name', read_only=True, default='')
    room_type_name = serializers.CharField(source='room_type.name', read_only=True, default='Standard Room')
    max_occupancy = serializers.IntegerField(source='room_type.max_occupancy', read_only=True, default=2)
    base_price = serializers.SerializerMethodField()
    hourly_rate = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = [
            'id',
            'property_id',
            'property_name',
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
        if getattr(obj, 'hourly_rate', None) is not None and float(obj.hourly_rate) > 0:
            return float(obj.hourly_rate)
        if obj.room_type and getattr(obj.room_type, 'hourly_rate', None) is not None:
            return float(obj.room_type.hourly_rate)
        return 0.0

class RoomListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source='property.name', read_only=True, default='')
    room_type_name = serializers.CharField(source='room_type.name', read_only=True, default='Standard Room')
    max_occupancy = serializers.IntegerField(source='room_type.max_occupancy', read_only=True, default=2)
    capacity = serializers.IntegerField(source='room_type.max_occupancy', read_only=True, default=2)
    base_price = serializers.SerializerMethodField()
    hourly_rate = serializers.SerializerMethodField()
    is_hourly_allowed = serializers.SerializerMethodField()
    current_guest_name = serializers.SerializerMethodField()
    active_booking_id = serializers.SerializerMethodField()
    housekeeping_status = serializers.SerializerMethodField()
    amenities = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = [
            'id',
            'property',
            'property_name',
            'room_type',
            'room_type_name',
            'room_number',
            'floor',
            'max_occupancy',
            'capacity',
            'base_price',
            'hourly_rate',
            'is_hourly_allowed',
            'status',
            'housekeeping_status',
            'amenities',
            'current_guest_name',
            'active_booking_id',
        ]

    def get_base_price(self, obj) -> float:
        if getattr(obj, 'base_price', None) and float(obj.base_price) > 0:
            return float(obj.base_price)
        if obj.room_type and obj.room_type.base_price_per_night:
            return float(obj.room_type.base_price_per_night)
        return 0.0

    def get_hourly_rate(self, obj) -> float:
        if getattr(obj, 'hourly_rate', None) is not None and float(obj.hourly_rate) > 0:
            return float(obj.hourly_rate)
        if obj.room_type and getattr(obj.room_type, 'hourly_rate', None) is not None:
            return float(obj.room_type.hourly_rate)
        return 0.0

    def get_is_hourly_allowed(self, obj):
        rate = self.get_hourly_rate(obj)
        if rate <= 0:
            return False
        if obj.room_type and getattr(obj.room_type, 'is_hourly_allowed', True) is False:
            return False
        if getattr(obj, 'is_hourly_allowed', None) is not None:
            return bool(obj.is_hourly_allowed)
        return True

    def get_amenities(self, obj):
        if obj.amenities and len(obj.amenities) > 0:
            return obj.amenities
        if obj.room_type and getattr(obj.room_type, 'amenities', None):
            return obj.room_type.amenities or []
        return []

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

class RoomSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source='property.name', read_only=True, default='')
    room_type_details = RoomTypeSerializer(source='room_type', read_only=True)
    room_type_name = serializers.SerializerMethodField()
    capacity = serializers.IntegerField(source='room_type.max_occupancy', read_only=True, default=2)
    base_price = serializers.SerializerMethodField()
    hourly_rate = serializers.SerializerMethodField()
    is_hourly_allowed = serializers.SerializerMethodField()
    amenities = serializers.SerializerMethodField()
    current_guest_name = serializers.SerializerMethodField()
    active_booking_id = serializers.SerializerMethodField()
    housekeeping_status = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = [
            'id', 'tenant', 'property', 'property_name', 'room_type',
            'room_type_details', 'room_type_name', 'capacity', 'base_price', 'hourly_rate',
            'is_hourly_allowed', 'room_number', 'floor', 'status', 'housekeeping_status',
            'amenities', 'current_guest_name', 'active_booking_id',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']

    def to_internal_value(self, data):
        if isinstance(data, dict):
            data = data.copy()
            if 'property_id' in data and 'property' not in data and data['property_id']:
                data['property'] = data['property_id']
            if 'propertyId' in data and 'property' not in data and data['propertyId']:
                data['property'] = data['propertyId']
            if 'room_type_id' in data and 'room_type' not in data and data['room_type_id']:
                data['room_type'] = data['room_type_id']
            if 'roomTypeId' in data and 'room_type' not in data and data['roomTypeId']:
                data['room_type'] = data['roomTypeId']
            if 'roomNumber' in data and 'room_number' not in data:
                data['room_number'] = data['roomNumber']
        return super().to_internal_value(data)

    def get_room_type_name(self, obj) -> str:
        return obj.room_type.name if obj.room_type else "Standard Room"

    def get_base_price(self, obj) -> float:
        if obj.room_type and obj.room_type.base_price_per_night is not None:
            return float(obj.room_type.base_price_per_night)
        return 0.0

    def get_hourly_rate(self, obj) -> float:
        if getattr(obj, 'hourly_rate', None) is not None and float(obj.hourly_rate) > 0:
            return float(obj.hourly_rate)
        if obj.room_type and getattr(obj.room_type, 'hourly_rate', None) is not None:
            return float(obj.room_type.hourly_rate)
        return 0.0

    def get_is_hourly_allowed(self, obj):
        rate = self.get_hourly_rate(obj)
        if rate <= 0:
            return False
        if obj.room_type and getattr(obj.room_type, 'is_hourly_allowed', True) is False:
            return False
        if getattr(obj, 'is_hourly_allowed', None) is not None:
            return bool(obj.is_hourly_allowed)
        return True

    def get_amenities(self, obj):
        if obj.amenities and len(obj.amenities) > 0:
            return obj.amenities
        if obj.room_type and getattr(obj.room_type, 'amenities', None):
            return obj.room_type.amenities or []
        return []

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

RoomDetailSerializer = RoomSerializer

