from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

def is_tenant_active(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or getattr(user, 'role', '') == 'SUPERADMIN':
        return True
    if getattr(user, 'tenant', None) and not user.tenant.is_active:
        return False
    return True

def is_tenant_overdue(user, request) -> bool:
    """
    Checks if tenant subscription is OVERDUE for non-superadmin mutation requests.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or getattr(user, 'role', '') == 'SUPERADMIN':
        return False
    if getattr(user, 'tenant', None):
        status = getattr(user.tenant, 'subscription_status', 'PAID')
        if status == 'OVERDUE' and request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return True
    return False

def is_superadmin_direct_mutation(user, request) -> bool:
    """
    Returns True if user is a SuperAdmin attempting write operations without an active impersonation token.
    """
    if not user or not user.is_authenticated:
        return False
    
    is_sa = user.is_superuser or getattr(user, 'role', '') == 'SUPERADMIN'
    if is_sa and request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
        # Check if token carries impersonation claim
        auth_data = getattr(request, 'auth', {})
        is_impersonated = False
        if isinstance(auth_data, dict):
            is_impersonated = auth_data.get('is_impersonated', False)
        elif hasattr(auth_data, 'get'):
            is_impersonated = auth_data.get('is_impersonated', False)
            
        if not is_impersonated:
            return True
    return False

class IsSuperAdmin(permissions.BasePermission):
    """
    Allows access only to global platform SuperAdmins.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPERADMIN')
        )

class IsTenantAdmin(permissions.BasePermission):
    """
    Allows access to Tenant Admins and SuperAdmins.
    Enforces direct mutation safeguard & OVERDUE subscription lock.
    """
    def has_permission(self, request, view):
        if not is_tenant_active(request.user):
            return False

        if is_tenant_overdue(request.user, request):
            raise PermissionDenied("Subscription Expired: Your hotel subscription is OVERDUE. Please contact SuperAdmin to renew service.")

        if is_superadmin_direct_mutation(request.user, request):
            raise PermissionDenied("SuperAdmin Read-Only Safeguard: Direct mutations prohibited. Please use 'Login as Tenant' impersonation mode to perform operational changes.")

        if request.user.is_superuser:
            return True
        return getattr(request.user, 'role', '') in ['SUPERADMIN', 'TENANT_ADMIN']

class IsPropertyManager(permissions.BasePermission):
    """
    Allows access to Property Managers, Tenant Admins, and SuperAdmins.
    """
    def has_permission(self, request, view):
        if not is_tenant_active(request.user):
            return False

        if is_tenant_overdue(request.user, request):
            raise PermissionDenied("Subscription Expired: Your hotel subscription is OVERDUE. Please contact SuperAdmin to renew service.")

        if is_superadmin_direct_mutation(request.user, request):
            raise PermissionDenied("SuperAdmin Read-Only Safeguard: Direct mutations prohibited. Please use 'Login as Tenant' impersonation mode to perform operational changes.")

        if request.user.is_superuser:
            return True
        return getattr(request.user, 'role', '') in ['SUPERADMIN', 'TENANT_ADMIN', 'PROPERTY_MANAGER']

class IsStaffMember(permissions.BasePermission):
    """
    Allows access to Staff members, Property Managers, Tenant Admins, and SuperAdmins.
    """
    def has_permission(self, request, view):
        if not is_tenant_active(request.user):
            return False

        if is_tenant_overdue(request.user, request):
            raise PermissionDenied("Subscription Expired: Your hotel subscription is OVERDUE. Please contact SuperAdmin to renew service.")

        if is_superadmin_direct_mutation(request.user, request):
            raise PermissionDenied("SuperAdmin Read-Only Safeguard: Direct mutations prohibited. Please use 'Login as Tenant' impersonation mode to perform operational changes.")

        if request.user.is_superuser:
            return True
        return getattr(request.user, 'role', '') in ['SUPERADMIN', 'TENANT_ADMIN', 'PROPERTY_MANAGER', 'STAFF']

class HasTenantAccess(permissions.BasePermission):
    """
    Object-level permission checking that the object belongs to the user's tenant.
    """
    def has_object_permission(self, request, view, obj):
        if not is_tenant_active(request.user):
            return False

        if is_tenant_overdue(request.user, request):
            raise PermissionDenied("Subscription Expired: Your hotel subscription is OVERDUE.")

        if request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPERADMIN':
            return True
        
        tenant_id = getattr(request.user, 'tenant_id', None)
        obj_tenant_id = getattr(obj, 'tenant_id', None)
        
        if tenant_id and obj_tenant_id:
            return tenant_id == obj_tenant_id
        return False


class HasModulePermission(permissions.BasePermission):
    """
    Dynamic RBAC permission check based on core/permissions_registry.py.
    - SuperAdmin and TenantAdmin bypass all checks (Full Access).
    - Checks tenant active, overdue, and direct superadmin mutation safeguards.
    - Reads action_permissions dict from ViewSet (e.g. {'list': 'bookings:view'}).
    - Checks if mapped action permission is present in request.user.custom_role.permissions.
    """
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if not is_tenant_active(user):
            return False

        if is_tenant_overdue(user, request):
            raise PermissionDenied("Subscription Expired: Your hotel subscription is OVERDUE. Please contact SuperAdmin to renew service.")

        if is_superadmin_direct_mutation(user, request):
            raise PermissionDenied("SuperAdmin Read-Only Safeguard: Direct mutations prohibited. Please use 'Login as Tenant' impersonation mode to perform operational changes.")

        # SuperAdmins & TenantAdmins have full access bypass
        if user.is_superuser or getattr(user, 'role', '') in ['SUPERADMIN', 'TENANT_ADMIN']:
            return True

        # Check action permissions mapping on ViewSet or required_permission on APIView
        action_perms = getattr(view, 'action_permissions', {})
        action = getattr(view, 'action', None)
        required_perm = action_perms.get(action) if action else getattr(view, 'required_permission', None)

        if not required_perm:
            return True


        # Custom role permission check
        if getattr(user, 'custom_role', None) and user.custom_role:
            user_perms = set(getattr(user.custom_role, 'permissions', []) or [])
            if required_perm in user_perms:
                return True
            return False

        # Legacy fallback if no custom_role is assigned
        role = getattr(user, 'role', '')
        if role == 'PROPERTY_MANAGER':
            if not required_perm.startswith('roles:'):
                return True
        elif role == 'STAFF':
            allowed_staff_actions = {
                'properties:view', 'rooms:view', 'rooms:change_status',
                'bookings:view', 'bookings:create', 'expenses:view',
                'expenses:create', 'staff:view'
            }
            if required_perm in allowed_staff_actions:
                return True

        return False



