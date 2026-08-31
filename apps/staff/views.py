from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.viewsets import TenantScopedViewSet
from apps.staff.models import StaffProfile
from apps.staff.serializers import StaffProfileSerializer
from apps.staff.services.staff_service import StaffService
from core.permissions import HasTenantAccess, HasModulePermission

class StaffProfileViewSet(TenantScopedViewSet):
    queryset = StaffProfile.objects.all()
    serializer_class = StaffProfileSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, HasModulePermission]
    action_permissions = {
        'list': 'staff:view',
        'retrieve': 'staff:view',
        'create': 'staff:manage',
        'update': 'staff:manage',
        'partial_update': 'staff:manage',
        'destroy': 'staff:manage',
    }

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related('property', 'tenant', 'user', 'user__custom_role')

    def perform_create(self, serializer):
        tenant = getattr(self.request.user, 'tenant', None)
        if not tenant and hasattr(self.request.user, 'tenant_id') and self.request.user.tenant_id:
            from apps.tenants.models import Tenant
            tenant = Tenant.objects.filter(id=self.request.user.tenant_id).first()

        if not tenant:
            from rest_framework import serializers as drf_serializers
            raise drf_serializers.ValidationError({"tenant": "Authenticated user is not linked to any active tenant."})

        serializer.save(tenant=tenant)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tenant = getattr(request.user, 'tenant', None)
        if not tenant and hasattr(request.user, 'tenant_id') and request.user.tenant_id:
            from apps.tenants.models import Tenant
            tenant = Tenant.objects.filter(id=request.user.tenant_id).first()

        if request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPERADMIN':
            tenant = serializer.validated_data.get('tenant', tenant)

        if not tenant:
            from rest_framework import serializers as drf_serializers
            raise drf_serializers.ValidationError({"tenant": "Authenticated user is not linked to any active tenant."})

        data = serializer.validated_data
        staff = StaffService.create_staff_member(
            tenant=tenant,
            name=data['name'],
            position=data['position'],
            phone_number=data.get('phone_number', ''),
            property_obj=data.get('property'),
            monthly_salary=data.get('monthly_salary', 0.0),
            department=data.get('department', ''),
            hired_date=data.get('hired_date'),
            is_active=data.get('is_active', True),
            enable_login=data.get('enable_login', False),
            username=data.get('login_username'),
            email=data.get('login_email'),
            password=data.get('password'),
            custom_role_id=data.get('custom_role_id'),
        )

        response_serializer = self.get_serializer(staff)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        updated_staff = StaffService.update_staff_member(
            staff_profile=instance,
            name=data.get('name'),
            position=data.get('position'),
            phone_number=data.get('phone_number'),
            property_obj=data.get('property'),
            monthly_salary=data.get('monthly_salary'),
            department=data.get('department'),
            hired_date=data.get('hired_date'),
            is_active=data.get('is_active'),
            enable_login=data.get('enable_login'),
            username=data.get('login_username'),
            email=data.get('login_email'),
            password=data.get('password'),
            custom_role_id=data.get('custom_role_id'),
        )

        response_serializer = self.get_serializer(updated_staff)
        return Response(response_serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        StaffService.delete_staff_member(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
