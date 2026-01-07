# policy/urls.py

from django.urls import path
from . import views

# Define app_name for clear namespacing and link resolution
app_name = 'policy'

urlpatterns = [
    path('policy-management/', views.policy_management_view, name='policy_management'),
    path('my-policies/', views.my_policies_view, name='my_policies'),
    path('apply/<int:policy_id>/', views.apply_policy_view, name='apply_policy'),
    path('policy-details/<str:policy_id>/', views.policy_details_view, name='policy_details'),
    path('withdraw/<int:policy_id>/', views.withdraw_policy, name='withdraw_policy'),
]