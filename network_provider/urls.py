from django.urls import path
from .import views
from .views import (
    ProviderDashboardView,
    NetworkProviderListView,
    VerifyEligibilityView,
    GetEligibilityFormView,
    NetworkProviderDashboardView,
    NetworkProviderUpdateView,
    NetworkProviderDeleteView,
)

app_name = 'network_provider'

urlpatterns = [
    path('dashboard/', ProviderDashboardView.as_view(), name='provider_dashboard'),
    path('list/', NetworkProviderListView.as_view(), name='network_providers_list'),
    path('verify-eligibility/', VerifyEligibilityView.as_view(), name='verify_eligibility'),
    path('get-eligibility-form/', GetEligibilityFormView.as_view(), name='get_eligibility_form'),

    path('provider_dashboard/', views.NetworkProviderDashboardView.as_view(), name='network_provider_dashboard'),    # Create

    # Update (Uses primary key 'pk' to identify the provider)
    path('provider/<int:pk>/edit/', NetworkProviderUpdateView.as_view(), name='edit_provider'),

    # Delete
    path('provider/<int:pk>/delete/', NetworkProviderDeleteView.as_view(), name='delete_provider'),

]