from datetime import date, timedelta
from decimal import Decimal
from django.db.models import Sum, Q, F
from apps.bookings.models import Booking
from apps.expenses.models import Expense
from apps.properties.models import Property
from apps.rooms.models import Room, RoomType
from apps.staff.models import StaffProfile

class ReportService:
    @staticmethod
    def get_financial_summary(tenant_id: int, property_id: int = None, start_date: date = None, end_date: date = None) -> dict:
        """
        SSOT function to calculate Financial Performance: Total Revenue, Total Expenses, Net Profit.
        """
        if not start_date:
            start_date = date.today().replace(day=1)
        if not end_date:
            end_date = date.today()

        days_count = (end_date - start_date).days + 1
        months_fraction = Decimal(days_count) / Decimal('30.0')

        # 1. Total Property Booking Revenue
        booking_query = Booking.objects.filter(
            tenant_id=tenant_id,
            check_in_date__gte=start_date,
            check_in_date__lte=end_date
        ).exclude(status='CANCELLED')

        if property_id:
            booking_query = booking_query.filter(property_id=property_id)

        booking_stats = booking_query.aggregate(
            booked=Sum('total_amount'),
            collected=Sum('paid_amount')
        )
        total_booked_revenue = booking_stats['booked'] or Decimal('0.0')
        total_collected_revenue = booking_stats['collected'] or Decimal('0.0')


        # 2. Raw Operational Expenses
        expense_query = Expense.objects.filter(
            tenant_id=tenant_id,
            expense_date__gte=start_date,
            expense_date__lte=end_date
        )
        if property_id:
            expense_query = expense_query.filter(property_id=property_id)

        raw_expenses = expense_query.aggregate(total=Sum('amount'))['total'] or Decimal('0.0')

        # 3. Staff Payroll Cost
        staff_query = StaffProfile.objects.filter(tenant_id=tenant_id, is_active=True)
        if property_id:
            staff_query = staff_query.filter(property_id=property_id)
        monthly_staff_salary = staff_query.aggregate(total=Sum('monthly_salary'))['total'] or Decimal('0.0')
        period_staff_expense = monthly_staff_salary * months_fraction

        # 4. Landlord Property Rent Cost
        prop_query = Property.objects.filter(tenant_id=tenant_id, status='ACTIVE')
        if property_id:
            prop_query = prop_query.filter(id=property_id)
        monthly_property_rent = prop_query.aggregate(total=Sum('monthly_rent'))['total'] or Decimal('0.0')
        period_rent_expense = monthly_property_rent * months_fraction

        # 5. Total Expenses & Net Profit
        total_expenses = raw_expenses + period_staff_expense + period_rent_expense
        net_profit = total_booked_revenue - total_expenses

        return {
            'period_start': start_date,
            'period_end': end_date,
            'period_days': days_count,
            'total_booked_revenue': round(total_booked_revenue, 2),
            'total_collected_revenue': round(total_collected_revenue, 2),
            'raw_operational_expenses': round(raw_expenses, 2),
            'staff_payroll_expense': round(period_staff_expense, 2),
            'property_rent_expense': round(period_rent_expense, 2),
            'total_expenses': round(total_expenses, 2),
            'net_profit': round(net_profit, 2)
        }

    @staticmethod
    def get_occupancy_summary(tenant_id: int, property_id: int = None, start_date: date = None, end_date: date = None) -> dict:
        """
        SSOT function to calculate Occupancy Rate: (Occupied Room-Nights / Total Available Room-Nights) * 100.
        """
        if not start_date:
            start_date = date.today().replace(day=1)
        if not end_date:
            end_date = date.today()

        days_count = (end_date - start_date).days + 1
        if days_count <= 0:
            days_count = 1

        rooms_query = Room.objects.filter(tenant_id=tenant_id)
        if property_id:
            rooms_query = rooms_query.filter(property_id=property_id)

        total_rooms = rooms_query.count()
        total_available_room_nights = total_rooms * days_count

        if total_available_room_nights == 0:
            return {
                'period_start': start_date,
                'period_end': end_date,
                'total_rooms': 0,
                'total_available_room_nights': 0,
                'occupied_room_nights': 0,
                'occupancy_rate_percentage': 0.0
            }

        # Calculate total occupied room nights within the period
        bookings = Booking.objects.filter(
            tenant_id=tenant_id,
            check_in_date__lt=end_date + timedelta(days=1),
            check_out_date__gt=start_date
        ).exclude(status='CANCELLED')

        if property_id:
            bookings = bookings.filter(property_id=property_id)

        occupied_room_nights = 0
        for booking in bookings:
            overlap_start = max(booking.check_in_date, start_date)
            overlap_end = min(booking.check_out_date, end_date + timedelta(days=1))
            overlap_days = (overlap_end - overlap_start).days
            if overlap_days > 0:
                occupied_room_nights += overlap_days

        occupancy_rate = (Decimal(occupied_room_nights) / Decimal(total_available_room_nights)) * Decimal('100.0')

        return {
            'period_start': start_date,
            'period_end': end_date,
            'total_rooms': total_rooms,
            'total_available_room_nights': total_available_room_nights,
            'occupied_room_nights': occupied_room_nights,
            'occupancy_rate_percentage': round(float(occupancy_rate), 2)
        }

    @staticmethod
    def get_dashboard_analytics(tenant_id: int, property_id: int = None, period: str = 'today') -> dict:
        """
        Executive Hospitality BI & Operations Command Center analytics engine.
        Calculates KPIs, trends, operations pulse, time-series data, and room type distributions.
        """
        today = date.today()

        if period == 'today':
            start_date = today
            end_date = today
            prev_start = today - timedelta(days=1)
            prev_end = today - timedelta(days=1)
        elif period == '7d':
            start_date = today - timedelta(days=6)
            end_date = today
            prev_start = start_date - timedelta(days=7)
            prev_end = start_date - timedelta(days=1)
        elif period == '30d':
            start_date = today - timedelta(days=29)
            end_date = today
            prev_start = start_date - timedelta(days=30)
            prev_end = start_date - timedelta(days=1)
        elif period == 'quarter':
            quarter_month = ((today.month - 1) // 3) * 3 + 1
            start_date = date(today.year, quarter_month, 1)
            end_date = today
            period_days = (end_date - start_date).days + 1
            prev_end = start_date - timedelta(days=1)
            prev_start = prev_end - timedelta(days=period_days - 1)
        elif period == 'ytd':
            start_date = date(today.year, 1, 1)
            end_date = today
            period_days = (end_date - start_date).days + 1
            prev_start = date(today.year - 1, 1, 1)
            prev_end = prev_start + timedelta(days=period_days - 1)
        else:
            period = 'today'
            start_date = today
            end_date = today
            prev_start = today - timedelta(days=1)
            prev_end = today - timedelta(days=1)

        rooms_query = Room.objects.filter(tenant_id=tenant_id)
        if property_id:
            rooms_query = rooms_query.filter(property_id=property_id)

        total_rooms = rooms_query.count()
        occupied_rooms_now = rooms_query.filter(status='OCCUPIED').count()
        dirty_rooms_count = rooms_query.filter(housekeeping_status='DIRTY').count()

        def calculate_period_metrics(p_start, p_end):
            p_days = (p_end - p_start).days + 1
            p_bookings = Booking.objects.filter(
                tenant_id=tenant_id,
                check_in_date__lte=p_end,
                check_out_date__gte=p_start
            ).exclude(status='CANCELLED')

            if property_id:
                p_bookings = p_bookings.filter(property_id=property_id)

            total_rev = Decimal('0.0')
            occupied_rn = 0
            for b in p_bookings:
                o_start = max(b.check_in_date, p_start)
                o_end = min(b.check_out_date, p_end + timedelta(days=1))
                o_days = (o_end - o_start).days
                if o_days > 0:
                    occupied_rn += o_days
                    rate = b.nightly_rate or (b.total_amount / Decimal(b.total_nights if b.total_nights else 1))
                    total_rev += Decimal(o_days) * rate

            avail_rn = total_rooms * p_days
            occ_rate = float(round((Decimal(occupied_rn) / Decimal(avail_rn) * Decimal('100.0')), 2)) if avail_rn > 0 else 0.0
            adr = float(round((total_rev / Decimal(occupied_rn)), 2)) if occupied_rn > 0 else 0.0
            revpar = float(round((total_rev / Decimal(avail_rn)), 2)) if avail_rn > 0 else 0.0

            return {
                'revenue': float(round(total_rev, 2)),
                'occupied_room_nights': occupied_rn,
                'available_room_nights': avail_rn,
                'occupancy_rate': occ_rate,
                'adr': adr,
                'revpar': revpar
            }

        curr_metrics = calculate_period_metrics(start_date, end_date)
        prev_metrics = calculate_period_metrics(prev_start, prev_end)

        def compute_trend(curr, prev):
            if prev == 0:
                return 100.0 if curr > 0 else 0.0
            return round(((curr - prev) / prev) * 100.0, 1)

        revenue_trend = compute_trend(curr_metrics['revenue'], prev_metrics['revenue'])
        occupancy_trend = compute_trend(curr_metrics['occupancy_rate'], prev_metrics['occupancy_rate'])
        adr_trend = compute_trend(curr_metrics['adr'], prev_metrics['adr'])
        revpar_trend = compute_trend(curr_metrics['revpar'], prev_metrics['revpar'])

        # Today's Revenue (Revenue for today's occupied room nights / bookings)
        today_bookings = Booking.objects.filter(
            tenant_id=tenant_id,
            check_in_date__lte=today,
            check_out_date__gte=today
        ).exclude(status='CANCELLED')
        if property_id:
            today_bookings = today_bookings.filter(property_id=property_id)

        today_revenue = sum(
            float(b.nightly_rate or (b.total_amount / Decimal(b.total_nights or 1))) for b in today_bookings
        )

        # Live Operations Pulse Feed
        arrivals_query = Booking.objects.filter(
            tenant_id=tenant_id,
            check_in_date=today,
            status__in=['CONFIRMED', 'RESERVED', 'PENDING']
        ).select_related('room', 'room__room_type', 'property')
        if property_id:
            arrivals_query = arrivals_query.filter(property_id=property_id)

        today_arrivals = [
            {
                'id': b.id,
                'guest_name': b.guest_name,
                'guest_phone': b.guest_phone,
                'room_id': b.room_id,
                'room_number': b.room.room_number if b.room else 'N/A',
                'room_type_name': b.room.room_type.name if b.room and b.room.room_type else 'Standard',
                'check_in_date': b.check_in_date.isoformat(),
                'advance_paid': float(b.paid_amount),
                'total_amount': float(b.total_amount),
                'status': b.status,
            }
            for b in arrivals_query
        ]

        departures_query = Booking.objects.filter(
            tenant_id=tenant_id,
            check_out_date=today,
            status='CHECKED_IN'
        ).select_related('room', 'room__room_type', 'property')
        if property_id:
            departures_query = departures_query.filter(property_id=property_id)

        today_departures = [
            {
                'id': b.id,
                'guest_name': b.guest_name,
                'guest_phone': b.guest_phone,
                'room_id': b.room_id,
                'room_number': b.room.room_number if b.room else 'N/A',
                'room_type_name': b.room.room_type.name if b.room and b.room.room_type else 'Standard',
                'check_out_date': b.check_out_date.isoformat(),
                'paid_amount': float(b.paid_amount),
                'total_amount': float(b.total_amount),
                'total_balance': float(b.total_amount - b.paid_amount),
                'status': b.status,
            }
            for b in departures_query
        ]

        pending_query = Booking.objects.filter(
            tenant_id=tenant_id,
            status='CHECKED_IN',
            paid_amount__lt=F('total_amount')
        ).select_related('room')
        if property_id:
            pending_query = pending_query.filter(property_id=property_id)

        pending_payments = [
            {
                'id': b.id,
                'guest_name': b.guest_name,
                'room_number': b.room.room_number if b.room else 'N/A',
                'paid_amount': float(b.paid_amount),
                'total_amount': float(b.total_amount),
                'balance': float(b.total_amount - b.paid_amount),
            }
            for b in pending_query
        ]

        # Time-Series Chart Data
        chart_data = []
        cur_day = start_date
        while cur_day <= end_date:
            day_metrics = calculate_period_metrics(cur_day, cur_day)
            chart_data.append({
                'date': cur_day.strftime('%Y-%m-%d'),
                'revenue': day_metrics['revenue'],
                'occupancy_rate': day_metrics['occupancy_rate'],
                'adr': day_metrics['adr'],
                'revpar': day_metrics['revpar'],
            })
            cur_day += timedelta(days=1)

        # Room Type Occupancy Matrix
        room_types_query = RoomType.objects.filter(tenant_id=tenant_id)
        if property_id:
            room_types_query = room_types_query.filter(property_id=property_id)

        room_type_occupancy = []
        for rt in room_types_query:
            rt_rooms = rooms_query.filter(room_type=rt)
            rt_total = rt_rooms.count()
            rt_occupied = rt_rooms.filter(status='OCCUPIED').count()
            rt_rate = round((rt_occupied / rt_total * 100.0) if rt_total > 0 else 0.0, 1)
            room_type_occupancy.append({
                'room_type_id': rt.id,
                'room_type': rt.name,
                'base_price': float(rt.base_price_per_night),
                'total_rooms': rt_total,
                'occupied_rooms': rt_occupied,
                'occupancy_rate': rt_rate,
            })

        return {
            'period': period,
            'kpis': {
                'today_revenue': float(round(today_revenue, 2)),
                'period_revenue': curr_metrics['revenue'],
                'revenue_trend': revenue_trend,
                'total_rooms': total_rooms,
                'occupied_rooms': occupied_rooms_now,
                'occupancy_rate': curr_metrics['occupancy_rate'],
                'occupancy_trend': occupancy_trend,
                'adr': curr_metrics['adr'],
                'adr_trend': adr_trend,
                'revpar': curr_metrics['revpar'],
                'revpar_trend': revpar_trend,
            },
            'operations_pulse': {
                'today_arrivals': today_arrivals,
                'today_departures': today_departures,
                'pending_payments': pending_payments,
                'dirty_rooms_count': dirty_rooms_count,
            },
            'chart_data': chart_data,
            'room_type_occupancy': room_type_occupancy,
        }

