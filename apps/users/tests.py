from django.test import TestCase
from apps.tenants.services.tenant_service import TenantService
from apps.users.services.user_service import UserService

class UserTestCase(TestCase):
    def setUp(self):
        self.tenant = TenantService.create_tenant(name="Oceanic Resort")

    def test_create_tenant_admin(self):
        user = UserService.create_user(
            username="oceanic_admin",
            email="admin@oceanic.com",
            password="SecurePassword123!",
            role="TENANT_ADMIN",
            tenant_id=self.tenant.id
        )
        self.assertEqual(user.role, "TENANT_ADMIN")
        self.assertEqual(user.tenant.id, self.tenant.id)

    def test_jwt_token_generation(self):
        user = UserService.create_user(
            username="oceanic_mgr",
            email="mgr@oceanic.com",
            password="SecurePassword123!",
            role="PROPERTY_MANAGER",
            tenant_id=self.tenant.id
        )
        tokens = UserService.generate_tokens_for_user(user)
        self.assertIn('access', tokens)
        self.assertIn('refresh', tokens)
