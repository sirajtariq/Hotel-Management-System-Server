from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from apps.tenants.models import Tenant
from apps.properties.models import Property
from apps.rooms.models import RoomType, Room
from apps.bookings.models import Booking
from apps.bookings.services.booking_service import BookingService
from apps.restaurant.models import (
    Category, MenuItem, MenuItemVariation,
    DiningTable, RestaurantOrder, RestaurantOrderItem
)
from apps.restaurant.services.order_service import OrderCalculationService
from apps.restaurant.services.room_billing_service import RoomBillingService


class RestaurantTestCase(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Grand Palace Hotel",
            slug="grandpalace",
            subscription_status="PAID"
        )
        self.property = Property.objects.create(
            tenant=self.tenant,
            name="Main Tower",
            address="123 Boulevard"
        )
        self.room_type = RoomType.objects.create(
            tenant=self.tenant,
            property=self.property,
            name="Executive Suite",
            base_price_per_night=Decimal("10000.00")
        )
        self.room = Room.objects.create(
            tenant=self.tenant,
            property=self.property,
            room_type=self.room_type,
            room_number="101",
            status="AVAILABLE"
        )
        self.booking = BookingService.create_booking(
            tenant=self.tenant,
            room=self.room,
            guest_name="John Doe",
            guest_phone="+923001234567",
            check_in_date=date.today(),
            check_out_date=date.today() + timedelta(days=2),
            nightly_rate=Decimal("10000.00")
        )
        BookingService.check_in(self.booking)

        # Setup Category & Items
        self.category = Category.objects.create(
            tenant=self.tenant,
            name="Fast Food",
            display_order=1
        )
        self.menu_item = MenuItem.objects.create(
            tenant=self.tenant,
            category=self.category,
            name="Zinger Burger",
            base_price=Decimal("650.00"),
            has_variations=True
        )
        self.var_single = MenuItemVariation.objects.create(
            menu_item=self.menu_item,
            name="Single",
            price=Decimal("650.00")
        )
        self.var_double = MenuItemVariation.objects.create(
            menu_item=self.menu_item,
            name="Double Patty",
            price=Decimal("950.00")
        )

        self.table = DiningTable.objects.create(
            tenant=self.tenant,
            property=self.property,
            table_number="T-01",
            capacity=4,
            floor_or_section="Ground Floor"
        )

    def test_order_pricing_calculation(self):
        items_data = [
            {'unit_price': Decimal('650.00'), 'quantity': 2},
            {'unit_price': Decimal('950.00'), 'quantity': 1},
        ]
        calc = OrderCalculationService.calculate_order_pricing(
            items_data=items_data,
            discount_type='FLAT',
            discount_value=Decimal('100.00'),
            tax_percentage=Decimal('5.00')
        )
        # Subtotal: 650*2 + 950 = 1300 + 950 = 2250
        # Discount: 100
        # Taxable: 2150
        # Tax (5% of 2150): 107.50
        # Grand Total: 2257.50
        self.assertEqual(calc['subtotal'], Decimal('2250.00'))
        self.assertEqual(calc['discount_amount'], Decimal('100.00'))
        self.assertEqual(calc['tax_amount'], Decimal('107.50'))
        self.assertEqual(calc['grand_total'], Decimal('2257.50'))

    def test_dine_in_order_flow_and_table_status(self):
        items_payload = [{
            'menu_item': self.menu_item,
            'variation': self.var_double,
            'item_name': self.menu_item.name,
            'variation_name': self.var_double.name,
            'unit_price': Decimal('950.00'),
            'quantity': 2,
        }]
        order_data = {
            'order_type': 'DINE_IN',
            'table': self.table,
            'discount_type': 'PERCENTAGE',
            'discount_value': Decimal('10.00'),
            'tax_percentage': Decimal('5.00'),
        }

        order = OrderCalculationService.create_order(
            tenant=self.tenant,
            property_obj=self.property,
            order_data=order_data,
            items_data=items_payload
        )

        # Check table became OCCUPIED
        self.table.refresh_from_db()
        self.assertEqual(self.table.status, 'OCCUPIED')
        self.assertEqual(order.items.count(), 1)

        # Transition order to COMPLETED
        OrderCalculationService.update_order_status(order, 'COMPLETED')
        self.table.refresh_from_db()
        self.assertEqual(self.table.status, 'AVAILABLE')

    def test_room_service_folio_billing(self):
        items_payload = [{
            'menu_item': self.menu_item,
            'unit_price': Decimal('650.00'),
            'quantity': 1,
        }]
        order_data = {
            'order_type': 'ROOM_SERVICE',
            'booking': self.booking,
            'room_number': '101',
            'customer_name': 'John Doe',
        }
        order = OrderCalculationService.create_order(
            tenant=self.tenant,
            property_obj=self.property,
            order_data=order_data,
            items_data=items_payload
        )

        initial_booking_total = self.booking.total_amount
        RoomBillingService.post_to_room_folio(order, self.booking)

        self.booking.refresh_from_db()
        order.refresh_from_db()

        self.assertEqual(order.payment_status, 'BILLED_TO_ROOM')
        self.assertEqual(order.payment_method, 'ROOM_FOLIO')
        self.assertEqual(self.booking.total_amount, initial_booking_total + order.grand_total)
