from django.test import TestCase
from apps.tenants.models import Tenant
from apps.tenants.services.tenant_service import TenantService

class TenantTestCase(TestCase):
    def test_create_tenant(self):
        tenant = TenantService.create_tenant(
            name="Grand Plaza Hotels",
            subscription_plan="PREMIUM",
            contact_email="admin@grandplaza.com"
        )
        self.assertEqual(tenant.name, "Grand Plaza Hotels")
        self.assertEqual(tenant.slug, "grand-plaza-hotels")
        self.assertEqual(tenant.subscription_plan, "PREMIUM")
        self.assertTrue(tenant.is_active)
