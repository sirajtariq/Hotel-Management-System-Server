from decimal import Decimal
import uuid
from django.utils import timezone
from django.db import transaction
from rest_framework.exceptions import ValidationError
from apps.restaurant.models import RestaurantOrder, RestaurantOrderItem, DiningTable


class OrderCalculationService:
    @staticmethod
    def calculate_order_pricing(
        items_data: list,
        discount_type: str = 'FLAT',
        discount_value: Decimal = Decimal('0.00'),
        tax_percentage: Decimal = Decimal('0.00')
    ) -> dict:
        """
        Calculates item totals, subtotal, discount amount, taxable amount, tax amount, and grand total.
        items_data format: [{'unit_price': Decimal, 'quantity': int}, ...]
        """
        subtotal = Decimal('0.00')
        processed_items = []

        for item in items_data:
            u_price = Decimal(str(item.get('unit_price', '0.00')))
            qty = int(item.get('quantity', 1))
            total_p = round(u_price * qty, 2)
            subtotal += total_p
            processed_items.append({
                **item,
                'unit_price': u_price,
                'quantity': qty,
                'total_price': total_p,
            })

        disc_val = Decimal(str(discount_value or '0.00'))
        if discount_type == 'PERCENTAGE':
            discount_amount = round((subtotal * disc_val) / Decimal('100.00'), 2)
        else:
            discount_amount = min(disc_val, subtotal)

        taxable_amount = max(Decimal('0.00'), subtotal - discount_amount)
        tax_pct = Decimal(str(tax_percentage or '0.00'))
        tax_amount = round((taxable_amount * tax_pct) / Decimal('100.00'), 2)
        grand_total = taxable_amount + tax_amount

        return {
            'subtotal': subtotal,
            'discount_type': discount_type,
            'discount_value': disc_val,
            'discount_amount': discount_amount,
            'tax_percentage': tax_pct,
            'tax_amount': tax_amount,
            'grand_total': grand_total,
            'items': processed_items,
        }

    @staticmethod
    def generate_order_number(tenant_id: int) -> str:
        """
        Generates a unique order number string format: ORD-YYYYMMDD-XXXX
        """
        today_str = timezone.now().strftime('%Y%m%d')
        unique_suffix = str(uuid.uuid4().hex[:6]).upper()
        return f"ORD-{today_str}-{unique_suffix}"

    @classmethod
    @transaction.atomic
    def create_order(cls, tenant, property_obj, order_data: dict, items_data: list, created_by=None) -> RestaurantOrder:
        """
        Creates a new restaurant order atomically and handles table status automation.
        """
        pricing = cls.calculate_order_pricing(
            items_data=items_data,
            discount_type=order_data.get('discount_type', 'FLAT'),
            discount_value=order_data.get('discount_value', Decimal('0.00')),
            tax_percentage=order_data.get('tax_percentage', Decimal('0.00'))
        )

        table = order_data.get('table')
        order_type = order_data.get('order_type', 'DINE_IN')

        if order_type == 'DINE_IN' and table:
            table.status = 'OCCUPIED'
            table.save(update_fields=['status'])

        order_number = cls.generate_order_number(tenant.id)

        order = RestaurantOrder.objects.create(
            tenant=tenant,
            property=property_obj,
            order_number=order_number,
            order_type=order_type,
            table=table,
            booking=order_data.get('booking'),
            room_number=order_data.get('room_number', ''),
            customer_name=order_data.get('customer_name', ''),
            customer_phone=order_data.get('customer_phone', ''),
            status='PENDING',
            payment_status=order_data.get('payment_status', 'UNPAID'),
            payment_method=order_data.get('payment_method', ''),
            subtotal=pricing['subtotal'],
            discount_type=pricing['discount_type'],
            discount_value=pricing['discount_value'],
            discount_amount=pricing['discount_amount'],
            tax_percentage=pricing['tax_percentage'],
            tax_amount=pricing['tax_amount'],
            grand_total=pricing['grand_total'],
            notes=order_data.get('notes', ''),
            created_by=created_by
        )

        for item_info in pricing['items']:
            RestaurantOrderItem.objects.create(
                order=order,
                menu_item=item_info['menu_item'],
                variation=item_info.get('variation'),
                item_name=item_info.get('item_name', item_info['menu_item'].name),
                variation_name=item_info.get('variation_name', ''),
                unit_price=item_info['unit_price'],
                quantity=item_info['quantity'],
                total_price=item_info['total_price'],
                special_instructions=item_info.get('special_instructions', ''),
                status='PENDING'
            )

        return order

    @classmethod
    @transaction.atomic
    def update_order_status(cls, order: RestaurantOrder, new_status: str) -> RestaurantOrder:
        """
        Updates order status and manages table automation on completion/cancellation.
        """
        old_status = order.status
        order.status = new_status
        order.save(update_fields=['updated_at', 'status'])

        # Update items status as well if order transitions
        if new_status == 'PREPARING':
            order.items.filter(status='PENDING').update(status='PREPARING')
        elif new_status == 'READY':
            order.items.filter(status__in=['PENDING', 'PREPARING']).update(status='READY')

        # Table release automation
        if order.order_type == 'DINE_IN' and order.table and new_status in ['COMPLETED', 'CANCELLED']:
            cls.sync_table_status(order.table)

        return order

    @staticmethod
    def sync_table_status(table: DiningTable):
        """
        Frees table to AVAILABLE if no other active orders exist on that table.
        """
        active_orders = RestaurantOrder.objects.filter(
            table=table,
            status__in=['PENDING', 'PREPARING', 'READY', 'SERVED']
        ).exists()

        if not active_orders:
            table.status = 'AVAILABLE'
            table.save(update_fields=['status'])
