from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.viewsets import TenantScopedViewSet
from core.permissions import HasTenantAccess, HasModulePermission
from apps.accounts.models import PaymentAccount, AccountTransaction, AccountTransfer
from apps.accounts.serializers import (
    PaymentAccountSerializer,
    AccountTransactionSerializer,
    AccountTransferSerializer,
    CreateTransferSerializer,
)
from apps.accounts.services.account_service import AccountService


class PaymentAccountViewSet(TenantScopedViewSet):
    queryset = PaymentAccount.objects.all()
    serializer_class = PaymentAccountSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, HasModulePermission]
    action_permissions = {
        'list': 'accounts:view',
        'retrieve': 'accounts:view',
        'create': 'accounts:manage',
        'update': 'accounts:manage',
        'partial_update': 'accounts:manage',
        'destroy': 'accounts:manage',
        'set_as_default': 'accounts:manage',
        'transactions_ledger': 'accounts:view',
    }

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return PaymentAccount.objects.none()

        role_upper = getattr(user, 'role', '').upper()
        is_superadmin = bool(getattr(user, 'is_superuser', False) or role_upper in ['SUPERADMIN', 'SUPER_ADMIN'])
        
        if is_superadmin:
            qs = PaymentAccount.objects.all()
            query_params = getattr(self.request, 'query_params', getattr(self.request, 'GET', {}))
            tenant_id = self.request.headers.get('X-Tenant-ID') or query_params.get('tenant_id') or getattr(user, 'tenant_id', None)
            if tenant_id:
                qs = qs.filter(tenant_id=tenant_id)
        elif getattr(user, 'tenant_id', None):
            qs = PaymentAccount.objects.filter(tenant_id=user.tenant_id)
        else:
            return PaymentAccount.objects.none()
        
        if not user.is_tenant_admin:
            from django.db.models import Q
            assigned_property_ids = user.assigned_properties.values_list('id', flat=True)
            qs = qs.filter(Q(property__isnull=True) | Q(property_id__in=assigned_property_ids))

        account_type = self.request.query_params.get('account_type')
        is_active = self.request.query_params.get('is_active')
        search = self.request.query_params.get('search', '').strip()
        property_id = self.request.query_params.get('property_id')

        if account_type:
            qs = qs.filter(account_type=account_type)
        if is_active is not None:
            if is_active.lower() == 'true':
                qs = qs.filter(is_active=True)
            elif is_active.lower() == 'false':
                qs = qs.filter(is_active=False)
        if property_id:
            from django.db.models import Q
            qs = qs.filter(Q(property__isnull=True) | Q(property_id=property_id))

        if search:
            from django.db.models import Q
            qs = qs.filter(Q(name__icontains=search) | Q(bank_name__icontains=search))

        return qs.annotate(transactions_count=Count('transactions')).order_by('-is_default', 'name')

    def perform_create(self, serializer):
        tenant = getattr(self.request.user, 'tenant', None)
        if not tenant and hasattr(self.request.user, 'tenant_id') and self.request.user.tenant_id:
            from apps.tenants.models import Tenant
            tenant = Tenant.objects.filter(id=self.request.user.tenant_id).first()

        if not tenant:
            from rest_framework import serializers as drf_serializers
            raise drf_serializers.ValidationError({"tenant": "Authenticated user is not linked to any active tenant."})
            
        user = self.request.user
        property_obj = serializer.validated_data.get('property')
        if not user.is_tenant_admin and not property_obj:
            from rest_framework import serializers as drf_serializers
            raise drf_serializers.ValidationError({"property": "Non-Tenant Admins cannot create Global / Chain-wide accounts."})

        serializer.save(tenant=tenant)

    def perform_update(self, serializer):
        user = self.request.user
        property_obj = serializer.validated_data.get('property', serializer.instance.property)
        if not user.is_tenant_admin and not property_obj:
            from rest_framework import serializers as drf_serializers
            raise drf_serializers.ValidationError({"property": "Non-Tenant Admins cannot manage Global / Chain-wide accounts."})
            
        instance = serializer.save()
        if not instance.is_active and instance.is_default:
            instance.is_default = False
            instance.save(update_fields=['is_default'])

    @action(detail=True, methods=['post'], url_path='set-default')
    def set_as_default(self, request, pk=None):
        account = self.get_object()
        tenant = account.tenant
        
        if not account.property:
            # Global account: only tenant admin can set as default
            if not request.user.is_tenant_admin:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("Only Tenant Admin can set a Global account as default.")
            # Unset default for all OTHER global accounts
            PaymentAccount.objects.filter(tenant=tenant, property__isnull=True).update(is_default=False)
        else:
            # Property account: unset default for all OTHER accounts in this property
            PaymentAccount.objects.filter(tenant=tenant, property=account.property).update(is_default=False)
            
        account.is_default = True
        account.save(update_fields=['is_default'])
        serializer = self.get_serializer(account)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='transactions')
    def transactions_ledger(self, request, pk=None):
        account = self.get_object()
        qs = AccountTransaction.objects.filter(tenant=account.tenant, account=account).order_by('-created_at')
        
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = AccountTransactionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = AccountTransactionSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AccountTransferViewSet(TenantScopedViewSet):
    queryset = AccountTransfer.objects.all()
    serializer_class = AccountTransferSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess]

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
        serializer = CreateTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        tenant = getattr(request.user, 'tenant', None)
        if not tenant and hasattr(request.user, 'tenant_id') and request.user.tenant_id:
            from apps.tenants.models import Tenant
            tenant = Tenant.objects.filter(id=request.user.tenant_id).first()

        if not tenant:
            from rest_framework import serializers as drf_serializers
            raise drf_serializers.ValidationError({"tenant": "Authenticated user is not linked to any active tenant."})

        transfer = AccountService.execute_transfer(
            tenant=tenant,
            from_account_id=data['from_account_id'],
            to_account_id=data['to_account_id'],
            amount=data['amount'],
            transfer_date=data.get('transfer_date'),
            reference_number=data.get('reference_number', ''),
            notes=data.get('notes', ''),
            receipt_image=data.get('receipt_image'),
            user=request.user,
        )

        response_serializer = AccountTransferSerializer(transfer)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
