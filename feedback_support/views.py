# feedback_support/views.py (User Side)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views import View
from django.views.generic import ListView, DetailView
from django.http import JsonResponse
from django.db.models import Q
from .models import Feedback, Policy, FeedbackComment
from django.utils import timezone

# Import network providers from external network_provider app
try:
    from network_provider.models import NetworkProvider as ExternalNetworkProvider

    HAS_EXTERNAL_NETWORK_PROVIDER = True
except ImportError:
    HAS_EXTERNAL_NETWORK_PROVIDER = False

# Manually define categories as per your requirements
FEEDBACK_CATEGORIES = [
    {'id': 1, 'name': 'Claim'},
    {'id': 2, 'name': 'Policy Enquiry'},
    {'id': 3, 'name': 'Network Provider'},
    {'id': 4, 'name': 'Service'},
]


class DashboardView(LoginRequiredMixin, View):
    """Dashboard view for feedback support"""
    template_name = 'feedback_support/dashboard.html'

    def get(self, request, *args, **kwargs):
        user_feedbacks = Feedback.objects.filter(created_by=request.user)

        # Calculate statistics
        total_feedbacks = user_feedbacks.count()
        open_feedbacks = user_feedbacks.filter(status='Open').count()
        closed_feedbacks = user_feedbacks.filter(status='Closed').count()
        under_review_feedbacks = user_feedbacks.filter(status='Under Review').count()

        # Get recent feedbacks with admin comments
        recent_feedbacks = user_feedbacks.order_by('-created_on')[:10]

        # Add admin comment info to each feedback
        for feedback in recent_feedbacks:
            feedback.admin_comments_count = feedback.feedback_comments.filter(is_admin=True).count()
            feedback.latest_admin_comment = feedback.get_latest_admin_comment()

        context = {
            'total_feedbacks': total_feedbacks,
            'open_feedbacks': open_feedbacks,
            'closed_feedbacks': closed_feedbacks,
            'under_review_feedbacks': under_review_feedbacks,
            'recent_feedbacks': recent_feedbacks,
        }

        return render(request, self.template_name, context)


