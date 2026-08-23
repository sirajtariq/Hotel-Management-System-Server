from decimal import Decimal
from django.db import transaction, IntegrityError
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied

from core.permissions import HasModulePermission
from apps.properties.models import Property
from apps.bookings.models import Booking
from apps.restaurant.models import (
    Category, MenuItem, MenuItemVariation,
    DiningTable, RestaurantOrder, RestaurantOrderItem
)
from apps.restaurant.serializers import (
    CategorySerializer, MenuItemSerializer, MenuItemVariationSerializer,
    DiningTableSerializer, RestaurantOrderListSerializer,
    RestaurantOrderDetailSerializer, RestaurantOrderCreateSerializer
)
from apps.restaurant.services.order_service import OrderCalculationService
from apps.restaurant.services.room_billing_service import RoomBillingService


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [HasModulePermission]
    required_permission = 'restaurant:menu_manage'

    def get_queryset(self):
        tenant = getattr(self.request.user, 'tenant', None)
        if not tenant and not self.request.user.is_superuser:
            return Category.objects.none()
        if self.request.user.is_superuser and not tenant:
            return Category.objects.all()
        return Category.objects.filter(tenant=tenant)

    def perform_create(self, serializer):
        tenant = getattr(self.request.user, 'tenant', None)
        if not tenant:
            raise ValidationError({'tenant': 'User is not assigned to any tenant.'})
        serializer.save(tenant=tenant)


class MenuItemViewSet(viewsets.ModelViewSet):
    serializer_class = MenuItemSerializer
    permission_classes = [HasModulePermission]

    action_permissions = {
        'list': 'restaurant:pos',
        'retrieve': 'restaurant:pos',
        'create': 'restaurant:menu_manage',
        'update': 'restaurant:menu_manage',
        'partial_update': 'restaurant:menu_manage',
        'destroy': 'restaurant:menu_manage',
        'toggle_availability': 'restaurant:menu_manage',
    }

    def get_queryset(self):
        tenant = getattr(self.request.user, 'tenant', None)
        if not tenant and not self.request.user.is_superuser:
            qs = MenuItem.objects.none()
        elif self.request.user.is_superuser and not tenant:
            qs = MenuItem.objects.all()
        else:
            qs = MenuItem.objects.filter(tenant=tenant)

        category_id = self.request.query_params.get('category_id')
        if category_id:
            qs = qs.filter(category_id=category_id)

        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(name__icontains=search)

        available_only = self.request.query_params.get('available_only')
        if available_only == 'true':
            qs = qs.filter(is_available=True)

        return qs.prefetch_related('variations', 'category')

    def perform_create(self, serializer):
        tenant = getattr(self.request.user, 'tenant', None)
        if not tenant:
            raise ValidationError({'tenant': 'User is not assigned to any tenant.'})
        serializer.save(tenant=tenant)

    @action(detail=True, methods=['post'])
    def toggle_availability(self, request, pk=None):
        item = self.get_object()
        item.is_available = not item.is_available
        item.save(update_fields=['is_available'])
        return Response({'id': item.id, 'name': item.name, 'is_available': item.is_available})


class DiningTableViewSet(viewsets.ModelViewSet):
    serializer_class = DiningTableSerializer
    permission_classes = [HasModulePermission]

    action_permissions = {
        'list': 'restaurant:tables_manage',
        'retrieve': 'restaurant:tables_manage',
        'create': 'restaurant:tables_manage',
        'update': 'restaurant:tables_manage',
        'partial_update': 'restaurant:tables_manage',
        'destroy': 'restaurant:tables_manage',
    }

    def get_queryset(self):
        tenant = getattr(self.request.user, 'tenant', None)
        if not tenant and not self.request.user.is_superuser:
            qs = DiningTable.objects.none()
        elif self.request.user.is_superuser and not tenant:
            qs = DiningTable.objects.all()
        else:
            qs = DiningTable.objects.filter(tenant=tenant)

        property_id = self.request.query_params.get('property_id')
        if property_id:
            qs = qs.filter(property_id=property_id)

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        return qs

    def perform_create(self, serializer):
        tenant = getattr(self.request.user, 'tenant', None)
        if not tenant:
            raise ValidationError({'tenant': 'User is not assigned to any tenant.'})

        prop = serializer.validated_data.get('property')
        if not prop or prop.tenant != tenant:
            prop = Property.objects.filter(tenant=tenant).first()
            if not prop:
                raise ValidationError({'property': 'No property exists for this tenant. Please create a property first.'})

        tbl_num = serializer.validated_data.get('table_number', '').strip()
        if DiningTable.objects.filter(tenant=tenant, property=prop, table_number=tbl_num).exists():
            raise ValidationError({'table_number': f"Table number '{tbl_num}' already exists for this property."})

        floor_sec = serializer.validated_data.get('floor_or_section') or 'Ground Floor'
        try:
            serializer.save(tenant=tenant, property=prop, floor_or_section=floor_sec)
        except IntegrityError:
            raise ValidationError({'table_number': f"Table number '{tbl_num}' already exists for this property."})

    def perform_update(self, serializer):
        tbl = self.get_object()
        tenant = tbl.tenant
        prop = serializer.validated_data.get('property', tbl.property)
        tbl_num = serializer.validated_data.get('table_number', tbl.table_number).strip()

        if DiningTable.objects.filter(tenant=tenant, property=prop, table_number=tbl_num).exclude(id=tbl.id).exists():
            raise ValidationError({'table_number': f"Table number '{tbl_num}' already exists for this property."})

        try:
            serializer.save(property=prop)
        except IntegrityError:
            raise ValidationError({'table_number': f"Table number '{tbl_num}' already exists for this property."})


