from django.db.models import Count
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.viewsets import TenantScopedViewSet
from apps.properties.models import Property
from apps.properties.serializers import PropertySerializer
from apps.properties.services.property_service import PropertyService
from core.permissions import HasTenantAccess, HasModulePermission

class PropertyViewSet(TenantScopedViewSet):
    queryset = Property.objects.all()
    serializer_class = PropertySerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, HasModulePermission]
    action_permissions = {
        'list': 'properties:view',
        'retrieve': 'properties:view',
        'create': 'properties:manage',
        'update': 'properties:manage',
        'partial_update': 'properties:manage',
        'destroy': 'properties:manage',
    }


    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related('tenant').annotate(total_rooms=Count('rooms', distinct=True))


    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tenant = request.user.tenant
        if request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPERADMIN':
            tenant = serializer.validated_data.get('tenant', tenant)

        property_obj = PropertyService.create_property(
            tenant=tenant,
            **serializer.validated_data
        )

        response_serializer = self.get_serializer(property_obj)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        updated_property = PropertyService.update_property(instance, **serializer.validated_data)
        response_serializer = self.get_serializer(updated_property)
        return Response(response_serializer.data)
