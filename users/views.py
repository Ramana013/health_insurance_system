from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import (FormView, ListView)
# , CreateView, UpdateView, DeleteView)
from .forms import UserRegisterForm
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import get_user_model

from django.contrib.auth import logout
from django.views import View

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView
from django.contrib.auth.hashers import make_password
from policy.models import UserPolicy, Policy, Claim
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db import models

User = get_user_model()

# Create your views here.
class UserRegisterView(FormView):
    template_name = 'users/register.html'
    form_class = UserRegisterForm
    success_url = reverse_lazy('users:login')
    
    def form_valid(self, form):
        user = form.save()
        messages.success(self.request, "Registration Successful.")
        return super().form_valid(form)

class UserLoginView(LoginView):
    template_name = 'users/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if user.role == 'admin':
            return reverse_lazy('admin_panel:admin_dashboard')
        elif user.role == 'network_provider':
            return reverse_lazy('network_provider:network_provider_dashboard')
        return reverse_lazy('users:user_dashboard')

'''class UserLogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('users:login')'''
        
class UserLogoutView(LogoutView):
    next_page = reverse_lazy('users:login')



class PolicyDashBoardView(LoginRequiredMixin, TemplateView):
    template_name = 'users/policy_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Count only policies belonging to the current user with status 'ACTIVE'
        context['active_policy_count'] = UserPolicy.objects.filter(
            user=self.request.user,
            status='ACTIVE'
        ).count()
        return context


class ForgotPasswordView(View):
    def get(self, request):
        return render(request, 'users/forgot_password.html')
    
    def post(self, request):
        username = request.POST.get('username')
        try:
            user = User.objects.get(username=username)
            return redirect('users:reset_password', username=user.username)
        except User.DoesNotExist:
            messages.error(request, 'User not Found.')
            return render(request, 'users/forgot_password.html')

class ResetPasswordView(View):
    def get(self, request, username):
        return render(request, 'users/reset_password.html', {'username': username})
    
    def post(self, request, username):
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        if password != confirm_password:
            messages.error(request, 'Password do not match.')
            return render(request, 'users/reset_password.html', {'username':username})
        
        user = User.objects.get(username=username)
        user.password = make_password(password)
        user.save()
        messages.success(request, "Password Reset Successful.")
        return redirect('users:login')


@login_required
def user_dashboard_view(request):
    # 1. Count claims belonging to this specific user
    # We use user_policy__user because the claim model links to User via UserPolicy
    claims_count = Claim.objects.filter(user_policy__user=request.user).count()

    # 2. (Optional) Get active policy count if you haven't already
    # active_policy_count = ... your existing logic ...

    return render(request, 'users/user_dashboard.html', {
        'claims_count': claims_count,
        # 'active_policy_count': active_policy_count,
    })