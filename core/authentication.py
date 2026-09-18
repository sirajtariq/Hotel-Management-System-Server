from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from django.contrib.auth import get_user_model
from apps.tenants.models import Tenant

User = get_user_model()

class CustomJWTAuthentication(JWTAuthentication):
    """
    Optimized JWT Authentication class that uses select_related('tenant', 'custom_role')
    to prevent extra N+1 database queries on every authenticated request.
    Also handles tenant resolution via X-Tenant-ID header / tenant_id param for SuperAdmins.
    """
    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)

        # 👑 Impersonation / Header tenant resolution for SuperAdmin
        if user.is_superuser or getattr(user, 'role', '').upper() in ['SUPERADMIN', 'SUPER_ADMIN']:
            header_tenant_id = request.headers.get('X-Tenant-ID') or request.META.get('HTTP_X_TENANT_ID')
            param_tenant_id = request.query_params.get('tenant_id') if hasattr(request, 'query_params') else request.GET.get('tenant_id')
            token_tenant_id = validated_token.get('tenant_id')

            target_tenant_id = header_tenant_id or param_tenant_id or token_tenant_id
            if target_tenant_id:
                tenant = Tenant.objects.filter(id=target_tenant_id).first()
                if tenant:
                    user.tenant = tenant
                    user.tenant_id = tenant.id
                    request.tenant = tenant

        return user, validated_token

    def get_user(self, validated_token):
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
        except KeyError:
            raise InvalidToken("Token contained no recognizable user identification")

        try:
            user = User.objects.select_related('tenant', 'custom_role').get(**{api_settings.USER_ID_FIELD: user_id})
        except User.DoesNotExist:
            raise AuthenticationFailed("User not found", code="user_not_found")

        if not user.is_active:
            raise AuthenticationFailed("User is inactive", code="user_inactive")

        return user
