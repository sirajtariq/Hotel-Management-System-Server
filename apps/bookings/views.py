from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.viewsets import TenantScopedViewSet
from apps.bookings.models import Booking
from apps.bookings.serializers import (
    BookingListSerializer,
    BookingDetailSerializer,
    RecordPaymentSerializer,
)
from apps.bookings.services.booking_service import BookingService, create_booking_with_lock
from core.permissions import HasTenantAccess, HasModulePermission

class BookingViewSet(TenantScopedViewSet):
    queryset = Booking.objects.select_related('property', 'room', 'room__room_type', 'tenant').all()
    serializer_class = BookingDetailSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, HasModulePermission]
    action_permissions = {
        'list': 'bookings:view',
        'retrieve': 'bookings:view',
        'create': 'bookings:create',
        'update': 'bookings:update',
        'partial_update': 'bookings:update',
        'destroy': 'bookings:cancel',
        'cancel': 'bookings:cancel',
        'check_in': 'bookings:update',
        'check_out': 'bookings:update',
        'confirm': 'bookings:update',
        'record_payment': 'bookings:record_payment',
    }

    def get_serializer_class(self):
        if self.action == 'list':
            return BookingListSerializer
        return BookingDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        related = ['property', 'room', 'room__room_type', 'tenant']
        existing_fields = [f.name for f in Booking._meta.get_fields()]
        if 'guest' in existing_fields:
            related.append('guest')

        qs = qs.select_related(*related)

        search = self.request.query_params.get('search')
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(guest_name__icontains=search) |
                Q(guest_phone__icontains=search) |
                Q(room__room_number__icontains=search) |
                Q(id__icontains=search)
            )

        status_param = self.request.query_params.get('status')
        if status_param and status_param != 'ALL':
            qs = qs.filter(status__iexact=status_param)

        property_param = self.request.query_params.get('property') or self.request.query_params.get('property_id')
        if property_param and property_param != 'ALL':
            qs = qs.filter(property_id=property_param)

        if self.action == 'list':
            deferred_fields = ['notes', 'special_requests', 'internal_remarks', 'cancellation_reason']
            to_defer = [field for field in deferred_fields if field in existing_fields]
            if to_defer:
                qs = qs.defer(*to_defer)
            return qs.order_by('-created_at')
        return qs.order_by('-created_at')


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
        booking = BookingService.create_booking(
            tenant=tenant,
            room=data['room'],
            guest_name=data['guest_name'],
            guest_phone=data['guest_phone'],
            booking_type=data.get('booking_type', 'NIGHTLY'),
            check_in_dt=data.get('check_in'),
            check_out_dt=data.get('check_out'),
            check_in_date=data.get('check_in_date'),
            check_out_date=data.get('check_out_date'),
            guest_email=data.get('guest_email', ''),
            nightly_rate=data.get('nightly_rate'),
            rate_applied=data.get('rate_applied'),
            subtotal_amount=data.get('subtotal_amount'),
            discount_type=data.get('discount_type', 'FLAT'),
            discount_value=data.get('discount_value', 0.0),
            discount_amount=data.get('discount_amount'),
            tax_rate=data.get('tax_rate', 0.0),
            tax_amount=data.get('tax_amount'),
            total_amount=data.get('total_amount'),
            paid_amount=data.get('paid_amount', 0.0),
            total_duration=data.get('total_duration', '')
        )

        response_serializer = self.get_serializer(booking)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='confirm')
    def confirm(self, request, pk=None):
        booking = self.get_object()
        updated_booking = BookingService.confirm_booking(booking)
        serializer = self.get_serializer(updated_booking)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='check-in')
    def check_in(self, request, pk=None):
        booking = self.get_object()
        updated_booking = BookingService.check_in(booking)
        return Response({
            "success": True,
            "message": f"Guest {updated_booking.guest_name} checked in successfully.",
            "id": updated_booking.id,
            "status": "CHECKED_IN",
            "roomStatus": "OCCUPIED"
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='check-out')
    def check_out(self, request, pk=None):
        booking = self.get_object()
        updated_booking = BookingService.check_out(booking)
        return Response({
            "success": True,
            "message": f"Guest {updated_booking.guest_name} checked out successfully.",
            "id": updated_booking.id,
            "status": "CHECKED_OUT",
            "roomStatus": "AVAILABLE",
            "housekeepingStatus": "DIRTY"
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        booking = self.get_object()
        updated_booking = BookingService.cancel_booking(booking)
        serializer = self.get_serializer(updated_booking)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='record-payment')
    def record_payment(self, request, pk=None):
        booking = self.get_object()
        serializer = RecordPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated_booking = BookingService.record_payment(
            booking=booking,
            amount=serializer.validated_data['amount']
        )
        response_serializer = self.get_serializer(updated_booking)
        return Response(response_serializer.data)