class FeedbackListView(LoginRequiredMixin, ListView):
    """Display all submitted feedbacks"""
    model = Feedback
    template_name = 'feedback_support/feedback_list.html'
    context_object_name = 'feedbacks'
    paginate_by = 20  # Optional: add pagination

    def get_queryset(self):
        search_query = self.request.GET.get('search', '')
        status_filter = self.request.GET.get('status', '')

        # Base queryset
        feedbacks = Feedback.objects.filter(created_by=self.request.user)

        # Apply search filter
        if search_query:
            feedbacks = feedbacks.filter(
                Q(ticket_id__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(category__icontains=search_query) |
                Q(policy_name__name__icontains=search_query)
            )

        # Apply status filter
        if status_filter:
            feedbacks = feedbacks.filter(status=status_filter)

        # Order by created date (newest first)
        feedbacks = feedbacks.order_by('-created_on')

        # Prefetch admin comments for each feedback
        feedbacks = feedbacks.prefetch_related('feedback_comments')

        # Add admin comment info to each feedback
        for feedback in feedbacks:
            feedback.admin_comments = feedback.feedback_comments.filter(is_admin=True).order_by('-created_at')
            feedback.latest_admin_comment = feedback.admin_comments.first() if feedback.admin_comments.exists() else None
            feedback.admin_comments_count = feedback.admin_comments.count()

        return feedbacks

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add filter values to context
        context['search_query'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')

        # Get counts for status filter buttons
        user_feedbacks = Feedback.objects.filter(created_by=self.request.user)
        context['total_count'] = user_feedbacks.count()
        context['open_count'] = user_feedbacks.filter(status='Open').count()
        context['closed_count'] = user_feedbacks.filter(status='Closed').count()
        context['review_count'] = user_feedbacks.filter(status='Under Review').count()

        return context


class SubmitFeedbackView(LoginRequiredMixin, View):
    """Submit new feedback"""
    template_name = 'feedback_support/submit_feedback.html'

    def get(self, request, *args, **kwargs):
        # Use manually defined categories
        categories = FEEDBACK_CATEGORIES

        # Get policies from database - using Policy model from feedback_support app
        policies = Policy.objects.all()

        # Get network providers from EXTERNAL network_provider app
        network_providers_list = []

        try:
            if HAS_EXTERNAL_NETWORK_PROVIDER:
                network_providers = ExternalNetworkProvider.objects.all()

                # Convert to a list of dictionaries with the format we need
                for provider in network_providers:
                    network_providers_list.append({
                        'id': provider.id,
                        'name': provider.hospital_name if hasattr(provider, 'hospital_name') else str(provider),
                    })

            else:
                from .models import NetworkProvider as LocalNetworkProvider
                local_providers = LocalNetworkProvider.objects.all()
                for provider in local_providers:
                    network_providers_list.append({
                        'id': provider.id,
                        'name': provider.name,
                    })

        except Exception as e:
            # Create sample data for testing
            network_providers_list = [
                {'id': 1, 'name': 'Apollo Hospitals'},
                {'id': 2, 'name': 'Max Healthcare'},
                {'id': 3, 'name': 'Fortis Hospitals'},
                {'id': 4, 'name': 'Manipal Hospitals'},
            ]

        context = {
            'categories': categories,
            'policies': policies,
            'network_providers': network_providers_list,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        # Get form data
        category_name = request.POST.get('category')
        policy_id = request.POST.get('policy_name')
        network_provider_id = request.POST.get('network_provider')
        description = request.POST.get('description', '').strip()

        # Validate required fields
        if not all([category_name, policy_id, network_provider_id, description]):
            messages.error(request, 'All fields are required.')
            return self.get(request)

        try:
            # Get policy object from local model
            policy = Policy.objects.get(id=policy_id)

            # Get network provider object
            from .models import NetworkProvider as LocalNetworkProvider
            network_provider_name = ""

            if HAS_EXTERNAL_NETWORK_PROVIDER:
                network_provider = ExternalNetworkProvider.objects.get(id=network_provider_id)
                network_provider_name = network_provider.hospital_name if hasattr(network_provider,
                                                                                  'hospital_name') else str(
                    network_provider)
            else:
                from .models import NetworkProvider
                network_provider = NetworkProvider.objects.get(id=network_provider_id)
                network_provider_name = network_provider.name

            # Create or get local network provider record
            local_network_provider, created = LocalNetworkProvider.objects.get_or_create(
                name=network_provider_name
            )

            # Create feedback
            feedback = Feedback(
                category=category_name,
                policy_name=policy,
                network_provider=local_network_provider,
                status='Open',
                description=description,
                created_by=request.user
            )
            feedback.save()

            messages.success(request, f'Feedback submitted successfully! Ticket ID: {feedback.ticket_id}')
            return redirect('feedback_support:feedback_list')

        except Policy.DoesNotExist:
            messages.error(request, 'Selected policy does not exist.')
        except Exception as e:
            messages.error(request, f'Error submitting feedback: {str(e)}')

        return self.get(request)


class ViewFeedbackView(LoginRequiredMixin, View):
    """View feedback details with admin comments"""
    template_name = 'feedback_support/view_feedback.html'

    def get(self, request, *args, **kwargs):
        ticket_id = self.kwargs.get('ticket_id')
        feedback = get_object_or_404(
            Feedback,
            ticket_id=ticket_id,
            created_by=request.user
        )

        # Get all comments for this feedback
        all_comments = feedback.feedback_comments.all().order_by('created_at')

        # Separate admin and user comments
        admin_comments = feedback.get_admin_comments()
        user_comments = feedback.feedback_comments.filter(is_admin=False)

        context = {
            'feedback': feedback,
            'all_comments': all_comments,
            'admin_comments': admin_comments,
            'user_comments': user_comments,
        }
        return render(request, self.template_name, context)


class EditFeedbackView(LoginRequiredMixin, View):
    """Edit feedback description"""
    template_name = 'feedback_support/edit_feedback.html'

    def get(self, request, *args, **kwargs):
        ticket_id = self.kwargs.get('ticket_id')
        feedback = get_object_or_404(
            Feedback,
            ticket_id=ticket_id,
            created_by=request.user
        )

        context = {
            'feedback': feedback,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        ticket_id = self.kwargs.get('ticket_id')
        feedback = get_object_or_404(
            Feedback,
            ticket_id=ticket_id,
            created_by=request.user
        )

        description = request.POST.get('description', '').strip()

        if not description:
            messages.error(request, 'Description is required.')
            context = {'feedback': feedback}
            return render(request, self.template_name, context)

        try:
            feedback.description = description
            feedback.save()
            messages.success(request, f'Feedback {ticket_id} updated successfully!')
            return redirect('feedback_support:view_feedback', ticket_id=ticket_id)

        except Exception as e:
            messages.error(request, f'Error updating feedback: {str(e)}')
            context = {'feedback': feedback}
            return render(request, self.template_name, context)


# AJAX endpoints for user side
def get_feedback_comments(request, ticket_id):
    """Get comments for a feedback (AJAX endpoint)"""
    try:
        feedback = get_object_or_404(Feedback, ticket_id=ticket_id, created_by=request.user)
        comments = feedback.feedback_comments.all().order_by('created_at')

        comments_data = []
        for comment in comments:
            comments_data.append({
                'id': comment.id,
                'user': comment.user.username,
                'comment': comment.comment,
                'is_admin': comment.is_admin,
                'timestamp': comment.created_at.strftime('%Y-%m-%d %H:%M'),
            })

        return JsonResponse({
            'success': True,
            'comments': comments_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)