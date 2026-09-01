from rest_framework import viewsets, exceptions
from core.permissions import HasTenantAccess

class TenantScopedViewSet(viewsets.ModelViewSet):
    """
    Reusable ViewSet enforcing tenant-level multi-tenant isolation.
    Automatically scopes get_queryset() to request.user.tenant_id for non-SuperAdmins.
    Allows SuperAdmin unrestricted access across all tenants and properties.
    """
    permission_classes = [HasTenantAccess]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        if not user or not user.is_authenticated:
            return queryset.none()

        # 👑 1. SuperAdmin: Unrestricted access to everything (optional filter via query params)
        if user.is_superuser or getattr(user, 'role', '') == 'SUPERADMIN':
            tenant_id = self.request.query_params.get('tenant_id')
            property_id = self.request.query_params.get('property_id')
            if tenant_id and hasattr(queryset.model, 'tenant'):
                queryset = queryset.filter(tenant_id=tenant_id)
            if property_id and hasattr(queryset.model, 'property'):
                queryset = queryset.filter(property_id=property_id)
            return queryset

        # 2. Scope by Tenant ID
        if hasattr(queryset.model, 'tenant') and getattr(user, 'tenant_id', None):
            queryset = queryset.filter(tenant_id=user.tenant_id)
        else:
            return queryset.none()

        # 3. Property-level RBAC Scoping for Non-Admins
        is_admin = getattr(user, 'is_tenant_admin', False) or getattr(user, 'role', '') in ['SUPERADMIN', 'TENANT_ADMIN']
        if not is_admin and hasattr(queryset.model, 'property'):
            prop_ids = set()

            if hasattr(user, 'assigned_properties') and user.assigned_properties.exists():
                prop_ids.update(user.assigned_properties.values_list('id', flat=True))

            if hasattr(user, 'staff_profile') and user.staff_profile and user.staff_profile.property_id:
                prop_ids.add(user.staff_profile.property_id)

            if getattr(user, 'assigned_property_id', None):
                prop_ids.add(user.assigned_property_id)
            elif getattr(user, 'property_id', None):
                prop_ids.add(user.property_id)

            if prop_ids:
                queryset = queryset.filter(property_id__in=list(prop_ids))
            else:
                return queryset.none()

        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        model = getattr(serializer.Meta, 'model', None)

        # If model is tenant-scoped
        if model and hasattr(model, 'tenant'):
            tenant = getattr(user, 'tenant', None)
            if not tenant and hasattr(user, 'tenant_id') and user.tenant_id:
                from apps.tenants.models import Tenant
                tenant = Tenant.objects.filter(id=user.tenant_id).first()

            if user.is_superuser or getattr(user, 'role', '') == 'SUPERADMIN':
                if 'tenant' not in serializer.validated_data or not serializer.validated_data.get('tenant'):
                    if tenant:
                        serializer.save(tenant=tenant)
                    elif 'tenant_id' in self.request.data:
                        serializer.save(tenant_id=self.request.data['tenant_id'])
                    else:
                        serializer.save()
                else:
                    serializer.save()
            else:
                if not tenant:
                    raise exceptions.PermissionDenied("User must belong to a tenant to create tenant-scoped resources.")
                serializer.save(tenant=tenant)
        else:
            serializer.save()
