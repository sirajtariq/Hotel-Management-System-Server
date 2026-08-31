from rest_framework import serializers
from apps.rooms.models import Room, RoomType
from apps.properties.models import Property

class RoomTypeSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source='property.name', read_only=True)
    property = serializers.PrimaryKeyRelatedField(
        queryset=Property.objects.all(),
        required=True
    )
    property_id = serializers.PrimaryKeyRelatedField(
        queryset=Property.objects.all(), source='property', write_only=True, required=False
    )
    base_price_per_night = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
    base_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, write_only=True
    )
    basePrice = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, write_only=True
    )
    code = serializers.CharField(required=False, write_only=True, allow_blank=True)
    amenities = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list
    )

    class Meta:
        model = RoomType
        fields = [
            'id',
            'property',
            'property_id',
            'property_name',
            'name',
            'code',
            'description',
            'max_occupancy',
            'base_price_per_night',
            'base_price',
            'basePrice',
            'is_hourly_allowed',
            'hourly_rate',
            'amenities',
            'created_at',
        ]
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']
        validators = []

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

    def validate(self, attrs):
        attrs.pop('code', None)

        if 'basePrice' in attrs and 'base_price_per_night' not in attrs:
            attrs['base_price_per_night'] = attrs.pop('basePrice')
        elif 'basePrice' in attrs:
            attrs.pop('basePrice')

        if 'base_price' in attrs and 'base_price_per_night' not in attrs:
            attrs['base_price_per_night'] = attrs.pop('base_price')
        elif 'base_price' in attrs:
            attrs.pop('base_price')

        if not attrs.get('base_price_per_night') and not self.instance:
            raise serializers.ValidationError({"base_price_per_night": "Base price per night is required."})

        if 'amenities' not in attrs:
            attrs['amenities'] = []

        prop = attrs.get('property')
        name = attrs.get('name')
        if prop and name:
            qs = RoomType.objects.filter(property=prop, name=name)
            if self.instance:
                qs = qs.exclude(id=self.instance.id)
            if qs.exists():
                raise serializers.ValidationError({"name": "Room type with this name already exists for this property."})

        return super().validate(attrs)

    def create(self, validated_data):
        return super().create(validated_data)

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
    room_type_name = serializers.CharField(source='room_type.name', read_only=True, default='Standard Room')
    max_occupancy = serializers.IntegerField(source='room_type.max_occupancy', read_only=True, default=2)
    capacity = serializers.IntegerField(source='room_type.max_occupancy', read_only=True, default=2)
    base_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    hourly_rate = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    is_hourly_allowed = serializers.BooleanField(required=False, allow_null=True)
    amenities = serializers.ListField(child=serializers.CharField(max_length=100), required=False, default=list)
    current_guest_name = serializers.SerializerMethodField()
    active_booking_id = serializers.SerializerMethodField()
    housekeeping_status = serializers.CharField(required=False, default='CLEAN')

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
        read_only_fields = ['id', 'tenant']

    def to_internal_value(self, data):
        if isinstance(data, dict):
            data = data.copy()
            if 'propertyId' in data and 'property' not in data:
                data['property'] = data['propertyId']
            if 'property_id' in data and 'property' not in data:
                data['property'] = data['property_id']
            if 'roomType' in data and 'room_type' not in data:
                data['room_type'] = data['roomType']
            if 'roomTypeId' in data and 'room_type' not in data:
                data['room_type'] = data['roomTypeId']
            if 'room_type_id' in data and 'room_type' not in data:
                data['room_type'] = data['room_type_id']
            if 'roomNumber' in data and 'room_number' not in data:
                data['room_number'] = data['roomNumber']
            if 'basePrice' in data and 'base_price' not in data:
                data['base_price'] = data['basePrice']
            if 'basePricePerNight' in data and 'base_price' not in data:
                data['base_price'] = data['basePricePerNight']
            if 'base_price_per_night' in data and 'base_price' not in data:
                data['base_price'] = data['base_price_per_night']
            if 'hourlyRate' in data and 'hourly_rate' not in data:
                data['hourly_rate'] = data['hourlyRate']
            if 'isHourlyAllowed' in data and 'is_hourly_allowed' not in data:
                data['is_hourly_allowed'] = data['isHourlyAllowed']
            if 'housekeepingStatus' in data and 'housekeeping_status' not in data:
                data['housekeeping_status'] = data['housekeepingStatus']
        return super().to_internal_value(data)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['base_price'] = self.get_base_price(instance)
        ret['hourly_rate'] = self.get_hourly_rate(instance)
        ret['is_hourly_allowed'] = self.get_is_hourly_allowed(instance)
        ret['amenities'] = self.get_amenities(instance)
        return ret

    def get_base_price(self, obj) -> float:
        if getattr(obj, 'base_price', None) is not None and float(obj.base_price) > 0:
            return float(obj.base_price)
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

