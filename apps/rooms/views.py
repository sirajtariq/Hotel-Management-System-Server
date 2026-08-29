from django.core.cache import cache
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.viewsets import TenantScopedViewSet
from apps.rooms.models import Room, RoomType
from apps.rooms.serializers import (
    RoomSerializer,
    RoomDetailSerializer,
    RoomListSerializer,
    RoomTypeSerializer,
    RoomTypeSelectorSerializer,
    AvailableRoomSelectorSerializer,
)
from apps.rooms.services.room_service import RoomService
from core.permissions import HasTenantAccess, HasModulePermission

class RoomTypeViewSet(TenantScopedViewSet):
    queryset = RoomType.objects.all()
    serializer_class = RoomTypeSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, HasModulePermission]
    action_permissions = {
        'list': 'rooms:view',
        'retrieve': 'rooms:view',
        'dropdown_selector': 'rooms:view',
        'create': 'rooms:manage',
        'update': 'rooms:manage',
        'partial_update': 'rooms:manage',
        'destroy': 'rooms:manage',
    }

    def get_queryset(self):
        qs = super().get_queryset().select_related('property')
        if self.action == 'list':
            return qs.only(
                'id',
                'tenant_id',
                'name',
                'property_id',
                'property__id',
                'property__name',
                'base_price_per_night',
                'hourly_rate',
                'is_hourly_allowed',
                'max_occupancy',
                'amenities',
                'created_at',
            ).order_by('-created_at')
        return qs.order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'dropdown_selector':
            return RoomTypeSelectorSerializer
        return RoomTypeSerializer

    @action(detail=False, methods=['get'], url_path='selector')
    def dropdown_selector(self, request):
        tenant_id = getattr(request.user, 'tenant_id', None) or 'global'
        property_id = request.query_params.get('property_id') or request.query_params.get('propertyId') or request.query_params.get('property') or 'all'
        cache_key = f"tenant_{tenant_id}_room_type_selector_{property_id}"

        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        qs = self.get_queryset().filter(is_active=True).only(
            'id', 'name', 'base_price_per_night', 'hourly_rate', 'is_hourly_allowed', 'amenities', 'max_occupancy'
        ).order_by('name')

        if property_id != 'all' and property_id != 'ALL':
            qs = qs.filter(property_id=property_id)

        serializer = RoomTypeSelectorSerializer(qs, many=True)
        cache.set(cache_key, serializer.data, timeout=900)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tenant = request.user.tenant
        if request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPERADMIN':
            tenant = serializer.validated_data.get('tenant', tenant)

        room_type = RoomService.create_room_type(
            tenant=tenant,
            property_obj=serializer.validated_data['property'],
            name=serializer.validated_data['name'],
            base_price_per_night=serializer.validated_data['base_price_per_night'],
            hourly_rate=serializer.validated_data.get('hourly_rate'),
            is_hourly_allowed=serializer.validated_data.get('is_hourly_allowed', True),
            max_occupancy=serializer.validated_data.get('max_occupancy', 2),
            description=serializer.validated_data.get('description', '')
        )

        response_serializer = self.get_serializer(room_type)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        updated_room_type = RoomService.update_room_type(instance, **serializer.validated_data)
        response_serializer = self.get_serializer(updated_room_type)
        return Response(response_serializer.data)

class RoomViewSet(TenantScopedViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomListSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, HasModulePermission]
    action_permissions = {
        'list': 'rooms:view',
        'available_rooms': 'rooms:view',
        'retrieve': 'rooms:view',
        'create': 'rooms:manage',
        'update': 'rooms:manage',
        'partial_update': 'rooms:manage',
        'destroy': 'rooms:manage',
        'change_status': 'rooms:change_status',
    }

    def get_serializer_class(self):
        if self.action == 'list':
            return RoomListSerializer
        return RoomDetailSerializer

    @action(detail=False, methods=['get'], url_path='available')
    def available_rooms(self, request):
        property_id = request.query_params.get('property_id') or request.query_params.get('propertyId') or request.query_params.get('property')
        qs = self.get_queryset().filter(status='AVAILABLE').select_related('room_type', 'property')

        if property_id and property_id != 'ALL':
            qs = qs.filter(property_id=property_id)

        serializer = AvailableRoomSelectorSerializer(qs, many=True)
        return Response(serializer.data)

    def get_queryset(self):
        qs = super().get_queryset()
        property_param = self.request.query_params.get('property') or self.request.query_params.get('property_id')
        if property_param and property_param != 'ALL':
            qs = qs.filter(property_id=property_param)

        if self.action == 'list':
            return qs.select_related('room_type', 'property', 'tenant').only(
                'id',
                'room_number',
                'floor',
                'hourly_rate',
                'is_hourly_allowed',
                'status',
                'housekeeping_status',
                'amenities',
                'tenant_id',
                'property_id',
                'room_type_id',
                'property__id',
                'property__name',
                'room_type__id',
                'room_type__name',
                'room_type__max_occupancy',
                'room_type__base_price_per_night',
                'room_type__hourly_rate',
                'room_type__is_hourly_allowed',
                'room_type__amenities',
            ).order_by('room_number')
        return qs.select_related('room_type', 'property', 'tenant').order_by('room_number')


    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tenant = request.user.tenant
        if request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPERADMIN':
            tenant = serializer.validated_data.get('tenant', tenant)

        room = RoomService.create_room(
            tenant=tenant,
            property_obj=serializer.validated_data['property'],
            room_type=serializer.validated_data['room_type'],
            room_number=serializer.validated_data['room_number'],
            floor=serializer.validated_data.get('floor', ''),
            status=serializer.validated_data.get('status', 'AVAILABLE'),
            amenities=serializer.validated_data.get('amenities', [])
        )

        response_serializer = self.get_serializer(room)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
