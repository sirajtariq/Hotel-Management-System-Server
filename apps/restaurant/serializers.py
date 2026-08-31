from rest_framework import serializers
from apps.restaurant.models import (
    Category, MenuItem, MenuItemVariation,
    DiningTable, RestaurantOrder, RestaurantOrderItem
)
from apps.properties.models import Property
from apps.bookings.models import Booking


class CategorySerializer(serializers.ModelSerializer):
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'tenant', 'name', 'display_order', 'is_active', 'items_count']
        read_only_fields = ['id', 'tenant']

    def get_items_count(self, obj):
        return obj.items.filter(is_available=True).count()


class MenuItemVariationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItemVariation
        fields = ['id', 'menu_item', 'name', 'price', 'is_available']
        read_only_fields = ['id', 'menu_item']


class MenuItemSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')
    variations = MenuItemVariationSerializer(many=True, required=False)

    class Meta:
        model = MenuItem
        fields = [
            'id', 'tenant', 'category', 'category_name', 'name',
            'description', 'base_price', 'has_variations',
            'is_available', 'image_url', 'variations'
        ]
        read_only_fields = ['id', 'tenant']

    def create(self, validated_data):
        variations_data = validated_data.pop('variations', [])
        menu_item = MenuItem.objects.create(**validated_data)

        for v_data in variations_data:
            MenuItemVariation.objects.create(menu_item=menu_item, **v_data)

        if variations_data:
            menu_item.has_variations = True
            menu_item.save(update_fields=['has_variations'])

        return menu_item

    def update(self, instance, validated_data):
        variations_data = validated_data.pop('variations', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if variations_data is not None:
            # Replace variations
            instance.variations.all().delete()
            for v_data in variations_data:
                MenuItemVariation.objects.create(menu_item=instance, **v_data)
            instance.has_variations = len(variations_data) > 0

        instance.save()
        return instance


class DiningTableSerializer(serializers.ModelSerializer):
    property_name = serializers.ReadOnlyField(source='property.name')
    property = serializers.PrimaryKeyRelatedField(queryset=Property.objects.all(), required=False, allow_null=True)
    floor_or_section = serializers.CharField(required=False, allow_blank=True, default='Ground Floor')

    class Meta:
        model = DiningTable
        fields = [
            'id', 'tenant', 'property', 'property_name',
            'table_number', 'capacity', 'floor_or_section', 'status'
        ]
        read_only_fields = ['id', 'tenant']


class RestaurantOrderItemSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.ReadOnlyField(source='menu_item.name')

    class Meta:
        model = RestaurantOrderItem
        fields = [
            'id', 'order', 'menu_item', 'menu_item_name', 'variation',
            'item_name', 'variation_name', 'unit_price', 'quantity',
            'total_price', 'special_instructions', 'status'
        ]
        read_only_fields = ['id', 'order']


class RestaurantOrderListSerializer(serializers.ModelSerializer):
    table_number = serializers.ReadOnlyField(source='table.table_number')
    items_count = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = RestaurantOrder
        fields = [
            'id', 'order_number', 'order_type', 'table', 'table_number',
            'booking', 'room_number', 'customer_name', 'customer_phone',
            'status', 'payment_status', 'payment_method',
            'grand_total', 'items_count', 'created_by_name', 'created_at'
        ]

    def get_items_count(self, obj):
        return obj.items.count()

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return 'POS Staff'


class RestaurantOrderDetailSerializer(serializers.ModelSerializer):
    table_number = serializers.ReadOnlyField(source='table.table_number')
    property_name = serializers.ReadOnlyField(source='property.name')
    items = RestaurantOrderItemSerializer(many=True, read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = RestaurantOrder
        fields = [
            'id', 'tenant', 'property', 'property_name', 'order_number',
            'order_type', 'table', 'table_number', 'booking', 'room_number',
            'customer_name', 'customer_phone', 'status', 'payment_status',
            'payment_method', 'subtotal', 'discount_type', 'discount_value',
            'discount_amount', 'tax_percentage', 'tax_amount', 'grand_total',
            'notes', 'created_by_name', 'created_at', 'updated_at', 'items'
        ]
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return 'POS Staff'


class RestaurantOrderItemInputSerializer(serializers.Serializer):
    menu_item_id = serializers.IntegerField()
    variation_id = serializers.IntegerField(required=False, allow_null=True)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    quantity = serializers.IntegerField(min_value=1, default=1)
    special_instructions = serializers.CharField(required=False, allow_blank=True, default='')


class RestaurantOrderCreateSerializer(serializers.Serializer):
    property_id = serializers.IntegerField(required=False, allow_null=True)
    order_type = serializers.ChoiceField(choices=RestaurantOrder.ORDER_TYPE_CHOICES, default='DINE_IN')
    table_id = serializers.IntegerField(required=False, allow_null=True)
    booking_id = serializers.IntegerField(required=False, allow_null=True)
    room_number = serializers.CharField(required=False, allow_blank=True, default='')
    customer_name = serializers.CharField(required=False, allow_blank=True, default='')
    customer_phone = serializers.CharField(required=False, allow_blank=True, default='')
    payment_status = serializers.ChoiceField(choices=RestaurantOrder.PAYMENT_STATUS_CHOICES, default='UNPAID')
    payment_method = serializers.CharField(required=False, allow_blank=True, default='')
    discount_type = serializers.ChoiceField(choices=RestaurantOrder.DISCOUNT_TYPE_CHOICES, default='FLAT')
    discount_value = serializers.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    items = RestaurantOrderItemInputSerializer(many=True, min_length=1)
