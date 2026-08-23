import io
import csv
from decimal import Decimal
from datetime import date, datetime
from django.db.models import Sum
from rest_framework.exceptions import ValidationError
from apps.expenses.models import Expense, ExpenseCategory
from apps.properties.models import Property
from apps.tenants.models import Tenant
from apps.users.models import User

class ExpenseService:
    @staticmethod
    def create_category(tenant: Tenant, name: str) -> ExpenseCategory:
        if ExpenseCategory.objects.filter(tenant=tenant, name=name).exists():
            raise ValidationError({'name': 'Category with this name already exists.'})
        return ExpenseCategory.objects.create(tenant=tenant, name=name)

    @staticmethod
    def create_expense(tenant: Tenant, property_obj: Property, category: ExpenseCategory, item_name: str, amount: Decimal, expense_date: date, vendor_name: str = '', description: str = '', created_by: User = None) -> Expense:
        """
        SSOT function to record an expense.
        """
        if property_obj.tenant_id != tenant.id or category.tenant_id != tenant.id:
            raise ValidationError({'tenant': 'Property or Category tenant mismatch.'})

        if amount <= 0:
            raise ValidationError({'amount': 'Expense amount must be greater than 0.'})

        expense = Expense.objects.create(
            tenant=tenant,
            property=property_obj,
            category=category,
            item_name=item_name,
            vendor_name=vendor_name,
            amount=amount,
            expense_date=expense_date,
            description=description,
            created_by=created_by
        )
        return expense

    @staticmethod
    def calculate_total_expenses(tenant_id: int, property_id: int = None, start_date: date = None, end_date: date = None) -> Decimal:
        """
        SSOT function to compute total raw operational expenses for financial reporting.
        """
        query = Expense.objects.filter(tenant_id=tenant_id)
        if property_id:
            query = query.filter(property_id=property_id)
        if start_date:
            query = query.filter(expense_date__gte=start_date)
        if end_date:
            query = query.filter(expense_date__lte=end_date)

        total = query.aggregate(total=Sum('amount'))['total']
        return total or Decimal('0.0')

    @staticmethod
    def export_expenses_csv(tenant_id: int, property_id: int = None, start_date: date = None, end_date: date = None, category_id: int = None) -> str:
        """
        SSOT function to export Expense records as Excel-compatible CSV with UTF-8 BOM ('\ufeff').
        """
        query = Expense.objects.filter(tenant_id=tenant_id).select_related('property', 'category', 'created_by')
        if property_id:
            query = query.filter(property_id=property_id)
        if category_id:
            query = query.filter(category_id=category_id)
        if start_date:
            query = query.filter(expense_date__gte=start_date)
        if end_date:
            query = query.filter(expense_date__lte=end_date)

        query = query.order_by('-expense_date', '-id')

        output = io.StringIO()
        output.write('\ufeff')  # UTF-8 BOM for Excel compatibility

        writer = csv.writer(output)

        # Header Columns
        writer.writerow([
            "Expense ID", "Expense Date", "Property", "Category",
            "Item Name", "Vendor Name", "Description", "Amount (PKR)", "Logged By", "Recorded At"
        ])

        total_amount = Decimal('0.00')
        count = 0

        for exp in query:
            count += 1
            total_amount += exp.amount
            creator_name = exp.created_by.get_full_name() if exp.created_by else "System"
            writer.writerow([
                f"EXP-{exp.id:04d}",
                str(exp.expense_date),
                exp.property.name if exp.property else "All Properties",
                exp.category.name if exp.category else "General",
                exp.item_name,
                exp.vendor_name or "N/A",
                exp.description or "",
                f"{exp.amount:,.2f}",
                creator_name,
                exp.created_at.strftime("%Y-%m-%d %H:%M") if exp.created_at else ""
            ])

        # Bottom Total Row
        writer.writerow([])
        writer.writerow(["TOTAL SUMMARY", f"{count} Items Recorded", "", "", "", "", "TOTAL EXPENSES (PKR):", f"{total_amount:,.2f}"])

        return output.getvalue()
