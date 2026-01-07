from django.views.generic.edit import FormView
from django.http import JsonResponse
from .forms import EligibilityCheckForm
from policy.models import Policy
from .network_providers_data import SAMPLE_PROVIDERS
from django.db.models import Q
from network_provider.models import NetworkProvider
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import traceback
from django.http import HttpResponse
from django.template.loader import render_to_string
from .utils import convert_to_int
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import JsonResponse, HttpResponseRedirect
from django.core.exceptions import PermissionDenied
from .models import NetworkProvider
from .forms import NetworkProviderForm
from django.views.generic import View, ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView
from django.contrib.auth import login

# Create your views here.

class ProviderDashboardView(TemplateView):
    template_name = 'network_provider/provider_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_count'] = NetworkProvider.objects.filter(status='Active').count()
        context['total_count'] = NetworkProvider.objects.count()
        context['cashless_count'] = NetworkProvider.objects.filter(network_type__icontains='Cashless').count()
        context['reimbursement_count'] = NetworkProvider.objects.filter(network_type__icontains='Reimbursement').count()
        return context


class NetworkProviderListView(ListView):
    model = NetworkProvider
    template_name = 'network_provider/network_providers.html'
    context_object_name = 'providers'
    paginate_by = 10

    def get_queryset(self):
        if not NetworkProvider.objects.exists():
            for data in SAMPLE_PROVIDERS:
                NetworkProvider.objects.create(
                    provider_id=data['id'],
                    hospital_name=data['name'],
                    location=data['location'],
                    contact=data['contact'],
                    type=data['type'],
                    network_type=data['net_type'],
                    coverage_limit=data['limit'],
                    status=data['status']
                )

        queryset = NetworkProvider.objects.all()

        status_filter = self.request.GET.get('status')
        if status_filter in ['Active', 'Inactive']:
            queryset = queryset.filter(status=status_filter)

        network_filter = self.request.GET.get('network_type')
        if network_filter:
            queryset = queryset.filter(network_type__icontains=network_filter)

        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(hospital_name__icontains=search_query) |
                Q(location__icontains=search_query) |
                Q(provider_id__icontains=search_query)
            )

        return queryset.order_by('provider_id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            if hasattr(Policy, 'is_active'):
                context['active_policies'] = Policy.objects.filter(is_active=True).order_by('name')
            elif hasattr(Policy, 'status'):
                context['active_policies'] = Policy.objects.filter(status='Active').order_by('name')
            else:
                context['active_policies'] = Policy.objects.all().order_by('name')
        except Exception as e:
            context['active_policies'] = []
            print(f"Error fetching policies: {e}")

        context['current_status'] = self.request.GET.get('status', '')
        context['current_network_type'] = self.request.GET.get('network_type', '')
        context['search_query'] = self.request.GET.get('search', '')

        context['total_providers'] = NetworkProvider.objects.count()
        context['active_providers'] = NetworkProvider.objects.filter(status='Active').count()

        return context


@method_decorator(csrf_exempt, name='dispatch')
class VerifyEligibilityView(FormView):
    form_class = EligibilityCheckForm

    def post(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            print("=== AJAX REQUEST RECEIVED ===")
            print("Raw POST data:", dict(request.POST))

            form = self.form_class(request.POST)

            if form.is_valid():
                print("Form is valid")
                return self.form_valid(form)
            else:
                print(f"Form is invalid. Errors: {form.errors}")
                return self.form_invalid(form)

        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        provider_id = self.request.POST.get('provider_id')
        policy_identifier = form.cleaned_data.get('policy_name')
        user_coverage_limit = form.cleaned_data.get('coverage_limit')
        coverage_type = form.cleaned_data.get('coverage_type')
        validity_years = form.cleaned_data.get('validity_years') or '1'

        print(f"=== FORM VALID METHOD START ===")
        print(f"Provider ID: {provider_id}")
        print(f"Policy Identifier: {policy_identifier}")
        print(f"User Coverage Limit: {user_coverage_limit}")
        print(f"Coverage Type: {coverage_type}")

        try:
            provider = NetworkProvider.objects.get(provider_id=provider_id)
            print(f"Found Provider: {provider.hospital_name}")
            print(f"Provider coverage limit (raw): {provider.coverage_limit}")

            policy = None
            try:
                policy = Policy.objects.get(policy_id=policy_identifier)
                print(f"Found policy by policy_id: {policy.name} (policy_id: {policy.policy_id})")
                print(f"Policy coverage limit (raw): {policy.coverage_limit}")
            except (Policy.DoesNotExist, ValueError):
                error_msg = f"Policy with identifier '{policy_identifier}' not found"
                print(f"Error: {error_msg}")
                return JsonResponse({
                    'eligibility_status': 'Error',
                    'message': error_msg
                }, status=404)

            # Convert amounts with detailed debugging
            policy_coverage_raw = getattr(policy, 'coverage_limit', '0')
            policy_coverage_int = convert_to_int(policy_coverage_raw)
            hospital_coverage_int = convert_to_int(provider.coverage_limit)
            user_coverage_int = convert_to_int(str(user_coverage_limit))

            print(f"\n=== COVERAGE AMOUNTS DETAILS ===")
            print(f"Policy coverage raw: '{policy_coverage_raw}'")
            print(f"Policy coverage int: {policy_coverage_int:,}")
            print(f"Hospital coverage raw: '{provider.coverage_limit}'")
            print(f"Hospital coverage int: {hospital_coverage_int:,}")
            print(f"User coverage int: {user_coverage_int:,}")
            print(f"=== END COVERAGE AMOUNTS ===")

            try:
                years_int = int(validity_years)
            except:
                years_int = 1
            years_display = f"{years_int} Year{'s' if years_int > 1 else ''}"

            # FIXED ELIGIBILITY LOGIC: User coverage should be <= provider coverage and <= policy coverage
            if provider.status != 'Active':
                status, msg = "Not Eligible", "This provider is currently inactive."
            elif user_coverage_int > policy_coverage_int:
                status = "Not Eligible"
                msg = f"Requested coverage (₹{user_coverage_int:,}) exceeds policy limit (₹{policy_coverage_int:,})."
            elif user_coverage_int > hospital_coverage_int:
                status = "Not Eligible"
                msg = f"Requested coverage (₹{user_coverage_int:,}) exceeds hospital network limit (₹{hospital_coverage_int:,})."
            else:
                status = "Eligible"
                msg = f"You are eligible for coverage at {provider.hospital_name}. Your requested coverage (₹{user_coverage_int:,}) is within both policy limit (₹{policy_coverage_int:,}) and hospital limit (₹{hospital_coverage_int:,})."

            print(f"=== ELIGIBILITY RESULT ===")
            print(f"Status: {status}")
            print(f"Message: {msg}")

            return JsonResponse({
                'eligibility_status': status,
                'message': msg,
                'policy_name': policy.name,
                'coverage_type': coverage_type,
                'user_coverage_limit': f'₹{user_coverage_int:,}',
                'validity_period': years_display,
                'hospital_limit': f'₹{hospital_coverage_int:,}',
                'policy_limit': f'₹{policy_coverage_int:,}',
                'details': True,
            })

        except NetworkProvider.DoesNotExist:
            error_msg = f'Network provider with ID "{provider_id}" not found'
            print(f"Error: {error_msg}")
            return JsonResponse({
                'eligibility_status': 'Error',
                'message': error_msg
            }, status=404)

        except Exception as e:
            error_details = traceback.format_exc()
            print(f"=== UNEXPECTED ERROR ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print(f"=== END ERROR ===")

            return JsonResponse({
                'eligibility_status': 'Error',
                'message': f'Server Error: {str(e)}'
            }, status=500)

    def form_invalid(self, form):
        errors = form.errors
        print(f"=== FORM INVALID METHOD ===")
        print(f"Form validation errors: {errors}")

        error_list = []
        for field, error_msgs in errors.items():
            for error_msg in error_msgs:
                error_list.append(f"{field}: {error_msg}")

        error_message = 'Invalid form data. Please check all fields.'
        if error_list:
            error_message = ' | '.join(error_list)

        print(f"Final error message: {error_message}")

        return JsonResponse({
            'eligibility_status': 'Error',
            'message': error_message,
            'errors': form.errors.as_json()
        }, status=400)


class GetEligibilityFormView(View):
    """View to serve eligibility form via AJAX"""

    def get(self, request):
        provider_id = request.GET.get('provider_id')
        provider_name = request.GET.get('provider_name', '')

        form = EligibilityCheckForm()

        form_html = render_to_string('network_provider/includes/eligibility_form.html', {
            'form': form,
            'provider_id': provider_id,
            'provider_name': provider_name,
        })

        return HttpResponse(form_html)


class NetworkProviderDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'network_provider/network_provider_dashboard.html'

    def get_context_data(self, **kwargs):
        """
        Handles the 'GET' request logic: filtering data and preparing the form.
        """
        context = super().get_context_data(**kwargs)

        # Filter providers created ONLY by the logged-in user
        my_providers = NetworkProvider.objects.filter(created_by=self.request.user).order_by('-created_at')

        context['providers'] = my_providers
        context['form'] = NetworkProviderForm()  # Empty form for the modal
        context['total_count'] = my_providers.count()
        context['active_count'] = my_providers.filter(status='Active').count()
        context['cashless_count'] = my_providers.filter(network_type__icontains='Cashless').count()

        return context

    def post(self, request, *args, **kwargs):
        """
        Handles the 'POST' request logic: saving the new provider.
        """
        form = NetworkProviderForm(request.POST)

        if form.is_valid():
            provider = form.save(commit=False)
            provider.created_by = request.user  # Link to the current user
            provider.save()

            messages.success(request, "Provider added successfully!")
            return redirect('network_provider:network_provider_dashboard')

        # If form is invalid, re-render the page with errors
        context = self.get_context_data()
        context['form'] = form  # Pass back the form with error messages
        return render(request, self.template_name, context)

class NetworkProviderUpdateView(LoginRequiredMixin, UserPassesTestMixin, SuccessMessageMixin, UpdateView):
    model = NetworkProvider
    form_class = NetworkProviderForm
    # Since we are using a modal on the dashboard, we don't strictly need a template,
    # but Django requires one for UpdateView. You can point it to your dashboard
    # or a simple redirect.
    template_name = 'network_provider/network_provider_dashboard.html'
    success_url = reverse_lazy('network_provider:network_provider_dashboard')
    success_message = "Provider updated successfully!"

    def test_func(self):
        return self.request.user == self.get_object().created_by

    def form_invalid(self, form):
        messages.error(self.request, "Update failed. Please check the data.")
        return redirect('network_provider:network_provider_dashboard')

class NetworkProviderDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = NetworkProvider
    template_name = 'network_provider/provider_confirm_delete.html'
    success_url = reverse_lazy('network_provider:network_provider_dashboard')

    def test_func(self):
        # Security: Only allow the owner to delete
        provider = self.get_object()
        return self.request.user == provider.created_by

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Provider deleted successfully.")
        return super().delete(request, *args, **kwargs)