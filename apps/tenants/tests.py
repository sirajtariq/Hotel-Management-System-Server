from django.test import TestCase
from rest_framework.test import APIClient
from apps.tenants.models import Tenant
from apps.tenants.services.tenant_service import TenantService
from apps.users.models import User

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

    def test_superadmin_permission_and_header_resolution(self):
        tenant = TenantService.create_tenant(
            name="SuperAdmin Target Hotel",
            subscription_plan="PRO"
        )
        superadmin = User.objects.create_superuser(
            username="superadmin_test",
            email="super@test.com",
            password="SuperPassword123!",
            role="SUPERADMIN"
        )

        client = APIClient()
        client.force_authenticate(user=superadmin)

        # 1. Superadmin listing tenants
        res = client.get('/api/v1/tenants/')
        self.assertEqual(res.status_code, 200)

        # 2. Superadmin accessing tenant-scoped resource with X-Tenant-ID header
        res_staff = client.get('/api/v1/staff/', HTTP_X_TENANT_ID=str(tenant.id))
        self.assertEqual(res_staff.status_code, 200)
