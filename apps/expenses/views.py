from datetime import datetime
from decimal import Decimal
from django.db.models import Count, Sum, Value, Q
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.viewsets import TenantScopedViewSet
from apps.expenses.models import Expense, AccountHead, ExpenseCategory
from apps.expenses.serializers import ExpenseSerializer, AccountHeadSerializer, ExpenseCategorySerializer
from apps.expenses.services.expense_service import ExpenseService
from core.permissions import HasTenantAccess, HasModulePermission

class AccountHeadViewSet(TenantScopedViewSet):
    queryset = AccountHead.objects.all()
    serializer_class = AccountHeadSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, HasModulePermission]
    action_permissions = {
        'list': 'expenses:view',
        'retrieve': 'expenses:view',
        'create': 'expenses:create',
        'update': 'expenses:create',
        'partial_update': 'expenses:create',
        'destroy': 'expenses:delete',
        'toggle_active': 'expenses:create',
    }

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        # Auto-seed default heads for tenant if they don't exist yet
        if user and user.is_authenticated and getattr(user, 'tenant', None):
            if not AccountHead.objects.filter(tenant=user.tenant).exists():
                ExpenseService.auto_seed_default_account_heads(user.tenant)
                qs = super().get_queryset()

        search = self.request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))

        return qs.annotate(
            expenses_count=Count('expenses'),
            total_spent_amount=Coalesce(Sum('expenses__amount'), Value(Decimal('0.00')))
        ).order_by('name')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tenant = request.user.tenant
        if request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPERADMIN':
            tenant = serializer.validated_data.get('tenant', tenant)

        head = ExpenseService.create_account_head(
            tenant=tenant,
            name=serializer.validated_data['name'],
            description=serializer.validated_data.get('description', '')
        )
        response_serializer = self.get_serializer(head)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='toggle-active')
    def toggle_active(self, request, pk=None):
        head = self.get_object()
        head.is_active = not head.is_active
        head.save(update_fields=['is_active'])
        serializer = self.get_serializer(head)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ExpenseCategoryViewSet(TenantScopedViewSet):
    """Legacy Category ViewSet kept for backward compatibility."""
    queryset = ExpenseCategory.objects.all()
    serializer_class = ExpenseCategorySerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, HasModulePermission]
    action_permissions = {
        'list': 'expenses:view',
        'retrieve': 'expenses:view',
        'create': 'expenses:create',
        'update': 'expenses:create',
        'partial_update': 'expenses:create',
        'destroy': 'expenses:delete',
    }

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tenant = request.user.tenant
        if request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPERADMIN':
            tenant = serializer.validated_data.get('tenant', tenant)

        category = ExpenseService.create_category(
            tenant=tenant,
            name=serializer.validated_data['name']
        )
        response_serializer = self.get_serializer(category)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ExpenseViewSet(TenantScopedViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, HasModulePermission]
    action_permissions = {
        'list': 'expenses:view',
        'retrieve': 'expenses:view',
        'create': 'expenses:create',
        'update': 'expenses:create',
        'partial_update': 'expenses:create',
        'destroy': 'expenses:delete',
        'export_csv': 'expenses:view',
    }

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.select_related('property', 'account_head', 'category', 'tenant', 'created_by')

        account_head_id = self.request.query_params.get('account_head_id')
        payment_method = self.request.query_params.get('payment_method')
        property_id = self.request.query_params.get('property_id')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        search = self.request.query_params.get('search', '').strip()

        if account_head_id:
            qs = qs.filter(account_head_id=account_head_id)
        if payment_method:
            qs = qs.filter(payment_method=payment_method)
        if property_id:
            qs = qs.filter(property_id=property_id)
        if start_date:
            qs = qs.filter(expense_date__gte=start_date)
        if end_date:
            qs = qs.filter(expense_date__lte=end_date)
        if search:
            qs = qs.filter(
                Q(vendor_name__icontains=search) |
                Q(item_name__icontains=search) |
                Q(description__icontains=search) |
                Q(receipt_number__icontains=search) |
                Q(account_head__name__icontains=search)
            )

        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tenant = request.user.tenant
        if request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPERADMIN':
            tenant = serializer.validated_data.get('tenant', tenant)

        data = serializer.validated_data
        expense = ExpenseService.create_expense(
            tenant=tenant,
            property_obj=data['property'],
            account_head=data.get('account_head'),
            category=data.get('category'),
            item_name=data.get('item_name', ''),
            amount=data['amount'],
            expense_date=data.get('expense_date'),
            payment_method=data.get('payment_method', 'CASH'),
            vendor_name=data.get('vendor_name', ''),
            receipt_number=data.get('receipt_number', ''),
            description=data.get('description', ''),
            created_by=request.user
        )

        response_serializer = self.get_serializer(expense)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='export_csv')
    def export_csv(self, request):
        tenant_id = request.user.tenant_id
        if (request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPERADMIN') and request.query_params.get('tenant_id'):
            tenant_id = int(request.query_params.get('tenant_id'))

        property_id = request.query_params.get('property_id')
        account_head_id = request.query_params.get('account_head_id')
        payment_method = request.query_params.get('payment_method')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        csv_content = ExpenseService.export_expenses_csv(
            tenant_id=tenant_id,
            property_id=int(property_id) if property_id else None,
            start_date=start_date,
            end_date=end_date,
            account_head_id=int(account_head_id) if account_head_id else None,
            payment_method=payment_method
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        response = HttpResponse(csv_content, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="expenses-export-{timestamp}.csv"'
        return response
