from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.UserRegisterView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    
    # path('admin_dashboard/', views.AdminDashBoardView.as_view(), name='admin_dashboard'),
    path('policy_dashboard/', views.PolicyDashBoardView.as_view(), name='policy_dashboard'),
    path('dashboard/', views.user_dashboard_view, name='user_dashboard'),
    # Custom Password Resetting Options
    path('forgot_password', views.ForgotPasswordView.as_view(), name='forgot_password'),
    path('reset_password/<str:username>/', views.ResetPasswordView.as_view(), name='reset_password'),
    path('claims/history/', views.user_dashboard_view, name='claim_history'),


]