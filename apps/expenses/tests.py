from datetime import date
from decimal import Decimal
from django.test import TestCase
from apps.tenants.services.tenant_service import TenantService
from apps.properties.services.property_service import PropertyService
from apps.expenses.services.expense_service import ExpenseService
from apps.expenses.models import AccountHead

class ExpenseTestCase(TestCase):
    def setUp(self):
        self.tenant = TenantService.create_tenant(name="Sunset Villas")
        self.property = PropertyService.create_property(
            tenant=self.tenant,
            name="Villa Sunset",
            address="789 Coast Rd",
            city="Malibu"
        )
        self.account_head = ExpenseService.create_account_head(
            tenant=self.tenant,
            name="Swimming Pool Maintenance",
            description="Pool chemicals and pump servicing"
        )

    def test_default_account_heads_seeded(self):
        heads = AccountHead.objects.filter(tenant=self.tenant)
        self.assertGreaterEqual(heads.count(), 7)

    def test_expense_creation_with_account_head_and_payment_method(self):
        expense = ExpenseService.create_expense(
            tenant=self.tenant,
            property_obj=self.property,
            account_head=self.account_head,
            item_name="Chlorine & Filter Replacement",
            vendor_name="Pool Care Pvt Ltd",
            amount=Decimal('12000.00'),
            payment_method='BANK_TRANSFER',
            receipt_number='REC-9910',
            expense_date=date.today()
        )
        self.assertEqual(expense.account_head.name, "Swimming Pool Maintenance")
        self.assertEqual(expense.vendor_name, "Pool Care Pvt Ltd")
        self.assertEqual(expense.payment_method, "BANK_TRANSFER")
        self.assertEqual(expense.amount, Decimal('12000.00'))

        total = ExpenseService.calculate_total_expenses(tenant_id=self.tenant.id)
        self.assertEqual(total, Decimal('12000.00'))
