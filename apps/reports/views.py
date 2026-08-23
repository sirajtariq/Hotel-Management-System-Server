from datetime import datetime
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from apps.reports.serializers import (
    ReportQuerySerializer,
    FinancialReportResponseSerializer,
    OccupancyReportResponseSerializer,
    DashboardAnalyticsQuerySerializer,
    DashboardAnalyticsResponseSerializer,
    FinancialFilterQuerySerializer
)
from apps.reports.services.report_service import ReportService
from apps.reports.services.export_service import ExportService
from apps.reports.services.financial_reporting_service import FinancialReportingService
from core.permissions import HasTenantAccess, HasModulePermission

class FinancialReportView(APIView):
    permission_classes = [IsAuthenticated, HasTenantAccess, HasModulePermission]
    required_permission = 'reports:view_pnl'

    @extend_schema(
        parameters=[ReportQuerySerializer],
        responses={200: FinancialReportResponseSerializer}
    )
    def get(self, request):
        query_serializer = ReportQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        params = query_serializer.validated_data

        tenant_id = request.user.tenant_id
        if (request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPERADMIN') and request.query_params.get('tenant_id'):
            tenant_id = int(request.query_params.get('tenant_id'))

        if not tenant_id:
            return Response(
                {'error': {'code': 'tenant_required', 'message': 'Tenant context is required for report generation.'}},
                status=status.HTTP_400_BAD_REQUEST
            )

        financial_data = ReportService.get_financial_summary(
            tenant_id=tenant_id,
            property_id=params.get('property_id'),
            start_date=params.get('start_date'),
            end_date=params.get('end_date')
        )
        response_serializer = FinancialReportResponseSerializer(financial_data)
        return Response(response_serializer.data)

class PnlExportView(APIView):
    permission_classes = [IsAuthenticated, HasTenantAccess, HasModulePermission]
    required_permission = 'reports:export'

    def get(self, request):
        query_serializer = ReportQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        params = query_serializer.validated_data

        tenant_id = request.user.tenant_id
        if (request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPERADMIN') and request.query_params.get('tenant_id'):
            tenant_id = int(request.query_params.get('tenant_id'))

        if not tenant_id:
            return Response(
                {'error': {'code': 'tenant_required', 'message': 'Tenant context is required for P&L export.'}},
                status=status.HTTP_400_BAD_REQUEST
            )

        csv_content = ExportService.export_pnl_csv(
            tenant_id=tenant_id,
            property_id=params.get('property_id'),
            start_date=params.get('start_date'),
            end_date=params.get('end_date')
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        response = HttpResponse(csv_content, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="pnl-statement-{timestamp}.csv"'
        return response

class OccupancyReportView(APIView):
    permission_classes = [IsAuthenticated, HasTenantAccess, HasModulePermission]
    required_permission = 'reports:view_pnl'

    @extend_schema(
        parameters=[ReportQuerySerializer],
        responses={200: OccupancyReportResponseSerializer}
    )
    def get(self, request):
        query_serializer = ReportQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        params = query_serializer.validated_data

        tenant_id = request.user.tenant_id
        if (request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPERADMIN') and request.query_params.get('tenant_id'):
            tenant_id = int(request.query_params.get('tenant_id'))

        if not tenant_id:
            return Response(
                {'error': {'code': 'tenant_required', 'message': 'Tenant context is required for report generation.'}},
                status=status.HTTP_400_BAD_REQUEST
            )

        occupancy_data = ReportService.get_occupancy_summary(
            tenant_id=tenant_id,
            property_id=params.get('property_id'),
            start_date=params.get('start_date'),
            end_date=params.get('end_date')
        )
        response_serializer = OccupancyReportResponseSerializer(occupancy_data)
        return Response(response_serializer.data)

class DashboardAnalyticsView(APIView):
    permission_classes = [IsAuthenticated, HasTenantAccess, HasModulePermission]
    required_permission = 'reports:view_pnl'

    @extend_schema(
        parameters=[DashboardAnalyticsQuerySerializer],
        responses={200: DashboardAnalyticsResponseSerializer}
    )
    def get(self, request):
        query_serializer = DashboardAnalyticsQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        params = query_serializer.validated_data

        tenant_id = request.user.tenant_id
        if (request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPERADMIN') and request.query_params.get('tenant_id'):
            tenant_id = int(request.query_params.get('tenant_id'))

        if not tenant_id:
            return Response(
                {'error': {'code': 'tenant_required', 'message': 'Tenant context is required for analytics generation.'}},
                status=status.HTTP_400_BAD_REQUEST
            )

        analytics_data = ReportService.get_dashboard_analytics(
            tenant_id=tenant_id,
            property_id=params.get('property_id'),
            period=params.get('period', 'today')
        )
        response_serializer = DashboardAnalyticsResponseSerializer(analytics_data)
        return Response(response_serializer.data)

class PnLReportTabEndpointView(APIView):
    permission_classes = [IsAuthenticated, HasTenantAccess, HasModulePermission]
    required_permission = 'reports:view_pnl'

    def get(self, request):
        query_serializer = FinancialFilterQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        params = query_serializer.validated_data

        tenant_id = request.user.tenant_id
        if (request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPERADMIN') and request.query_params.get('tenant_id'):
            tenant_id = int(request.query_params.get('tenant_id'))

        if not tenant_id:
            return Response({'error': {'code': 'tenant_required', 'message': 'Tenant context required.'}}, status=400)

        data = FinancialReportingService.get_pnl_report(
            tenant_id=tenant_id,
            property_id=params.get('property_id'),
            period=params.get('period', 'this_month'),
            start_date=params.get('start_date'),
            end_date=params.get('end_date')
        )
        return Response(data)

class RevenueReportTabEndpointView(APIView):
    permission_classes = [IsAuthenticated, HasTenantAccess, HasModulePermission]
    required_permission = 'reports:view_pnl'

    def get(self, request):
        query_serializer = FinancialFilterQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        params = query_serializer.validated_data

        tenant_id = request.user.tenant_id
        if (request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPERADMIN') and request.query_params.get('tenant_id'):
            tenant_id = int(request.query_params.get('tenant_id'))

        if not tenant_id:
            return Response({'error': {'code': 'tenant_required', 'message': 'Tenant context required.'}}, status=400)

        data = FinancialReportingService.get_revenue_report(
            tenant_id=tenant_id,
            property_id=params.get('property_id'),
            period=params.get('period', 'this_month'),
            start_date=params.get('start_date'),
            end_date=params.get('end_date')
        )
        return Response(data)

class ExpenseReportTabEndpointView(APIView):
    permission_classes = [IsAuthenticated, HasTenantAccess, HasModulePermission]
    required_permission = 'reports:view_pnl'

    def get(self, request):
        query_serializer = FinancialFilterQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        params = query_serializer.validated_data

        tenant_id = request.user.tenant_id
        if (request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPERADMIN') and request.query_params.get('tenant_id'):
            tenant_id = int(request.query_params.get('tenant_id'))

        if not tenant_id:
            return Response({'error': {'code': 'tenant_required', 'message': 'Tenant context required.'}}, status=400)

        data = FinancialReportingService.get_expense_report(
            tenant_id=tenant_id,
            property_id=params.get('property_id'),
            period=params.get('period', 'this_month'),
            start_date=params.get('start_date'),
            end_date=params.get('end_date')
        )
        return Response(data)

class HospitalityKpiReportTabEndpointView(APIView):
    permission_classes = [IsAuthenticated, HasTenantAccess, HasModulePermission]
    required_permission = 'reports:view_pnl'

    def get(self, request):
        query_serializer = FinancialFilterQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        params = query_serializer.validated_data

        tenant_id = request.user.tenant_id
        if (request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPERADMIN') and request.query_params.get('tenant_id'):
            tenant_id = int(request.query_params.get('tenant_id'))

        if not tenant_id:
            return Response({'error': {'code': 'tenant_required', 'message': 'Tenant context required.'}}, status=400)

        data = FinancialReportingService.get_hospitality_kpi_report(
            tenant_id=tenant_id,
            property_id=params.get('property_id'),
            period=params.get('period', 'this_month'),
            start_date=params.get('start_date'),
            end_date=params.get('end_date')
        )
        return Response(data)

class RestaurantReportTabEndpointView(APIView):
    permission_classes = [IsAuthenticated, HasTenantAccess, HasModulePermission]
    required_permission = 'reports:view_pnl'

    def get(self, request):
        query_serializer = FinancialFilterQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        params = query_serializer.validated_data

        tenant_id = request.user.tenant_id
        if (request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPERADMIN') and request.query_params.get('tenant_id'):
            tenant_id = int(request.query_params.get('tenant_id'))

        if not tenant_id:
            return Response({'error': {'code': 'tenant_required', 'message': 'Tenant context required.'}}, status=400)

        data = FinancialReportingService.get_restaurant_report(
            tenant_id=tenant_id,
            property_id=params.get('property_id'),
            period=params.get('period', 'this_month'),
            start_date=params.get('start_date'),
            end_date=params.get('end_date')
        )
        return Response(data)

class ReceivablesReportTabEndpointView(APIView):
    permission_classes = [IsAuthenticated, HasTenantAccess, HasModulePermission]
    required_permission = 'reports:view_pnl'

    def get(self, request):
        query_serializer = FinancialFilterQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        params = query_serializer.validated_data

        tenant_id = request.user.tenant_id
        if (request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPERADMIN') and request.query_params.get('tenant_id'):
            tenant_id = int(request.query_params.get('tenant_id'))

        if not tenant_id:
            return Response({'error': {'code': 'tenant_required', 'message': 'Tenant context required.'}}, status=400)

        data = FinancialReportingService.get_receivables_report(
            tenant_id=tenant_id,
            property_id=params.get('property_id'),
            period=params.get('period', 'this_month'),
            start_date=params.get('start_date'),
            end_date=params.get('end_date')
        )
        return Response(data)

class FinancialSuiteExportCsvView(APIView):
    permission_classes = [IsAuthenticated, HasTenantAccess, HasModulePermission]
    required_permission = 'reports:export'

    def get(self, request):
        query_serializer = FinancialFilterQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        params = query_serializer.validated_data

        tenant_id = request.user.tenant_id
        if (request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPERADMIN') and request.query_params.get('tenant_id'):
            tenant_id = int(request.query_params.get('tenant_id'))

        if not tenant_id:
            return Response({'error': {'code': 'tenant_required', 'message': 'Tenant context required.'}}, status=400)

        report_type = params.get('report_type', 'pnl')
        csv_content = FinancialReportingService.export_financial_csv(
            tenant_id=tenant_id,
            report_type=report_type,
            property_id=params.get('property_id'),
            period=params.get('period', 'this_month'),
            start_date=params.get('start_date'),
            end_date=params.get('end_date')
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        response = HttpResponse(csv_content, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="financial-report-{report_type}-{timestamp}.csv"'
        return response


class FinancialReportView(APIView):
    permission_classes = [IsAuthenticated, HasTenantAccess, HasModulePermission]
    required_permission = 'reports:view_pnl'

    @extend_schema(
        parameters=[ReportQuerySerializer],
        responses={200: FinancialReportResponseSerializer}
    )
    def get(self, request):
        query_serializer = ReportQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        params = query_serializer.validated_data

        tenant_id = request.user.tenant_id
        if (request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPERADMIN') and request.query_params.get('tenant_id'):
            tenant_id = int(request.query_params.get('tenant_id'))

        if not tenant_id:
            return Response(
                {'error': {'code': 'tenant_required', 'message': 'Tenant context is required for report generation.'}},
                status=status.HTTP_400_BAD_REQUEST
            )

        financial_data = ReportService.get_financial_summary(
            tenant_id=tenant_id,
            property_id=params.get('property_id'),
            start_date=params.get('start_date'),
            end_date=params.get('end_date')
        )
        response_serializer = FinancialReportResponseSerializer(financial_data)
        return Response(response_serializer.data)

class PnlExportView(APIView):
    permission_classes = [IsAuthenticated, HasTenantAccess, HasModulePermission]
    required_permission = 'reports:export'

    def get(self, request):
        query_serializer = ReportQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        params = query_serializer.validated_data

        tenant_id = request.user.tenant_id
        if (request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPERADMIN') and request.query_params.get('tenant_id'):
            tenant_id = int(request.query_params.get('tenant_id'))

        if not tenant_id:
            return Response(
                {'error': {'code': 'tenant_required', 'message': 'Tenant context is required for P&L export.'}},
                status=status.HTTP_400_BAD_REQUEST
            )

        csv_content = ExportService.export_pnl_csv(
            tenant_id=tenant_id,
            property_id=params.get('property_id'),
            start_date=params.get('start_date'),
            end_date=params.get('end_date')
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        response = HttpResponse(csv_content, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="pnl-statement-{timestamp}.csv"'
        return response

class OccupancyReportView(APIView):
    permission_classes = [IsAuthenticated, HasTenantAccess, HasModulePermission]
    required_permission = 'reports:view_pnl'

    @extend_schema(
        parameters=[ReportQuerySerializer],
        responses={200: OccupancyReportResponseSerializer}
    )
    def get(self, request):
        query_serializer = ReportQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        params = query_serializer.validated_data

        tenant_id = request.user.tenant_id
        if (request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPERADMIN') and request.query_params.get('tenant_id'):
            tenant_id = int(request.query_params.get('tenant_id'))

        if not tenant_id:
            return Response(
                {'error': {'code': 'tenant_required', 'message': 'Tenant context is required for report generation.'}},
                status=status.HTTP_400_BAD_REQUEST
            )

        occupancy_data = ReportService.get_occupancy_summary(
            tenant_id=tenant_id,
            property_id=params.get('property_id'),
            start_date=params.get('start_date'),
            end_date=params.get('end_date')
        )
        response_serializer = OccupancyReportResponseSerializer(occupancy_data)
        return Response(response_serializer.data)

class DashboardAnalyticsView(APIView):
    permission_classes = [IsAuthenticated, HasTenantAccess, HasModulePermission]
    required_permission = 'reports:view_pnl'

    @extend_schema(
        parameters=[DashboardAnalyticsQuerySerializer],
        responses={200: DashboardAnalyticsResponseSerializer}
    )
    def get(self, request):
        query_serializer = DashboardAnalyticsQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        params = query_serializer.validated_data

        tenant_id = request.user.tenant_id
        if (request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPERADMIN') and request.query_params.get('tenant_id'):
            tenant_id = int(request.query_params.get('tenant_id'))

        if not tenant_id:
            return Response(
                {'error': {'code': 'tenant_required', 'message': 'Tenant context is required for analytics generation.'}},
                status=status.HTTP_400_BAD_REQUEST
            )

        analytics_data = ReportService.get_dashboard_analytics(
            tenant_id=tenant_id,
            property_id=params.get('property_id'),
            period=params.get('period', 'today')
        )
        response_serializer = DashboardAnalyticsResponseSerializer(analytics_data)
        return Response(response_serializer.data)

