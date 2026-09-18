from apps.tenants.models import Tenant

class TenantResolutionMiddleware:
    """
    Middleware that resolves the active tenant for requests when impersonation headers
    (e.g. X-Tenant-ID or HTTP_X_TENANT_ID) or query parameters (tenant_id) are present.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            user = request.user
            if user.is_superuser or getattr(user, 'role', '').upper() in ['SUPERADMIN', 'SUPER_ADMIN']:
                header_tenant_id = request.headers.get('X-Tenant-ID') or request.META.get('HTTP_X_TENANT_ID')
                param_tenant_id = request.GET.get('tenant_id')
                target_tenant_id = header_tenant_id or param_tenant_id

                if target_tenant_id:
                    tenant = Tenant.objects.filter(id=target_tenant_id).first()
                    if tenant:
                        user.tenant = tenant
                        user.tenant_id = tenant.id
                        request.tenant = tenant

        return self.get_response(request)
