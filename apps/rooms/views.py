from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.viewsets import TenantScopedViewSet
from apps.rooms.models import Room, RoomType
from apps.rooms.serializers import (
    RoomSerializer,
    RoomTypeSerializer,
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
        'create': 'rooms:manage',
        'update': 'rooms:manage',
        'partial_update': 'rooms:manage',
        'destroy': 'rooms:manage',
    }

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
            max_occupancy=serializer.validated_data.get('max_occupancy', 2),
            description=serializer.validated_data.get('description', '')
        )

        response_serializer = self.get_serializer(room_type)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

class RoomViewSet(TenantScopedViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
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
        if property_param:
            qs = qs.filter(property_id=property_param)
        return qs.select_related('property', 'room_type', 'tenant')


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
            status=serializer.validated_data.get('status', 'AVAILABLE')
        )

        response_serializer = self.get_serializer(room)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
