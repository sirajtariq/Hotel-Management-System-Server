from typing import Optional
from datetime import date, datetime, time
from decimal import Decimal
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from apps.bookings.models import Booking
from apps.rooms.models import Room
from apps.tenants.models import Tenant
from apps.properties.models import Property

def check_room_availability(room, check_in_dt, check_out_dt, exclude_booking_id=None):
    if check_out_dt <= check_in_dt:
        raise ValidationError({"check_out": "Check-out time must be strictly after check-in time."})

    conflicts = Booking.objects.filter(
        tenant=room.tenant,
        room=room,
        status__in=['CONFIRMED', 'CHECKED_IN', 'RESERVED', 'PENDING'],
    ).filter(
        Q(check_in__lt=check_out_dt, check_out__gt=check_in_dt) |
        Q(check_in__isnull=True, check_in_date__lt=check_out_dt.date(), check_out_date__gt=check_in_dt.date())
    )
    if exclude_booking_id:
        conflicts = conflicts.exclude(id=exclude_booking_id)

    if conflicts.exists():
        c = conflicts.first()
        start_str = c.check_in.strftime('%d-%b %I:%M %p') if c.check_in else str(c.check_in_date)
        end_str = c.check_out.strftime('%d-%b %I:%M %p') if c.check_out else str(c.check_out_date)
        raise ValidationError({
            "room": f"Room {room.room_number} is already booked for the selected date range ({start_str} to {end_str})."
        })

