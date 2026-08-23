from rest_framework import viewsets, exceptions
from core.permissions import HasTenantAccess

class TenantScopedViewSet(viewsets.ModelViewSet):
    """
    Reusable ViewSet enforcing tenant-level multi-tenant isolation.
    Automatically scopes get_queryset() to request.user.tenant_id for non-SuperAdmins.
    Automatically assigns request.user.tenant to created objects if applicable.
    """
    permission_classes = [HasTenantAccess]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        if not user or not user.is_authenticated:
            return queryset.none()

        # SuperAdmin bypasses tenant scoping, but can filter by tenant_id query param if provided
        if user.is_superuser or getattr(user, 'role', '') == 'SUPERADMIN':
            tenant_param = self.request.query_params.get('tenant_id')
            if tenant_param and hasattr(queryset.model, 'tenant'):
                return queryset.filter(tenant_id=tenant_param)
            return queryset

        # Tenant users MUST only access their tenant's data
        if hasattr(queryset.model, 'tenant') and getattr(user, 'tenant_id', None):
            return queryset.filter(tenant_id=user.tenant_id)

        return queryset.none()

    def perform_create(self, serializer):
        user = self.request.user
        model = serializer.Meta.model

        # If model is tenant-scoped
        if hasattr(model, 'tenant'):
            if user.is_superuser or getattr(user, 'role', '') == 'SUPERADMIN':
                # SuperAdmin can pass tenant explicitly or use own
                if 'tenant' not in serializer.validated_data and getattr(user, 'tenant', None):
                    serializer.save(tenant=user.tenant)
                else:
                    serializer.save()
            else:
                if not getattr(user, 'tenant', None):
                    raise exceptions.PermissionDenied("User must belong to a tenant to create tenant-scoped resources.")
                serializer.save(tenant=user.tenant)
        else:
            serializer.save()
