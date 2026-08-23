from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from rest_framework.exceptions import ValidationError
from apps.tenants.services.tenant_service import TenantService
from apps.properties.services.property_service import PropertyService
from apps.rooms.services.room_service import RoomService
from apps.bookings.services.booking_service import BookingService

class BookingTestCase(TestCase):
    def setUp(self):
        self.tenant = TenantService.create_tenant(name="Palace Suites")
        self.property = PropertyService.create_property(
            tenant=self.tenant,
            name="Palace Main",
            address="456 Beach Blvd",
            city="Miami"
        )
        self.room_type = RoomService.create_room_type(
            tenant=self.tenant,
            property_obj=self.property,
            name="Executive Suite",
            base_price_per_night=Decimal('200.00')
        )
        self.room = RoomService.create_room(
            tenant=self.tenant,
            property_obj=self.property,
            room_type=self.room_type,
            room_number="101"
        )

    def test_booking_creation_and_ssot_calculation(self):
        check_in = date.today()
        check_out = check_in + timedelta(days=3)

        booking = BookingService.create_booking(
            tenant=self.tenant,
            room=self.room,
            guest_name="John Doe",
            guest_phone="+15550199",
            check_in_date=check_in,
            check_out_date=check_out,
            paid_amount=Decimal('300.00')  # Partial payment of 300 out of 600
        )

        self.assertEqual(booking.total_nights, 3)
        self.assertEqual(booking.nightly_rate, Decimal('200.00'))
        self.assertEqual(booking.total_amount, Decimal('600.00'))
        self.assertEqual(booking.paid_amount, Decimal('300.00'))
        self.assertEqual(booking.payment_status, 'PARTIAL')

    def test_booking_payment_record(self):
        check_in = date.today()
        check_out = check_in + timedelta(days=2)
        booking = BookingService.create_booking(
            tenant=self.tenant,
            room=self.room,
            guest_name="Jane Smith",
            guest_phone="+15550188",
            check_in_date=check_in,
            check_out_date=check_out,
            paid_amount=Decimal('0.00')
        )
        self.assertEqual(booking.payment_status, 'UNPAID')

        BookingService.record_payment(booking, Decimal('400.00'))
        self.assertEqual(booking.paid_amount, Decimal('400.00'))
        self.assertEqual(booking.payment_status, 'PAID')

    def test_overlapping_booking_rejection(self):
        check_in = date.today()
        check_out = check_in + timedelta(days=5)

        BookingService.create_booking(
            tenant=self.tenant,
            room=self.room,
            guest_name="Guest One",
            guest_phone="+15550177",
            check_in_date=check_in,
            check_out_date=check_out
        )

        # Overlapping attempt
        with self.assertRaises(ValidationError):
            BookingService.create_booking(
                tenant=self.tenant,
                room=self.room,
                guest_name="Guest Two",
                guest_phone="+15550166",
                check_in_date=check_in + timedelta(days=2),
                check_out_date=check_in + timedelta(days=4)
            )

    def test_booking_checkin_checkout_flow(self):
        check_in = date.today()
        check_out = check_in + timedelta(days=2)

        booking = BookingService.create_booking(
            tenant=self.tenant,
            room=self.room,
            guest_name="Alice",
            guest_phone="+15550155",
            check_in_date=check_in,
            check_out_date=check_out
        )

        BookingService.confirm_booking(booking)
        self.assertEqual(booking.status, 'CONFIRMED')

        BookingService.check_in(booking)
        self.assertEqual(booking.status, 'CHECKED_IN')
        self.assertEqual(self.room.status, 'OCCUPIED')

        BookingService.check_out(booking)
        self.assertEqual(booking.status, 'CHECKED_OUT')
        self.assertEqual(self.room.status, 'CLEANING')

    def test_hourly_booking_creation_and_conflict_validation(self):
        from django.utils import timezone
        from datetime import datetime

        today = date.today()
        dt_14 = timezone.make_aware(datetime.combine(today, datetime.strptime("14:00", "%H:%M").time()))
        dt_17 = timezone.make_aware(datetime.combine(today, datetime.strptime("17:00", "%H:%M").time()))
        dt_15 = timezone.make_aware(datetime.combine(today, datetime.strptime("15:00", "%H:%M").time()))
        dt_18 = timezone.make_aware(datetime.combine(today, datetime.strptime("18:00", "%H:%M").time()))
        dt_19 = timezone.make_aware(datetime.combine(today, datetime.strptime("19:00", "%H:%M").time()))
        dt_22 = timezone.make_aware(datetime.combine(today, datetime.strptime("22:00", "%H:%M").time()))

        # 1. Hourly booking: 02:00 PM - 05:00 PM (3 hours @ 1000/hr = 3000)
        booking1 = BookingService.create_booking(
            tenant=self.tenant,
            room=self.room,
            guest_name="Hourly Guest 1",
            guest_phone="+15550999",
            booking_type='HOURLY',
            check_in_dt=dt_14,
            check_out_dt=dt_17,
            rate_applied=Decimal('1000.00'),
            total_amount=Decimal('3000.00'),
            paid_amount=Decimal('3000.00')
        )
        self.assertEqual(booking1.total_duration, "3 Hours")
        self.assertEqual(booking1.total_amount, Decimal('3000.00'))

        # 2. Conflicting attempt: 03:00 PM - 06:00 PM -> Must raise ValidationError
        with self.assertRaises(ValidationError):
            BookingService.create_booking(
                tenant=self.tenant,
                room=self.room,
                guest_name="Conflicting Guest",
                guest_phone="+15550888",
                booking_type='HOURLY',
                check_in_dt=dt_15,
                check_out_dt=dt_18
            )

        # 3. Non-overlapping attempt: 07:00 PM - 10:00 PM -> Must succeed
        booking2 = BookingService.create_booking(
            tenant=self.tenant,
            room=self.room,
            guest_name="Evening Guest",
            guest_phone="+15550777",
            booking_type='HOURLY',
            check_in_dt=dt_19,
            check_out_dt=dt_22,
            rate_applied=Decimal('1000.00'),
            total_amount=Decimal('3000.00')
        )
        self.assertIsNotNone(booking2.id)

