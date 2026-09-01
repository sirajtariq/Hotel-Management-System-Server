from decimal import Decimal
from apps.restaurant.models import RestaurantOrder


class InvoiceService:
    @staticmethod
    def get_invoice_context(booking):
        """
        SSOT function to compile comprehensive invoice data and financial folio calculations.
        """
        property_obj = booking.property
        property_data = {
            "name": property_obj.name if property_obj else "",
            "address": getattr(property_obj, 'address', '') or "",
            "city": getattr(property_obj, 'city', '') or "",
            "phone": getattr(property_obj, 'phone', '') or "",
            "email": getattr(property_obj, 'email', '') or "",
        }

        # Fetch linked POS Food & Beverage orders
        pos_orders = getattr(booking, 'restaurant_orders', None)
        if pos_orders is None:
            pos_orders = RestaurantOrder.objects.filter(booking=booking)

        pos_items_summary = []
        pos_total = Decimal('0.00')

        if pos_orders:
            valid_orders = pos_orders.filter(
                status__in=['COMPLETED', 'BILLED_TO_ROOM', 'DELIVERED', 'SERVED', 'READY', 'PREPARING', 'PENDING']
            )
            for order in valid_orders:
                pos_total += order.grand_total
                pos_items_summary.append({
                    "id": order.id,
                    "order_number": order.order_number or str(order.id),
                    "description": f"Restaurant Bill #{order.order_number or order.id} (Food & Beverage)",
                    "quantity": f"{order.items.count()} items",
                    "rate": str(order.grand_total),
                    "total": str(order.grand_total),
                    "payment_status": order.payment_status,
                })

        total_amount = booking.total_amount or Decimal('0.00')
        room_charges = max(Decimal('0.00'), total_amount - pos_total)
        total_folio_bill = room_charges + pos_total

        total_refunded = Decimal(str(getattr(booking, 'total_refunded', 0) or 0))
        net_paid = Decimal(str(getattr(booking, 'paid_amount', 0) or 0))
        total_paid = net_paid + total_refunded  # Gross advance / total paid before refund
        balance_due = max(Decimal('0.00'), total_folio_bill - net_paid)

        room_stay_item = {
            "description": f"Room Accommodation - Room {booking.room.room_number if booking.room else ''} ({booking.room.room_type.name if booking.room and booking.room.room_type else 'Suite'})",
            "quantity": f"{booking.total_nights or 1} Nights",
            "rate": str(booking.rate_applied or booking.nightly_rate or (room_charges / max(1, booking.total_nights or 1))),
            "total": str(room_charges),
        }

        tenant_code = getattr(booking.tenant, 'code', '') or 'RS'
        invoice_number = f"INV-{tenant_code.upper()}-2026-{booking.id:04d}"

        guest_data = {
            "full_name": booking.guest_name,
            "phone": booking.guest_phone,
            "email": booking.guest_email,
            "cnic": getattr(booking, 'cnic_or_passport', '') or 'N/A'
        }

        stay_summary = {
            "check_in": booking.check_in.strftime('%Y-%m-%d %H:%M') if booking.check_in else (booking.check_in_date.strftime('%Y-%m-%d') if booking.check_in_date else ''),
            "check_out": booking.check_out.strftime('%Y-%m-%d %H:%M') if booking.check_out else (booking.check_out_date.strftime('%Y-%m-%d') if booking.check_out_date else ''),
            "total_nights": booking.total_nights,
            "booking_type": booking.booking_type,
            "status": booking.status,
            "payment_status": booking.payment_status,
        }

        return {
            "invoice_number": invoice_number,
            "booking_id": booking.id,
            "property": property_data,
            "guest": guest_data,
            "stay": stay_summary,
            "line_items": [room_stay_item] + pos_items_summary,
            "room_stay_charges": str(room_charges),
            "restaurant_charges": str(pos_total),
            "total_folio_bill": str(total_folio_bill),
            "total_paid": str(total_paid),
            "total_refunded": str(total_refunded),
            "net_paid": str(net_paid),
            "balance_due": str(balance_due),
        }
