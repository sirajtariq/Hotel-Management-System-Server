from decimal import Decimal
from rest_framework import serializers
from apps.bookings.models import Booking
from apps.rooms.serializers import RoomSerializer

class BookingListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source='property.name', read_only=True)
    room_number = serializers.CharField(source='room.room_number', read_only=True)
    room_type_name = serializers.CharField(source='room.room_type.name', read_only=True, default='Standard Executive Suite')
    invoice_number = serializers.SerializerMethodField()
    remaining_balance = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id',
            'invoice_number',
            'property_name',
            'room_number',
            'room_type_name',
            'guest_name',
            'guest_phone',
            'guest_email',
            'booking_type',
            'check_in',
            'check_out',
            'check_in_date',
            'check_out_date',
            'total_duration',
            'total_amount',
            'paid_amount',
            'remaining_balance',
            'payment_status',
            'status',
            'created_at',
        ]

    def get_invoice_number(self, obj) -> str:
        tenant_code = getattr(obj.tenant, 'code', '') or 'RS'
        return f"INV-{tenant_code.upper()}-2026-{obj.id:04d}"

    def get_remaining_balance(self, obj) -> Decimal:
        return max(Decimal('0.00'), obj.total_amount - obj.paid_amount)


class BookingDetailSerializer(serializers.ModelSerializer):
    room_details = RoomSerializer(source='room', read_only=True)
    invoice_number = serializers.SerializerMethodField()
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    property_name = serializers.CharField(source='property.name', read_only=True)
    property_address = serializers.CharField(source='property.address', read_only=True)
    property_city = serializers.CharField(source='property.city', read_only=True)
    room_number = serializers.CharField(source='room.room_number', read_only=True)
    room_type_name = serializers.SerializerMethodField()
    remaining_balance = serializers.SerializerMethodField()

    check_in = serializers.DateTimeField(required=False, allow_null=True)
    check_out = serializers.DateTimeField(required=False, allow_null=True)
    check_in_date = serializers.DateField(required=False, allow_null=True)
    check_out_date = serializers.DateField(required=False, allow_null=True)
    discount_type = serializers.CharField(required=False, default='FLAT')
    discount_value = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=Decimal('0.00'))
    discount_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal('0.00'))
    tax_rate = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default=Decimal('0.00'))
    tax_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal('0.00'))
    subtotal_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal('0.00'))
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal('0.00'))

    class Meta:
        model = Booking
        fields = [
            'id', 'tenant', 'tenant_name', 'property', 'property_name', 'property_address', 'property_city',
            'room', 'room_number', 'room_type_name', 'room_details',
            'booking_type', 'invoice_number', 'guest_name', 'guest_email', 'guest_phone',
            'check_in', 'check_out', 'check_in_date', 'check_out_date', 'total_nights', 'total_duration',
            'nightly_rate', 'rate_applied', 'subtotal_amount', 'discount_type', 'discount_value', 'discount_amount',
            'tax_rate', 'tax_amount', 'total_amount', 'paid_amount', 'remaining_balance',
            'payment_status', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'tenant', 'property', 'total_nights',
            'payment_status', 'status',
            'created_at', 'updated_at'
        ]

    def to_internal_value(self, data):
        if isinstance(data, dict):
            data = data.copy()
            if 'room_id' in data and 'room' not in data:
                data['room'] = data['room_id']
            if 'property_id' in data and 'property' not in data:
                data['property'] = data['property_id']
        return super().to_internal_value(data)

    def get_invoice_number(self, obj) -> str:
        tenant_code = getattr(obj.tenant, 'code', '') or 'RS'
        return f"INV-{tenant_code.upper()}-2026-{obj.id:04d}"

    def get_room_type_name(self, obj) -> str:
        if obj.room and getattr(obj.room, 'room_type', None):
            return obj.room.room_type.name
        return "Standard Executive Suite"

    def get_remaining_balance(self, obj) -> Decimal:
        return max(Decimal('0.00'), obj.total_amount - obj.paid_amount)


BookingSerializer = BookingDetailSerializer

class RecordPaymentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))
