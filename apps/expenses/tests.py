from datetime import date
from decimal import Decimal
from django.test import TestCase
from apps.tenants.services.tenant_service import TenantService
from apps.properties.services.property_service import PropertyService
from apps.expenses.services.expense_service import ExpenseService

class ExpenseTestCase(TestCase):
    def setUp(self):
        self.tenant = TenantService.create_tenant(name="Sunset Villas")
        self.property = PropertyService.create_property(
            tenant=self.tenant,
            name="Villa Sunset",
            address="789 Coast Rd",
            city="Malibu"
        )
        self.category = ExpenseService.create_category(tenant=self.tenant, name="Maintenance & Supplies")

    def test_expense_creation_with_vendor_and_item_name(self):
        expense = ExpenseService.create_expense(
            tenant=self.tenant,
            property_obj=self.property,
            category=self.category,
            item_name="Air Conditioner Filter Replacement",
            vendor_name="HVAC Supplies Corp",
            amount=Decimal('450.00'),
            expense_date=date.today()
        )
        self.assertEqual(expense.item_name, "Air Conditioner Filter Replacement")
        self.assertEqual(expense.vendor_name, "HVAC Supplies Corp")
        self.assertEqual(expense.amount, Decimal('450.00'))

        total = ExpenseService.calculate_total_expenses(tenant_id=self.tenant.id)
        self.assertEqual(total, Decimal('450.00'))
