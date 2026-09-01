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
        from apps.users.models import User
        self.tenant = TenantService.create_tenant(name="Palace Suites")
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            tenant=self.tenant,
            is_superuser=True,
            is_staff=True
        )
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
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, 'OCCUPIED')

        BookingService.check_out(booking)
        self.assertEqual(booking.status, 'CHECKED_OUT')
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, 'AVAILABLE')

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

    def test_process_refund_flow(self):
        from apps.accounts.models import PaymentAccount, PaymentTransaction, AccountTransaction
        from apps.expenses.models import AccountHead
        from apps.bookings.serializers import BookingRefundSerializer
        from rest_framework.test import APIRequestFactory

        # Create Payment Account & Account Head for tenant
        payment_acc = PaymentAccount.objects.create(
            tenant=self.tenant,
            name="Main Cash Drawer",
            account_type="CASH",
            current_balance=Decimal('5000.00')
        )
        account_head = AccountHead.objects.create(
            tenant=self.tenant,
            name="Booking Refund Contra-Revenue"
        )

        check_in = date.today()
        check_out = check_in + timedelta(days=2)
        booking = BookingService.create_booking(
            tenant=self.tenant,
            room=self.room,
            guest_name="Refund Test Guest",
            guest_phone="+15550000",
            check_in_date=check_in,
            check_out_date=check_out,
            total_amount=Decimal('400.00'),
            paid_amount=Decimal('400.00')
        )

        # 1. Test Serializer validation with missing required fields
        factory = APIRequestFactory()
        request = factory.post('/dummy')
        request.user = self.user

        invalid_ser = BookingRefundSerializer(data={}, context={'booking': booking, 'request': request})
        self.assertFalse(invalid_ser.is_valid())
        self.assertIn('payment_account', invalid_ser.errors)
        self.assertIn('account_head', invalid_ser.errors)

        # 2. Test Serializer validation exceeding max refundable amount
        exceed_ser = BookingRefundSerializer(data={
            'amount': '500.00',
            'payment_account': payment_acc.id,
            'account_head': account_head.id
        }, context={'booking': booking, 'request': request})
        self.assertFalse(exceed_ser.is_valid())
        self.assertIn('amount', exceed_ser.errors)

        # 3. Test Valid Serializer
        valid_ser = BookingRefundSerializer(data={
            'amount': '200.00',
            'payment_account': payment_acc.id,
            'account_head': account_head.id,
            'reason': 'Guest cancelled reservation early'
        }, context={'booking': booking, 'request': request})
        self.assertTrue(valid_ser.is_valid(), valid_ser.errors)

        # 4. Process Refund action on confirmed booking (status -> CANCELLED)
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=request.user)

        response = client.post(f'/api/v1/bookings/{booking.id}/refund/', {
            'amount': '200.00',
            'payment_account': payment_acc.id,
            'account_head': account_head.id,
            'reason': 'Guest cancelled'
        }, format='json')

        self.assertEqual(response.status_code, 200)
        payment_acc.refresh_from_db()
        booking.refresh_from_db()
        self.assertEqual(payment_acc.current_balance, Decimal('4800.00'))
        self.assertEqual(booking.total_refunded, Decimal('200.00'))
        self.assertEqual(booking.paid_amount, Decimal('200.00'))
        self.assertEqual(booking.status, 'CANCELLED')

        # Verify PaymentTransaction, AccountTransaction & Expense records created
        from apps.expenses.models import Expense
        self.assertTrue(PaymentTransaction.objects.filter(booking=booking, amount=Decimal('200.00')).exists())
        self.assertTrue(AccountTransaction.objects.filter(reference_id=str(booking.id), amount=Decimal('200.00')).exists())
        self.assertTrue(Expense.objects.filter(account_head=account_head, amount=Decimal('200.00')).exists())

        # 5. Process partial refund on CHECKED_IN booking (status should remain CHECKED_IN)
        checked_in_booking = BookingService.create_booking(
            tenant=self.tenant,
            room=self.room,
            guest_name="In-House Guest",
            guest_phone="+15551111",
            check_in_date=check_in + timedelta(days=10),
            check_out_date=check_in + timedelta(days=12),
            total_amount=Decimal('800.00'),
            paid_amount=Decimal('800.00')
        )
        BookingService.check_in(checked_in_booking)
        self.assertEqual(checked_in_booking.status, 'CHECKED_IN')

        resp2 = client.post(f'/api/v1/bookings/{checked_in_booking.id}/refund/', {
            'amount': '100.00',
            'payment_account': payment_acc.id,
            'account_head': account_head.id,
            'reason': 'Partial service adjustment refund'
        }, format='json')
        self.assertEqual(resp2.status_code, 200)
        checked_in_booking.refresh_from_db()
        self.assertEqual(checked_in_booking.total_refunded, Decimal('100.00'))
        self.assertEqual(checked_in_booking.status, 'CHECKED_IN')