class RestaurantOrderViewSet(viewsets.ModelViewSet):
    permission_classes = [HasModulePermission]

    action_permissions = {
        'list': 'restaurant:orders_view',
        'retrieve': 'restaurant:orders_view',
        'create': 'restaurant:pos',
        'update': 'restaurant:pos',
        'partial_update': 'restaurant:pos',
        'destroy': 'restaurant:orders_view',
        'update_kitchen_status': 'restaurant:kitchen',
        'settle_payment': 'restaurant:pos',
        'receipt_data': 'restaurant:orders_view',
    }

    def get_serializer_class(self):
        if self.action == 'list':
            return RestaurantOrderListSerializer
        elif self.action == 'create':
            return RestaurantOrderCreateSerializer
        return RestaurantOrderDetailSerializer

    def get_queryset(self):
        tenant = getattr(self.request.user, 'tenant', None)
        if not tenant and not self.request.user.is_superuser:
            qs = RestaurantOrder.objects.none()
        elif self.request.user.is_superuser and not tenant:
            qs = RestaurantOrder.objects.all()
        else:
            qs = RestaurantOrder.objects.filter(tenant=tenant)

        property_id = self.request.query_params.get('property_id')
        if property_id:
            qs = qs.filter(property_id=property_id)

        order_status = self.request.query_params.get('status')
        if order_status:
            qs = qs.filter(status=order_status)

        order_type = self.request.query_params.get('order_type')
        if order_type:
            qs = qs.filter(order_type=order_type)

        payment_status = self.request.query_params.get('payment_status')
        if payment_status:
            qs = qs.filter(payment_status=payment_status)

        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                order_number__icontains=search
            ) | qs.filter(
                customer_name__icontains=search
            ) | qs.filter(
                room_number__icontains=search
            )

        active_kitchen = self.request.query_params.get('active_kitchen')
        if active_kitchen == 'true':
            qs = qs.filter(status__in=['PENDING', 'PREPARING', 'READY'])

        date_param = self.request.query_params.get('date')
        if date_param:
            qs = qs.filter(created_at__date=date_param)

        return qs.select_related('table', 'booking', 'property', 'created_by').prefetch_related('items')

    def create(self, request, *args, **kwargs):
        serializer = RestaurantOrderCreateSerializer(data=request.data)
        serializer.is_validate_or_raise = True
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        tenant = getattr(request.user, 'tenant', None)
        if not tenant:
            raise ValidationError({'tenant': 'User is not assigned to any tenant.'})

        property_id = data.get('property_id')
        property_obj = None
        if property_id:
            property_obj = Property.objects.filter(id=property_id, tenant=tenant).first()
        if not property_obj:
            property_obj = Property.objects.filter(tenant=tenant).first()
        if not property_obj:
            raise ValidationError({'property_id': 'No property exists for this tenant. Please create a property first.'})

        table_obj = None
        if data.get('table_id'):
            try:
                table_obj = DiningTable.objects.get(id=data['table_id'], tenant=tenant)
            except DiningTable.DoesNotExist:
                raise ValidationError({'table_id': 'Invalid dining table.'})

        booking_obj = None
        if data.get('booking_id'):
            try:
                booking_obj = Booking.objects.get(id=data['booking_id'], tenant=tenant)
            except Booking.DoesNotExist:
                raise ValidationError({'booking_id': 'Invalid booking.'})

        # Process item models
        items_payload = []
        for item_data in data['items']:
            try:
                m_item = MenuItem.objects.get(id=item_data['menu_item_id'], tenant=tenant)
            except MenuItem.DoesNotExist:
                raise ValidationError({'menu_item_id': f"Invalid menu item ID {item_data['menu_item_id']}."})

            variation_obj = None
            var_name = ''
            if item_data.get('variation_id'):
                try:
                    variation_obj = MenuItemVariation.objects.get(id=item_data['variation_id'], menu_item=m_item)
                    var_name = variation_obj.name
                except MenuItemVariation.DoesNotExist:
                    raise ValidationError({'variation_id': f"Invalid variation ID {item_data['variation_id']}."})

            items_payload.append({
                'menu_item': m_item,
                'variation': variation_obj,
                'item_name': m_item.name,
                'variation_name': var_name,
                'unit_price': item_data['unit_price'],
                'quantity': item_data['quantity'],
                'special_instructions': item_data.get('special_instructions', ''),
            })

        order_data = {
            'order_type': data['order_type'],
            'table': table_obj,
            'booking': booking_obj,
            'room_number': data.get('room_number', ''),
            'customer_name': data.get('customer_name', ''),
            'customer_phone': data.get('customer_phone', ''),
            'payment_status': data.get('payment_status', 'UNPAID'),
            'payment_method': data.get('payment_method', ''),
            'discount_type': data.get('discount_type', 'FLAT'),
            'discount_value': data.get('discount_value', Decimal('0.00')),
            'tax_percentage': data.get('tax_percentage', Decimal('0.00')),
            'notes': data.get('notes', ''),
        }

        order = OrderCalculationService.create_order(
            tenant=tenant,
            property_obj=property_obj,
            order_data=order_data,
            items_data=items_payload,
            created_by=request.user
        )

        # Handle room folio billing if payment status is BILLED_TO_ROOM at creation
        if order.payment_status == 'BILLED_TO_ROOM' and booking_obj:
            RoomBillingService.post_to_room_folio(order, booking_obj)

        out_serializer = RestaurantOrderDetailSerializer(order)
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def update_kitchen_status(self, request, pk=None):
        order = self.get_object()
        new_status = request.data.get('status')
        item_id = request.data.get('item_id')

        valid_statuses = ['PENDING', 'PREPARING', 'READY', 'SERVED', 'COMPLETED', 'CANCELLED']
        if new_status not in valid_statuses:
            raise ValidationError({'status': f"Invalid status. Must be one of {valid_statuses}."})

        if item_id:
            try:
                item = order.items.get(id=item_id)
                item.status = new_status
                item.save(update_fields=['status'])
            except RestaurantOrderItem.DoesNotExist:
                raise ValidationError({'item_id': 'Order item not found.'})
        else:
            OrderCalculationService.update_order_status(order, new_status)

        out_serializer = RestaurantOrderDetailSerializer(order)
        return Response(out_serializer.data)

    @action(detail=True, methods=['post'])
    def settle_payment(self, request, pk=None):
        order = self.get_object()
        payment_status_choice = request.data.get('payment_status', 'PAID')
        payment_method = request.data.get('payment_method', 'CASH')
        booking_id = request.data.get('booking_id')

        if payment_status_choice == 'BILLED_TO_ROOM':
            booking_obj = None
            if booking_id:
                try:
                    booking_obj = Booking.objects.get(id=booking_id, tenant=order.tenant)
                except Booking.DoesNotExist:
                    raise ValidationError({'booking_id': 'Specified booking not found.'})
            RoomBillingService.post_to_room_folio(order, booking_obj)
        else:
            order.payment_status = 'PAID'
            order.payment_method = payment_method
            order.save(update_fields=['payment_status', 'payment_method', 'updated_at'])
            if order.status in ['PENDING', 'PREPARING', 'READY', 'SERVED']:
                OrderCalculationService.update_order_status(order, 'COMPLETED')

        out_serializer = RestaurantOrderDetailSerializer(order)
        return Response(out_serializer.data)

    @action(detail=True, methods=['get'])
    def receipt_data(self, request, pk=None):
        order = self.get_object()
        tenant = order.tenant
        prop = order.property

        items_list = []
        for item in order.items.all():
            items_list.append({
                'id': item.id,
                'item_name': item.item_name,
                'variation_name': item.variation_name,
                'unit_price': str(item.unit_price),
                'quantity': item.quantity,
                'total_price': str(item.total_price),
                'special_instructions': item.special_instructions,
                'status': item.status,
            })

        data = {
            'header': {
                'tenant_name': tenant.name,
                'property_name': prop.name,
                'property_address': prop.address or '',
                'property_phone': prop.phone or '',
            },
            'order': {
                'id': order.id,
                'order_number': order.order_number,
                'order_type': order.get_order_type_display(),
                'order_type_code': order.order_type,
                'table_number': order.table.table_number if order.table else None,
                'room_number': order.room_number,
                'customer_name': order.customer_name,
                'customer_phone': order.customer_phone,
                'status': order.get_status_display(),
                'payment_status': order.get_payment_status_display(),
                'payment_method': order.payment_method,
                'created_at': order.created_at.strftime('%d-%b-%Y %I:%M %p'),
                'created_by': order.created_by.get_full_name() if order.created_by else 'POS Staff',
            },
            'financials': {
                'subtotal': str(order.subtotal),
                'discount_type': order.discount_type,
                'discount_value': str(order.discount_value),
                'discount_amount': str(order.discount_amount),
                'tax_percentage': str(order.tax_percentage),
                'tax_amount': str(order.tax_amount),
                'grand_total': str(order.grand_total),
            },
            'items': items_list,
            'notes': order.notes,
        }
        return Response(data)
