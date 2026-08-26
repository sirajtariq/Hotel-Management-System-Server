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
from apps.bookings.services.booking_service import BookingService
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
        return qs.select_related('property', 'room', 'room__room_type', 'tenant')


    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tenant = request.user.tenant
        if request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPERADMIN':
            tenant = serializer.validated_data.get('tenant', tenant)

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
        serializer = self.get_serializer(updated_booking)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='check-out')
    def check_out(self, request, pk=None):
        booking = self.get_object()
        updated_booking = BookingService.check_out(booking)
        serializer = self.get_serializer(updated_booking)
        return Response(serializer.data)

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
