from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from apps.tenants.services.tenant_service import TenantService
from apps.properties.services.property_service import PropertyService
from apps.rooms.services.room_service import RoomService
from apps.bookings.services.booking_service import BookingService
from apps.expenses.services.expense_service import ExpenseService
from apps.staff.services.staff_service import StaffService
from apps.reports.services.report_service import ReportService

class ReportTestCase(TestCase):
    def setUp(self):
        self.tenant_a = TenantService.create_tenant(name="Tenant Alpha")
        self.tenant_b = TenantService.create_tenant(name="Tenant Beta")

        self.prop_a = PropertyService.create_property(
            tenant=self.tenant_a,
            name="Alpha Manor",
            address="1 Alpha Way",
            city="Boston",
            monthly_rent=Decimal('3000.00')
        )
        self.prop_b = PropertyService.create_property(
            tenant=self.tenant_b,
            name="Beta Lodge",
            address="2 Beta Rd",
            city="Chicago",
            monthly_rent=Decimal('5000.00')
        )

        self.room_type_a = RoomService.create_room_type(
            tenant=self.tenant_a,
            property_obj=self.prop_a,
            name="Deluxe Room",
            base_price_per_night=Decimal('100.00')
        )
        self.room_a = RoomService.create_room(
            tenant=self.tenant_a,
            property_obj=self.prop_a,
            room_type=self.room_type_a,
            room_number="101"
        )

        # Create Staff for Tenant A
        StaffService.create_staff_member(
            tenant=self.tenant_a,
            property_obj=self.prop_a,
            name="Tom Staff",
            department="Front Desk",
            position="Receptionist",
            monthly_salary=Decimal('3000.00'),
            hired_date=date.today()
        )

    def test_financial_and_occupancy_report_services(self):
        start_date = date(2026, 8, 1)
        end_date = date(2026, 8, 30)  # 30 days = exactly 1 month fraction

        # Create Booking in Tenant A
        BookingService.create_booking(
            tenant=self.tenant_a,
            room=self.room_a,
            guest_name="Guest A",
            guest_phone="+15559900",
            check_in_date=start_date,
            check_out_date=start_date + timedelta(days=10),
            paid_amount=Decimal('1000.00')
        )

        # Create Expense in Tenant A
        cat = ExpenseService.create_category(tenant=self.tenant_a, name="Utilities")
        ExpenseService.create_expense(
            tenant=self.tenant_a,
            property_obj=self.prop_a,
            category=cat,
            item_name="Electricity Bill",
            amount=Decimal('500.00'),
            expense_date=start_date + timedelta(days=5)
        )

        # Financial Summary for Tenant A
        fin_summary_a = ReportService.get_financial_summary(
            tenant_id=self.tenant_a.id,
            start_date=start_date,
            end_date=end_date
        )

        # Booked Revenue = 10 nights * $100 = $1000
        self.assertEqual(fin_summary_a['total_booked_revenue'], Decimal('1000.00'))
        self.assertEqual(fin_summary_a['total_collected_revenue'], Decimal('1000.00'))
        self.assertEqual(fin_summary_a['raw_operational_expenses'], Decimal('500.00'))
        self.assertEqual(fin_summary_a['staff_payroll_expense'], Decimal('3000.00'))
        self.assertEqual(fin_summary_a['property_rent_expense'], Decimal('3000.00'))
        self.assertEqual(fin_summary_a['total_expenses'], Decimal('6500.00'))
        self.assertEqual(fin_summary_a['net_profit'], Decimal('-5500.00'))

        # Multi-tenant scoping check: Tenant B summary should be 0
        fin_summary_b = ReportService.get_financial_summary(
            tenant_id=self.tenant_b.id,
            start_date=start_date,
            end_date=end_date
        )
        self.assertEqual(fin_summary_b['total_booked_revenue'], Decimal('0.00'))

        # Occupancy Summary for Tenant A
        occ_summary_a = ReportService.get_occupancy_summary(
            tenant_id=self.tenant_a.id,
            start_date=start_date,
            end_date=end_date
        )
        self.assertEqual(occ_summary_a['total_rooms'], 1)
        self.assertEqual(occ_summary_a['occupied_room_nights'], 10)
        # 10 occupied out of 30 total available room nights = 33.33%
        self.assertAlmostEqual(occ_summary_a['occupancy_rate_percentage'], 33.33, places=1)

    def test_dashboard_analytics_service(self):
        today = date.today()
        # Create an arrival booking today
        booking = BookingService.create_booking(
            tenant=self.tenant_a,
            room=self.room_a,
            guest_name="Today Guest",
            guest_phone="+15551122",
            check_in_date=today,
            check_out_date=today + timedelta(days=2),
            paid_amount=Decimal('100.00')
        )
        BookingService.confirm_booking(booking)

        analytics = ReportService.get_dashboard_analytics(
            tenant_id=self.tenant_a.id,
            property_id=self.prop_a.id,
            period='today'
        )

        self.assertIn('kpis', analytics)
        self.assertIn('operations_pulse', analytics)
        self.assertEqual(analytics['kpis']['total_rooms'], 1)
        self.assertEqual(len(analytics['operations_pulse']['today_arrivals']), 1)
        self.assertEqual(analytics['operations_pulse']['today_arrivals'][0]['guest_name'], "Today Guest")

    def test_financial_suite_reporting_services(self):
        from apps.reports.services.financial_reporting_service import FinancialReportingService

        pnl = FinancialReportingService.get_pnl_report(self.tenant_a.id, period='this_month')
        self.assertIn('gross_revenue', pnl)
        self.assertIn('total_expenses', pnl)

        rev = FinancialReportingService.get_revenue_report(self.tenant_a.id, period='this_month')
        self.assertIn('revenue_by_room_type', rev)

        exp = FinancialReportingService.get_expense_report(self.tenant_a.id, period='this_month')
        self.assertIn('categories_breakdown', exp)

        kpis = FinancialReportingService.get_hospitality_kpi_report(self.tenant_a.id, period='this_month')
        self.assertIn('occupancy_rate', kpis)

        rest = FinancialReportingService.get_restaurant_report(self.tenant_a.id, period='this_month')
        self.assertIn('total_sales', rest)

        rec = FinancialReportingService.get_receivables_report(self.tenant_a.id, period='this_month')
        self.assertIn('total_tax_collected', rec)

        csv_data = FinancialReportingService.export_financial_csv(self.tenant_a.id, report_type='pnl', period='this_month')
        self.assertTrue(len(csv_data) > 0)
        self.assertIn("EXECUTIVE P&L FINANCIAL STATEMENT", csv_data)



