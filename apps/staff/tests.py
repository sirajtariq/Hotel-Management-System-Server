from datetime import date
from decimal import Decimal
from django.test import TestCase
from apps.tenants.services.tenant_service import TenantService
from apps.properties.services.property_service import PropertyService
from apps.staff.services.staff_service import StaffService

class StaffTestCase(TestCase):
    def setUp(self):
        self.tenant = TenantService.create_tenant(name="Apex Hospitality")
        self.property = PropertyService.create_property(
            tenant=self.tenant,
            name="Apex Heights",
            address="100 Peak St",
            city="Denver"
        )

    def test_standalone_staff_creation(self):
        # Cleaner without user login account
        staff = StaffService.create_staff_member(
            tenant=self.tenant,
            property_obj=self.property,
            name="Maria Gonzalez",
            department="Housekeeping",
            position="Senior Cleaner",
            phone="+15551122",
            monthly_salary=Decimal('3200.00'),
            hired_date=date.today(),
            user=None  # Standalone, no login account needed
        )

        self.assertEqual(staff.name, "Maria Gonzalez")
        self.assertIsNone(staff.user)
        self.assertEqual(staff.monthly_salary, Decimal('3200.00'))

        payroll = StaffService.calculate_monthly_payroll(tenant_id=self.tenant.id)
        self.assertEqual(payroll, Decimal('3200.00'))
