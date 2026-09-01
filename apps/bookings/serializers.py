from decimal import Decimal
from rest_framework import serializers
from apps.bookings.models import Booking
from apps.accounts.models import PaymentAccount
from apps.expenses.models import AccountHead
from apps.rooms.serializers import RoomSerializer

class BookingListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source='property.name', read_only=True)
    room_number = serializers.CharField(source='room.room_number', read_only=True)
    room_type_name = serializers.CharField(source='room.room_type.name', read_only=True, default='Standard Executive Suite')
    invoice_number = serializers.SerializerMethodField()
    remaining_balance = serializers.SerializerMethodField()
    total_refunded = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

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
            'total_refunded',
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
    invoice_number = serializers.SerializerMethodField()
    property_name = serializers.CharField(source='property.name', read_only=True)
    property_address = serializers.CharField(source='property.address', read_only=True, default='')
    property_city = serializers.CharField(source='property.city', read_only=True, default='')
    property_phone = serializers.CharField(source='property.phone', read_only=True, default='')
    property_email = serializers.CharField(source='property.email', read_only=True, default='')
    property_data = serializers.SerializerMethodField()

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
    total_refunded = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal('0.00'))
    totalRefunded = serializers.DecimalField(source='total_refunded', max_digits=12, decimal_places=2, read_only=True)

    restaurant_orders = serializers.SerializerMethodField()
    restaurantOrders = serializers.SerializerMethodField()
    total_restaurant_charges = serializers.SerializerMethodField()
    totalRestaurantCharges = serializers.SerializerMethodField()

    room_stay_charges = serializers.SerializerMethodField()
    total_folio_bill = serializers.SerializerMethodField()
    gross_paid = serializers.SerializerMethodField()
    net_paid = serializers.SerializerMethodField()
    balance_due = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id',
            'property',
            'property_name',
            'property_address',
            'property_city',
            'property_phone',
            'property_email',
            'property_data',
            'room',
            'room_number',
            'room_type_name',
            'booking_type',
            'invoice_number',
            'guest_name',
            'guest_email',
            'guest_phone',
            'check_in',
            'check_out',
            'check_in_date',
            'check_out_date',
            'total_nights',
            'total_duration',
            'nightly_rate',
            'rate_applied',
            'subtotal_amount',
            'discount_type',
            'discount_value',
            'discount_amount',
            'tax_rate',
            'tax_amount',
            'total_amount',
            'paid_amount',
            'total_refunded',
            'totalRefunded',
            'remaining_balance',
            'payment_status',
            'status',
            'restaurant_orders',
            'restaurantOrders',
            'total_restaurant_charges',
            'totalRestaurantCharges',
            'room_stay_charges',
            'total_folio_bill',
            'gross_paid',
            'net_paid',
            'balance_due',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'tenant', 'property', 'total_nights',
            'payment_status', 'status',
            'created_at', 'updated_at'
        ]

    def get_property_data(self, obj):
        p = obj.property
        return {
            "name": p.name if p else "",
            "address": getattr(p, 'address', '') or "",
            "city": getattr(p, 'city', '') or "",
            "phone": getattr(p, 'phone', '') or "",
            "email": getattr(p, 'email', '') or "",
        }

    def get_restaurant_orders(self, obj):
        from apps.restaurant.serializers import RestaurantOrderListSerializer
        orders = obj.restaurant_orders.exclude(status='CANCELLED')
        return RestaurantOrderListSerializer(orders, many=True).data

    def get_restaurantOrders(self, obj):
        return self.get_restaurant_orders(obj)

    def get_total_restaurant_charges(self, obj):
        from django.db.models import Sum
        total = obj.restaurant_orders.exclude(status='CANCELLED').aggregate(t=Sum('grand_total'))['t']
        return Decimal(str(total or 0))

    def get_totalRestaurantCharges(self, obj):
        return self.get_total_restaurant_charges(obj)

    def get_room_stay_charges(self, obj):
        pos_total = self.get_total_restaurant_charges(obj)
        tot = obj.total_amount or Decimal('0.00')
        return max(Decimal('0.00'), tot - pos_total)

    def get_total_folio_bill(self, obj):
        return obj.total_amount or Decimal('0.00')

    def get_gross_paid(self, obj):
        paid = obj.paid_amount or Decimal('0.00')
        ref = obj.total_refunded or Decimal('0.00')
        return paid + ref

    def get_net_paid(self, obj):
        return obj.paid_amount or Decimal('0.00')

    def get_balance_due(self, obj):
        tot = obj.total_amount or Decimal('0.00')
        net_paid = obj.paid_amount or Decimal('0.00')
        return max(Decimal('0.00'), tot - net_paid)

    def to_internal_value(self, data):
        if isinstance(data, dict):
            data = data.copy()
            if 'propertyId' in data and 'property' not in data:
                data['property'] = data['propertyId']
            if 'property_id' in data and 'property' not in data:
                data['property'] = data['property_id']
            if 'roomId' in data and 'room' not in data:
                data['room'] = data['roomId']
            if 'room_id' in data and 'room' not in data:
                data['room'] = data['room_id']
            if 'guestName' in data and 'guest_name' not in data:
                data['guest_name'] = data['guestName']
            if 'guestPhone' in data and 'guest_phone' not in data:
                data['guest_phone'] = data['guestPhone']
            if 'guestEmail' in data and 'guest_email' not in data:
                data['guest_email'] = data['guestEmail']
            if 'bookingType' in data and 'booking_type' not in data:
                data['booking_type'] = data['bookingType']
            if 'checkIn' in data and 'check_in' not in data:
                data['check_in'] = data['checkIn']
            if 'checkOut' in data and 'check_out' not in data:
                data['check_out'] = data['checkOut']
            if 'rateApplied' in data and 'rate_applied' not in data:
                data['rate_applied'] = data['rateApplied']
            if 'nightlyRate' in data and 'rate_applied' not in data:
                data['rate_applied'] = data['nightlyRate']
            if 'discountType' in data and 'discount_type' not in data:
                data['discount_type'] = data['discountType']
            if 'discountValue' in data and 'discount_value' not in data:
                data['discount_value'] = data['discountValue']
            if 'taxRate' in data and 'tax_rate' not in data:
                data['tax_rate'] = data['taxRate']
            if 'totalAmount' in data and 'total_amount' not in data:
                data['total_amount'] = data['totalAmount']
            if 'paidAmount' in data and 'paid_amount' not in data:
                data['paid_amount'] = data['paidAmount']
            if 'initialPayment' in data and 'paid_amount' not in data:
                data['paid_amount'] = data['initialPayment']
            if 'totalDuration' in data and 'total_duration' not in data:
                data['total_duration'] = data['totalDuration']
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


class BookingRefundSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'), required=True)
    payment_account = serializers.PrimaryKeyRelatedField(
        queryset=PaymentAccount.objects.all(),
        required=True,
        error_messages={
            'required': 'Payment Account is strictly required to process a refund.',
            'does_not_exist': 'Selected payment account does not exist.'
        }
    )
    account_head = serializers.PrimaryKeyRelatedField(
        queryset=AccountHead.objects.all(),
        required=True,
        error_messages={
            'required': 'Account Head is strictly required to categorize this refund in financial records.',
            'does_not_exist': 'Selected account head does not exist.'
        }
    )
    cancellation_fee = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.00'), default=Decimal('0.00'), required=False)
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        booking = self.context.get('booking')
        tenant = None
        if request and getattr(request, 'user', None) and getattr(request.user, 'tenant', None):
            tenant = request.user.tenant
        elif booking and getattr(booking, 'tenant', None):
            tenant = booking.tenant

        if tenant:
            self.fields['payment_account'].queryset = PaymentAccount.objects.filter(tenant=tenant)
            self.fields['account_head'].queryset = AccountHead.objects.filter(tenant=tenant)

    def to_internal_value(self, data):
        if isinstance(data, dict):
            data = data.copy()
            if 'payment_account' not in data and 'paymentAccountId' in data:
                data['payment_account'] = data['paymentAccountId']
            if 'account_head' not in data and 'accountHeadId' in data:
                data['account_head'] = data['accountHeadId']
        return super().to_internal_value(data)

    def validate_amount(self, value):
        booking = self.context.get('booking')
        if not booking:
            raise serializers.ValidationError("Booking context missing.")
        
        # Calculate max refundable balance
        paid = Decimal(str(getattr(booking, 'paid_amount', 0) or 0))
        refunded = Decimal(str(getattr(booking, 'total_refunded', 0) or 0))
        max_refundable = paid - refunded
        if value > max_refundable:
            raise serializers.ValidationError(
                f"Refund amount (PKR {value}) exceeds maximum refundable balance (PKR {max_refundable})."
            )
        return value


class RecordPaymentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))
    payment_method = serializers.CharField(required=False, allow_blank=True, default='cash')
    payment_account_id = serializers.IntegerField(required=False, allow_null=True)
    account_id = serializers.IntegerField(required=False, allow_null=True)

    def to_internal_value(self, data):
        if isinstance(data, dict):
            data = data.copy()
            if 'paymentAccountId' in data and 'payment_account_id' not in data:
                data['payment_account_id'] = data['paymentAccountId']
            if 'accountId' in data and 'account_id' not in data:
                data['account_id'] = data['accountId']
            if 'paymentMethod' in data and 'payment_method' not in data:
                data['payment_method'] = data['paymentMethod']
        return super().to_internal_value(data)