class BookingService:
    @staticmethod
    def calculate_payment_status(paid_amount: Decimal, total_amount: Decimal) -> str:
        """
        SSOT formula for booking payment status.
        """
        if paid_amount >= total_amount and total_amount > 0:
            return 'PAID'
        elif paid_amount > 0:
            return 'PARTIAL'
        return 'UNPAID'

    @staticmethod
    def validate_dates(check_in_date: date, check_out_date: date):
        """
        SSOT function to validate booking date range.
        """
        if check_out_date <= check_in_date:
            raise ValidationError({'check_out_date': 'Check-out date must be strictly after check-in date.'})

    @staticmethod
    def is_room_available(room: Room, check_in_date: date, check_out_date: date, exclude_booking_id: int = None) -> bool:
        """
        SSOT function to check room availability and prevent overlapping bookings.
        """
        check_in_dt = timezone.make_aware(datetime.combine(check_in_date, time(14, 0))) if isinstance(check_in_date, date) else check_in_date
        check_out_dt = timezone.make_aware(datetime.combine(check_out_date, time(12, 0))) if isinstance(check_out_date, date) else check_out_date
        try:
            check_room_availability(room, check_in_dt, check_out_dt, exclude_booking_id=exclude_booking_id)
            return True
        except ValidationError:
            return False

    @classmethod
    @transaction.atomic
    def create_booking(
        cls,
        tenant: Tenant,
        room: Room,
        guest_name: str,
        guest_phone: str,
        booking_type: str = 'NIGHTLY',
        check_in_dt: datetime = None,
        check_out_dt: datetime = None,
        check_in_date: date = None,
        check_out_date: date = None,
        guest_email: str = '',
        nightly_rate: Decimal = None,
        rate_applied: Decimal = None,
        subtotal_amount: Decimal = None,
        discount_type: str = 'FLAT',
        discount_value: Decimal = Decimal('0.00'),
        discount_amount: Decimal = None,
        tax_rate: Decimal = Decimal('0.00'),
        tax_amount: Decimal = None,
        total_amount: Decimal = None,
        paid_amount: Decimal = Decimal('0.0'),
        total_duration: str = ''
    ) -> Booking:
        """
        SSOT function to create a new booking supporting NIGHTLY and HOURLY modes with manual Tax % and Discount.
        """
        if not check_in_dt and check_in_date:
            check_in_dt = datetime.combine(check_in_date, time(14, 0))
        if not check_out_dt and check_out_date:
            check_out_dt = datetime.combine(check_out_date, time(12, 0))

        if not check_in_dt or not check_out_dt:
            raise ValidationError({"check_in": "Check-in and check-out date/time are required."})

        if timezone.is_naive(check_in_dt):
            check_in_dt = timezone.make_aware(check_in_dt)
        if timezone.is_naive(check_out_dt):
            check_out_dt = timezone.make_aware(check_out_dt)

        # 1. Lock the room row exclusively for the duration of this transaction
        try:
            locked_room = (
                Room.objects.select_for_update()
                .select_related('property', 'room_type')
                .get(id=room.id, tenant=tenant)
            )
        except Room.DoesNotExist:
            raise ValidationError({"room": "Selected room does not exist or is not assigned to this property."})

        check_room_availability(locked_room, check_in_dt, check_out_dt)
        room = locked_room

        check_in_d = check_in_dt.date()
        check_out_d = check_out_dt.date()
        if check_out_d <= check_in_d and booking_type == 'NIGHTLY':
            check_out_d = check_in_d + timezone.timedelta(days=1)

        total_nights = max(1, (check_out_d - check_in_d).days)

        if booking_type == 'HOURLY':
            hours = max(1, int((check_out_dt - check_in_dt).total_seconds() // 3600))
            if not total_duration:
                total_duration = f"{hours} Hours"
            if rate_applied is None:
                rate_applied = Decimal(getattr(room, 'hourly_rate', None) or (room.room_type.base_price_per_night / Decimal('6.0')))
            if subtotal_amount is None:
                subtotal_amount = Decimal(hours) * Decimal(rate_applied)
        else:
            if not total_duration:
                total_duration = f"{total_nights} Night" if total_nights == 1 else f"{total_nights} Nights"
            if rate_applied is None:
                rate_applied = Decimal(nightly_rate or room.room_type.base_price_per_night)
            if subtotal_amount is None:
                subtotal_amount = Decimal(total_nights) * Decimal(rate_applied)

        if discount_type == 'PERCENTAGE':
            if discount_amount is None and discount_value is not None:
                discount_amount = round(Decimal(subtotal_amount) * (Decimal(discount_value) / Decimal('100.0')), 2)
        else:
            if discount_amount is None and discount_value is not None:
                discount_amount = min(Decimal(subtotal_amount), Decimal(discount_value))

        if discount_amount is None:
            discount_amount = Decimal('0.00')
        if discount_value is None:
            discount_value = Decimal('0.00')

        net_subtotal = max(Decimal('0.00'), Decimal(subtotal_amount) - Decimal(discount_amount))

        if tax_rate is None:
            tax_rate = Decimal('0.00')

        if tax_amount is None:
            tax_amount = round(net_subtotal * (Decimal(tax_rate) / Decimal('100.0')), 2)

        if total_amount is None:
            total_amount = net_subtotal + Decimal(tax_amount)

        payment_status = cls.calculate_payment_status(paid_amount, total_amount)

        booking_status = 'RESERVED'
        if paid_amount >= total_amount and total_amount > 0:
            booking_status = 'CONFIRMED'

        booking = Booking.objects.create(
            tenant=tenant,
            property=room.property,
            room=room,
            guest_name=guest_name,
            guest_email=guest_email,
            guest_phone=guest_phone,
            booking_type=booking_type,
            check_in_date=check_in_d,
            check_out_date=check_out_d,
            check_in=check_in_dt,
            check_out=check_out_dt,
            total_nights=total_nights,
            total_duration=total_duration,
            nightly_rate=rate_applied if booking_type == 'NIGHTLY' else None,
            rate_applied=rate_applied,
            subtotal_amount=subtotal_amount,
            discount_type=discount_type,
            discount_value=discount_value,
            discount_amount=discount_amount,
            tax_rate=tax_rate,
            tax_amount=tax_amount,
            total_amount=total_amount,
            paid_amount=paid_amount,
            payment_status=payment_status,
            status=booking_status
        )

        now = timezone.now()
        if check_in_dt <= now and check_out_dt > now:
            room.status = 'OCCUPIED'
        else:
            room.status = 'RESERVED'
        room.save(update_fields=['status', 'updated_at'])

        return booking

    @classmethod
    @transaction.atomic
    def confirm_booking(cls, booking: Booking) -> Booking:
        if booking.status == 'CANCELLED':
            raise ValidationError({'status': 'Cannot confirm a cancelled booking.'})
        booking.status = 'CONFIRMED'
        booking.save(update_fields=['status', 'updated_at'])
        return booking

    @classmethod
    @transaction.atomic
    def check_in(cls, booking: Booking) -> Booking:
        if booking.status in ['CANCELLED', 'CHECKED_OUT']:
            raise ValidationError({'status': f'Cannot check in a booking in state {booking.status}.'})
        
        booking.status = 'CHECKED_IN'
        booking.save(update_fields=['status', 'updated_at'])

        # Update room status to OCCUPIED
        room = booking.room
        room.status = 'OCCUPIED'
        room.save(update_fields=['status', 'updated_at'])

        return booking

    @classmethod
    @transaction.atomic
    def check_out(cls, booking: Booking) -> Booking:
        if booking.status != 'CHECKED_IN':
            raise ValidationError({'status': 'Only checked-in bookings can be checked out.'})

        booking.status = 'CHECKED_OUT'
        booking.save(update_fields=['status', 'updated_at'])

        # Update room status to AVAILABLE and housekeeping_status to DIRTY
        room = booking.room
        room.status = 'AVAILABLE'
        room.housekeeping_status = 'DIRTY'
        room.save(update_fields=['status', 'housekeeping_status', 'updated_at'])

        return booking

    @classmethod
    @transaction.atomic
    def cancel_booking(cls, booking: Booking) -> Booking:
        if booking.status == 'CHECKED_OUT':
            raise ValidationError({'status': 'Cannot cancel a booking that has already checked out.'})

        booking.status = 'CANCELLED'
        booking.save(update_fields=['status', 'updated_at'])

        # Free room if reserved or occupied
        if booking.room.status in ['OCCUPIED', 'RESERVED']:
            booking.room.status = 'AVAILABLE'
            booking.room.save(update_fields=['status', 'updated_at'])

        return booking

    @classmethod
    @transaction.atomic
    def record_payment(
        cls,
        booking: Booking,
        amount: Decimal,
        payment_account_id: Optional[int] = None,
        payment_method: Optional[str] = None,
        user=None
    ) -> Booking:
        """
        SSOT function to record a payment towards a booking and credit the target PaymentAccount.
        """
        if amount <= 0:
            raise ValidationError({'amount': 'Payment amount must be greater than 0.'})

        tenant = booking.tenant

        # Resolve target PaymentAccount
        account = None
        if payment_account_id:
            from apps.accounts.models import PaymentAccount
            account = PaymentAccount.objects.filter(id=payment_account_id, tenant=tenant, is_active=True).first()

        if not account:
            from apps.accounts.models import PaymentAccount
            account = PaymentAccount.objects.filter(tenant=tenant, is_default=True, is_active=True).first()

        if not account:
            from apps.accounts.models import PaymentAccount
            account = PaymentAccount.objects.filter(tenant=tenant, is_active=True).first()

        if account:
            from apps.accounts.services.account_service import AccountService
            tenant_code = getattr(tenant, 'code', '') or 'RS'
            inv_no = f"INV-{tenant_code.upper()}-2026-{booking.id:04d}"
            desc = f"Room Payment for Booking #{booking.id} ({booking.guest_name})"
            AccountService.record_transaction(
                tenant=tenant,
                account=account,
                transaction_type='INFLOW',
                amount=amount,
                source_module='BOOKING',
                reference_id=inv_no,
                description=desc,
                user=user
            )

        booking.paid_amount += amount
        booking.payment_status = cls.calculate_payment_status(booking.paid_amount, booking.total_amount)
        booking.save(update_fields=['paid_amount', 'payment_status', 'updated_at'])
        return booking

def create_booking_with_lock(*, tenant_id, property_id, room_id, guest_name='', guest_phone='', check_in_date=None, check_out_date=None, **booking_kwargs):
    """
    Acquires an exclusive row-level lock on the Room record to prevent
    simultaneous overlapping reservations (double booking).
    """
    with transaction.atomic():
        try:
            room = (
                Room.objects.select_for_update()
                .select_related('property', 'room_type')
                .get(id=room_id, tenant_id=tenant_id, property_id=property_id)
            )
        except Room.DoesNotExist:
            raise ValidationError({"room": "Selected room does not exist or is not assigned to this property."})

        tenant = room.tenant
        return BookingService.create_booking(
            tenant=tenant,
            room=room,
            guest_name=guest_name,
            guest_phone=guest_phone,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            **booking_kwargs
        )
