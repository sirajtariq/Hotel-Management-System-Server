import io
import csv
from decimal import Decimal
from datetime import date
from django.db import transaction
from django.db.models import Sum
from rest_framework.exceptions import ValidationError
from apps.expenses.models import Expense, AccountHead, ExpenseCategory
from apps.expenses.signals import DEFAULT_ACCOUNT_HEADS
from apps.properties.models import Property
from apps.tenants.models import Tenant
from apps.users.models import User

class ExpenseService:
    @staticmethod
    def auto_seed_default_account_heads(tenant: Tenant):
        """
        Ensures tenant has default Account Heads provisioned.
        """
        for name, description in DEFAULT_ACCOUNT_HEADS:
            AccountHead.objects.get_or_create(
                tenant=tenant,
                name=name,
                defaults={'description': description, 'is_active': True}
            )

    @staticmethod
    def create_category(tenant: Tenant, name: str) -> ExpenseCategory:
        """Legacy helper kept for backward compatibility."""
        if ExpenseCategory.objects.filter(tenant=tenant, name=name).exists():
            raise ValidationError({'name': 'Category with this name already exists.'})
        return ExpenseCategory.objects.create(tenant=tenant, name=name)

    @staticmethod
    def create_account_head(tenant: Tenant, name: str, description: str = '') -> AccountHead:
        if AccountHead.objects.filter(tenant=tenant, name=name).exists():
            raise ValidationError({'name': 'Account Head with this name already exists.'})
        return AccountHead.objects.create(tenant=tenant, name=name, description=description)

    @staticmethod
    @transaction.atomic
    def create_expense(
        tenant: Tenant,
        property_obj: Property,
        account_head: AccountHead = None,
        category: ExpenseCategory = None,
        item_name: str = '',
        amount: Decimal = Decimal('0.00'),
        expense_date: date = None,
        payment_method: str = 'CASH',
        vendor_name: str = '',
        receipt_number: str = '',
        description: str = '',
        created_by: User = None
    ) -> Expense:
        """
        SSOT function to record an expense transaction.
        """
        if property_obj.tenant_id != tenant.id:
            raise ValidationError({'property': 'Property tenant mismatch.'})

        if account_head and account_head.tenant_id != tenant.id:
            raise ValidationError({'account_head': 'Account Head tenant mismatch.'})

        # Fallback: if no account_head passed but tenant has heads, pick or create default
        if not account_head:
            heads = AccountHead.objects.filter(tenant=tenant, is_active=True)
            if not heads.exists():
                ExpenseService.auto_seed_default_account_heads(tenant)
                heads = AccountHead.objects.filter(tenant=tenant, is_active=True)
            
            if category:
                # Try matching by name
                matched = heads.filter(name__icontains=category.name).first()
                account_head = matched or heads.first()
            else:
                account_head = heads.first()

        if amount <= 0:
            raise ValidationError({'amount': 'Expense amount must be greater than 0.'})

        if not expense_date:
            expense_date = date.today()

        expense = Expense.objects.create(
            tenant=tenant,
            property=property_obj,
            account_head=account_head,
            category=category,
            item_name=item_name or account_head.name,
            amount=amount,
            expense_date=expense_date,
            payment_method=payment_method,
            vendor_name=vendor_name,
            receipt_number=receipt_number,
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
    def export_expenses_csv(
        tenant_id: int,
        property_id: int = None,
        start_date: date = None,
        end_date: date = None,
        account_head_id: int = None,
        payment_method: str = None
    ) -> str:
        """
        SSOT function to export Expense records as Excel-compatible CSV with UTF-8 BOM ('\ufeff').
        """
        query = Expense.objects.filter(tenant_id=tenant_id).select_related('property', 'account_head', 'created_by')
        if property_id:
            query = query.filter(property_id=property_id)
        if account_head_id:
            query = query.filter(account_head_id=account_head_id)
        if payment_method:
            query = query.filter(payment_method=payment_method)
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
            "Expense ID", "Expense Date", "Property", "Account Head",
            "Vendor / Paid To", "Payment Method", "Receipt #",
            "Description", "Amount (PKR)", "Logged By", "Recorded At"
        ])

        total_amount = Decimal('0.00')
        count = 0

        for exp in query:
            count += 1
            total_amount += exp.amount
            creator_name = exp.created_by.get_full_name() if exp.created_by else "Staff"
            head_name = exp.account_head.name if exp.account_head else (exp.category.name if exp.category else "General")
            writer.writerow([
                f"EXP-{exp.id:04d}",
                str(exp.expense_date),
                exp.property.name if exp.property else "All Properties",
                head_name,
                exp.vendor_name or "N/A",
                exp.get_payment_method_display(),
                exp.receipt_number or "N/A",
                exp.description or "",
                f"{exp.amount:,.2f}",
                creator_name,
                exp.created_at.strftime("%Y-%m-%d %H:%M") if exp.created_at else ""
            ])

        # Bottom Total Row
        writer.writerow([])
        writer.writerow(["TOTAL SUMMARY", f"{count} Items Recorded", "", "", "", "", "", "TOTAL EXPENSES (PKR):", f"{total_amount:,.2f}"])

        return output.getvalue()
