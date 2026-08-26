from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.viewsets import TenantScopedViewSet
from core.permissions import HasTenantAccess
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
    permission_classes = [IsAuthenticated, HasTenantAccess]

    def get_queryset(self):
        qs = super().get_queryset()
        account_type = self.request.query_params.get('account_type')
        is_active = self.request.query_params.get('is_active')
        search = self.request.query_params.get('search', '').strip()

        if account_type:
            qs = qs.filter(account_type=account_type)
        if is_active is not None:
            if is_active.lower() == 'true':
                qs = qs.filter(is_active=True)
            elif is_active.lower() == 'false':
                qs = qs.filter(is_active=False)

        if search:
            qs = qs.filter(name__icontains=search) | qs.filter(bank_name__icontains=search)

        return qs

    def perform_create(self, serializer):
        tenant = self.request.user.tenant
        serializer.save(tenant=tenant)

    @action(detail=True, methods=['post'], url_path='set-default')
    def set_as_default(self, request, pk=None):
        account = self.get_object()
        tenant = account.tenant
        PaymentAccount.objects.filter(tenant=tenant).update(is_default=False)
        account.is_default = True
        account.save(update_fields=['is_default'])
        serializer = self.get_serializer(account)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='transactions')
    def transactions_ledger(self, request, pk=None):
        account = self.get_object()
        qs = AccountTransaction.objects.filter(tenant=account.tenant, account=account).order_by('-created_at')
        serializer = AccountTransactionSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AccountTransferViewSet(TenantScopedViewSet):
    queryset = AccountTransfer.objects.all()
    serializer_class = AccountTransferSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess]

    def create(self, request, *args, **kwargs):
        serializer = CreateTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        transfer = AccountService.execute_transfer(
            tenant=request.user.tenant,
            from_account_id=data['from_account_id'],
            to_account_id=data['to_account_id'],
            amount=data['amount'],
            transfer_date=data.get('transfer_date'),
            reference_number=data.get('reference_number', ''),
            notes=data.get('notes', ''),
            user=request.user,
        )

        response_serializer = AccountTransferSerializer(transfer)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
