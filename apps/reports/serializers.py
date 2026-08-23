from rest_framework import serializers

class ReportQuerySerializer(serializers.Serializer):
    property_id = serializers.IntegerField(required=False, allow_null=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)

class FinancialReportResponseSerializer(serializers.Serializer):
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    period_days = serializers.IntegerField()
    total_booked_revenue = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_collected_revenue = serializers.DecimalField(max_digits=14, decimal_places=2)
    raw_operational_expenses = serializers.DecimalField(max_digits=14, decimal_places=2)
    staff_payroll_expense = serializers.DecimalField(max_digits=14, decimal_places=2)
    property_rent_expense = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_expenses = serializers.DecimalField(max_digits=14, decimal_places=2)
    net_profit = serializers.DecimalField(max_digits=14, decimal_places=2)

class OccupancyReportResponseSerializer(serializers.Serializer):
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    total_rooms = serializers.IntegerField()
    total_available_room_nights = serializers.IntegerField()
    occupied_room_nights = serializers.IntegerField()
    occupancy_rate_percentage = serializers.FloatField()

class DashboardAnalyticsQuerySerializer(serializers.Serializer):
    period = serializers.ChoiceField(choices=['today', '7d', '30d', 'quarter', 'ytd'], default='today', required=False)
    property_id = serializers.IntegerField(required=False, allow_null=True)

class KpiMetricsSerializer(serializers.Serializer):
    today_revenue = serializers.FloatField()
    period_revenue = serializers.FloatField()
    revenue_trend = serializers.FloatField()
    total_rooms = serializers.IntegerField()
    occupied_rooms = serializers.IntegerField()
    occupancy_rate = serializers.FloatField()
    occupancy_trend = serializers.FloatField()
    adr = serializers.FloatField()
    adr_trend = serializers.FloatField()
    revpar = serializers.FloatField()
    revpar_trend = serializers.FloatField()

class ArrivalItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    guest_name = serializers.CharField()
    guest_phone = serializers.CharField()
    room_id = serializers.IntegerField(allow_null=True)
    room_number = serializers.CharField()
    room_type_name = serializers.CharField()
    check_in_date = serializers.CharField()
    advance_paid = serializers.FloatField()
    total_amount = serializers.FloatField()
    status = serializers.CharField()

class DepartureItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    guest_name = serializers.CharField()
    guest_phone = serializers.CharField()
    room_id = serializers.IntegerField(allow_null=True)
    room_number = serializers.CharField()
    room_type_name = serializers.CharField()
    check_out_date = serializers.CharField()
    paid_amount = serializers.FloatField()
    total_amount = serializers.FloatField()
    total_balance = serializers.FloatField()
    status = serializers.CharField()

class PendingPaymentItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    guest_name = serializers.CharField()
    room_number = serializers.CharField()
    paid_amount = serializers.FloatField()
    total_amount = serializers.FloatField()
    balance = serializers.FloatField()

class OperationsPulseSerializer(serializers.Serializer):
    today_arrivals = ArrivalItemSerializer(many=True)
    today_departures = DepartureItemSerializer(many=True)
    pending_payments = PendingPaymentItemSerializer(many=True)
    dirty_rooms_count = serializers.IntegerField()

class TimeSeriesPointSerializer(serializers.Serializer):
    date = serializers.CharField()
    revenue = serializers.FloatField()
    occupancy_rate = serializers.FloatField()
    adr = serializers.FloatField()
    revpar = serializers.FloatField()

class RoomTypeOccupancySerializer(serializers.Serializer):
    room_type_id = serializers.IntegerField()
    room_type = serializers.CharField()
    base_price = serializers.FloatField()
    total_rooms = serializers.IntegerField()
    occupied_rooms = serializers.IntegerField()
    occupancy_rate = serializers.FloatField()

class DashboardAnalyticsResponseSerializer(serializers.Serializer):
    period = serializers.CharField()
    kpis = KpiMetricsSerializer()
    operations_pulse = OperationsPulseSerializer()
    chart_data = TimeSeriesPointSerializer(many=True)
    room_type_occupancy = RoomTypeOccupancySerializer(many=True)

class FinancialFilterQuerySerializer(serializers.Serializer):
    period = serializers.ChoiceField(
        choices=['today', '7d', '30d', 'this_month', 'last_month', 'quarter', 'ytd', 'custom'],
        default='this_month',
        required=False
    )
    property_id = serializers.IntegerField(required=False, allow_null=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    report_type = serializers.CharField(required=False, default='pnl')


