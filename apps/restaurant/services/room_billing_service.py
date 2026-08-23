from django.db import transaction
from rest_framework.exceptions import ValidationError
from apps.bookings.services.booking_service import BookingService
from apps.restaurant.models import RestaurantOrder


class RoomBillingService:
    @classmethod
    @transaction.atomic
    def post_to_room_folio(cls, order: RestaurantOrder, booking=None) -> RestaurantOrder:
        """
        Posts restaurant order grand total directly to guest room booking folio.
        """
        target_booking = booking or order.booking
        if not target_booking:
            raise ValidationError("A valid guest booking is required for Room Service billing.")

        if target_booking.status != 'CHECKED_IN':
            raise ValidationError(f"Cannot bill to room. Guest booking #{target_booking.id} is in '{target_booking.status}' status (Must be CHECKED_IN).")

        # Update booking totals and recalculate payment status
        target_booking.total_amount += order.grand_total
        target_booking.payment_status = BookingService.calculate_payment_status(
            target_booking.paid_amount,
            target_booking.total_amount
        )
        target_booking.save(update_fields=['total_amount', 'payment_status', 'updated_at'])

        # Update order payment state
        order.booking = target_booking
        order.payment_status = 'BILLED_TO_ROOM'
        order.payment_method = 'ROOM_FOLIO'
        if not order.room_number and target_booking.room:
            order.room_number = target_booking.room.room_number
        if not order.customer_name:
            order.customer_name = target_booking.guest_name

        order.save(update_fields=['booking', 'payment_status', 'payment_method', 'room_number', 'customer_name', 'updated_at'])
        return order
