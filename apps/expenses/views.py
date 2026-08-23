from datetime import datetime
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.viewsets import TenantScopedViewSet
from apps.expenses.models import Expense, ExpenseCategory
from apps.expenses.serializers import ExpenseSerializer, ExpenseCategorySerializer
from apps.expenses.services.expense_service import ExpenseService
from core.permissions import HasTenantAccess, HasModulePermission

class ExpenseCategoryViewSet(TenantScopedViewSet):
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
        return qs.select_related('property', 'category', 'tenant')

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
            category=data['category'],
            item_name=data['item_name'],
            amount=data['amount'],
            expense_date=data['expense_date'],
            vendor_name=data.get('vendor_name', ''),
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
        category_id = request.query_params.get('category_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        csv_content = ExpenseService.export_expenses_csv(
            tenant_id=tenant_id,
            property_id=int(property_id) if property_id else None,
            start_date=start_date,
            end_date=end_date,
            category_id=int(category_id) if category_id else None
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        response = HttpResponse(csv_content, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="expenses-export-{timestamp}.csv"'
        return response
