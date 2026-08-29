from django.core.cache import cache
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.viewsets import TenantScopedViewSet
from apps.properties.models import Property
from apps.properties.serializers import (
    PropertyListSerializer,
    PropertyDetailSerializer,
    PropertySelectorSerializer,
)
from apps.properties.services.property_service import PropertyService
from core.permissions import HasTenantAccess, HasModulePermission

class PropertyViewSet(TenantScopedViewSet):
    queryset = Property.objects.all()
    serializer_class = PropertyDetailSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, HasModulePermission]
    action_permissions = {
        'list': 'properties:view',
        'retrieve': 'properties:view',
        'dropdown_selector': 'properties:view',
        'create': 'properties:manage',
        'update': 'properties:manage',
        'partial_update': 'properties:manage',
        'destroy': 'properties:manage',
    }

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == 'list':
            return qs.annotate(
                total_rooms=Count('rooms', distinct=True),
                booked_rooms=Count('rooms', filter=Q(rooms__status__in=['OCCUPIED', 'RESERVED']), distinct=True),
                cleaning_rooms=Count('rooms', filter=Q(rooms__status__in=['CLEANING', 'DIRTY', 'MAINTENANCE']), distinct=True),
                available_rooms=Count('rooms', filter=Q(rooms__status='AVAILABLE'), distinct=True),
            ).order_by('-created_at')
        return qs.order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'list':
            return PropertyListSerializer
        elif self.action == 'dropdown_selector':
            return PropertySelectorSerializer
        return PropertyDetailSerializer

    @action(detail=False, methods=['get'], url_path='selector')
    def dropdown_selector(self, request):
        """High-speed endpoint for booking/expense form dropdowns with in-memory caching"""
        tenant_id = getattr(request.user, 'tenant_id', None) or 'global'
        cache_key = f"tenant_{tenant_id}_property_selector"

        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        qs = self.get_queryset().filter(status='ACTIVE').only('id', 'name', 'city').order_by('name')
        serializer = PropertySelectorSerializer(qs, many=True)
        cache.set(cache_key, serializer.data, timeout=900)
        return Response(serializer.data)

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
