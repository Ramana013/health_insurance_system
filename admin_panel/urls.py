from django.urls import path
from . import views
from .views import PolicyListView

app_name = 'admin_panel' # Essential for namespacing

urlpatterns = [
    path('dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('manage-policies/', PolicyListView.as_view(), name='admin_policy_management'),
    path('claims/', views.admin_claims, name='admin_claims'),
    path('update-claim-status/', views.update_claim_status, name='update_claim_status'),
    path('feedback/', views.admin_feedback_dashboard, name='feedback_dashboard'),
    path('feedback/ticket/<str:ticket_id>/', views.admin_view_ticket, name='view_ticket'),
    path('feedback/ticket/<str:ticket_id>/resolve/', views.admin_resolve_ticket, name='resolve_ticket'),
    path('feedback/ticket/<str:ticket_id>/status/', views.admin_update_status, name='update_status'),
    path('feedback/ticket/<str:ticket_id>/comments/', views.get_ticket_comments, name='get_comments'),
    path('feedback/comment/<str:ticket_id>/', views.admin_add_comment, name='add_comment'),
    # Reports & Analytics URLs
    path('reports/', views.ReportsDashboardView.as_view(), name='reports_dashboard'),

    # Report Generation URLs (using correct class names)
    path('reports/claims/', views.ClaimsReportView.as_view(), name='claims_report'),
    path('reports/policy-usage/', views.PolicyUsageReportView.as_view(), name='policy_usage_report'),
    path('reports/provider/', views.ProviderReportView.as_view(), name='provider_report'),
    path('reports/monthly-trends/', views.MonthlyTrendsReportView.as_view(), name='monthly_trends_report'),

    # API Endpoints
    path('reports/chart-data/', views.ChartDataView.as_view(), name='get_chart_data'),
]