import io
import csv
from datetime import date, datetime
from decimal import Decimal
from django.db.models import Sum, Count
from apps.bookings.models import Booking
from apps.expenses.models import Expense
from apps.properties.models import Property
from apps.staff.models import StaffProfile
from apps.tenants.models import Tenant
from apps.reports.services.report_service import ReportService

class ExportService:
    @staticmethod
    def export_pnl_csv(tenant_id: int, property_id: int = None, start_date: date = None, end_date: date = None) -> str:
        """
        SSOT CSV Exporter for Profit & Loss (P&L) Financial Report with UTF-8 BOM ('\ufeff').
        """
        pnl = ReportService.get_financial_summary(
            tenant_id=tenant_id,
            property_id=property_id,
            start_date=start_date,
            end_date=end_date
        )

        tenant = Tenant.objects.filter(id=tenant_id).first()
        tenant_name = tenant.name if tenant else "Hotel Platform Tenant"
        property_obj = Property.objects.filter(id=property_id).first() if property_id else None
        property_name = property_obj.name if property_obj else "All Properties"

        output = io.StringIO()
        # UTF-8 BOM for Microsoft Excel compatibility
        output.write('\ufeff')

        writer = csv.writer(output)

        # Header Block
        writer.writerow(["PROFIT & LOSS (P&L) FINANCIAL STATEMENT"])
        writer.writerow(["Hotel Client / Tenant:", tenant_name])
        writer.writerow(["Property Scope:", property_name])
        writer.writerow(["Statement Period:", f"{pnl['period_start']} to {pnl['period_end']} ({pnl['period_days']} Days)"])
        writer.writerow(["Generated Timestamp:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        writer.writerow([])

        # Section 1: Revenue Breakdown
        writer.writerow(["1. REVENUE BREAKDOWN", "AMOUNT (PKR)"])
        writer.writerow(["Total Booked Revenue", f"{pnl['total_booked_revenue']:,.2f}"])
        writer.writerow(["Total Collected Cash Revenue", f"{pnl['total_collected_revenue']:,.2f}"])
        receivables = max(Decimal('0.00'), pnl['total_booked_revenue'] - pnl['total_collected_revenue'])
        writer.writerow(["Outstanding Receivables", f"{receivables:,.2f}"])
        writer.writerow([])

        # Section 2: Operational Expenses by Category
        writer.writerow(["2. OPERATIONAL EXPENSES BY CATEGORY", "AMOUNT (PKR)"])
        expense_qs = Expense.objects.filter(
            tenant_id=tenant_id,
            expense_date__gte=pnl['period_start'],
            expense_date__lte=pnl['period_end']
        )
        if property_id:
            expense_qs = expense_qs.filter(property_id=property_id)

        categories_summary = expense_qs.values('category__name').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')

        if categories_summary:
            for cat in categories_summary:
                cat_name = cat['category__name'] or "General Expenses"
                writer.writerow([f"Category: {cat_name} ({cat['count']} items)", f"{cat['total']:,.2f}"])
        else:
            writer.writerow(["No category operational expenses logged in period", "0.00"])

        writer.writerow(["Subtotal Raw Operational Expenses", f"{pnl['raw_operational_expenses']:,.2f}"])
        writer.writerow([])

        # Section 3: Staff Payroll & Property Rent
        writer.writerow(["3. PAYROLL & FIXED OVERHEADS", "AMOUNT (PKR)"])
        writer.writerow(["Staff Payroll Cost (Calculated)", f"{pnl['staff_payroll_expense']:,.2f}"])
        writer.writerow(["Landlord Property Rent (Calculated)", f"{pnl['property_rent_expense']:,.2f}"])
        writer.writerow([])

        # Section 4: Summary Totals
        writer.writerow(["4. FINANCIAL SUMMARY & NET MARGIN", "AMOUNT (PKR)"])
        writer.writerow(["Total Gross Revenue", f"{pnl['total_booked_revenue']:,.2f}"])
        writer.writerow(["Total Expenses & Overheads", f"{pnl['total_expenses']:,.2f}"])
        margin_label = "NET PROFIT" if pnl['net_profit'] >= 0 else "NET LOSS"
        writer.writerow([f"FINAL {margin_label}", f"{pnl['net_profit']:,.2f}"])

        return output.getvalue()
