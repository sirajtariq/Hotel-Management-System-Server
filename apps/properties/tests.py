from decimal import Decimal
from django.test import TestCase
from apps.tenants.services.tenant_service import TenantService
from apps.properties.services.property_service import PropertyService

class PropertyTestCase(TestCase):
    def setUp(self):
        self.tenant = TenantService.create_tenant(name="Urban Apartments")

    def test_create_property_with_monthly_rent(self):
        prop = PropertyService.create_property(
            tenant=self.tenant,
            name="Urban Tower A",
            address="123 Main St",
            city="New York",
            monthly_rent=Decimal('15000.00')
        )
        self.assertEqual(prop.name, "Urban Tower A")
        self.assertEqual(prop.monthly_rent, Decimal('15000.00'))
