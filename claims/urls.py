from django.urls import path
from .views import ClaimDashboardView, SubmitClaimView
from . import views

app_name = 'claims'

urlpatterns = [
    path('dashboard/', ClaimDashboardView.as_view(), name='claim_dashboard'),
    path('submit/', SubmitClaimView.as_view(), name='submit_claim'),
    path('details/<int:claim_id>/', views.get_claim_details, name='get_claim_details'),
    path('download/<int:claim_id>/', views.download_claim_document, name='download_claim_document'),

]