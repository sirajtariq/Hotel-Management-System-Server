from django.urls import path
from apps.reports.views import (
    FinancialReportView,
    OccupancyReportView,
    PnlExportView,
    DashboardAnalyticsView,
    PnLReportTabEndpointView,
    RevenueReportTabEndpointView,
    ExpenseReportTabEndpointView,
    HospitalityKpiReportTabEndpointView,
    RestaurantReportTabEndpointView,
    ReceivablesReportTabEndpointView,
    FinancialSuiteExportCsvView
)

urlpatterns = [
    path('financial/', FinancialReportView.as_view(), name='financial-report'),
    path('financial/export_csv/', PnlExportView.as_view(), name='financial-report-export-csv'),
    path('financial/pnl/', PnLReportTabEndpointView.as_view(), name='financial-pnl'),
    path('financial/revenue/', RevenueReportTabEndpointView.as_view(), name='financial-revenue'),
    path('financial/expenses/', ExpenseReportTabEndpointView.as_view(), name='financial-expenses'),
    path('financial/hospitality_kpis/', HospitalityKpiReportTabEndpointView.as_view(), name='financial-hospitality-kpis'),
    path('financial/restaurant/', RestaurantReportTabEndpointView.as_view(), name='financial-restaurant'),
    path('financial/receivables/', ReceivablesReportTabEndpointView.as_view(), name='financial-receivables'),
    path('financial/suite_export_csv/', FinancialSuiteExportCsvView.as_view(), name='financial-suite-export-csv'),
    path('occupancy/', OccupancyReportView.as_view(), name='occupancy-report'),
    path('dashboard_analytics/', DashboardAnalyticsView.as_view(), name='dashboard-analytics'),
]


