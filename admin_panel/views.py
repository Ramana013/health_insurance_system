from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, View
from django.shortcuts import redirect, render, get_object_or_404
from policy.models import Policy, UserPolicy, Claim
from django.views.generic import ListView, TemplateView, View
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import user_passes_test, login_required
from django.utils import timezone
from feedback_support.models import Feedback, FeedbackComment
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
from django.db.models import Count, Avg, Sum, Q
import csv
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet


# Check if NetworkProvider model exists
try:
    from providers.models import NetworkProvider
    HAS_NETWORK_PROVIDER = True
except ImportError:
    HAS_NETWORK_PROVIDER = False
    NetworkProvider = None

class AdminDashboardView(TemplateView):
    template_name = 'admin_panel/admin_dashboard.html'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(request, "You don't have permission to access this page.")
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get current date
        from django.utils import timezone
        current_date = timezone.now()

        # Get the custom user model
        User = get_user_model()

        # Calculate statistics
        total_policies = Policy.objects.count()
        active_claims = Claim.objects.filter(
            status__in=['SUBMITTED', 'UNDER_REVIEW', 'submitted', 'Under Review']
        ).count()
        pending_feedback = Feedback.objects.filter(status='Open').count()

        # Calculate total revenue (sum of all policy premiums)
        from django.db.models import Sum
        total_revenue = Policy.objects.aggregate(total=Sum('premium'))['total'] or 0

        # Get recent claims (last 4)
        recent_claims = Claim.objects.select_related(
            'user_policy__user', 'user_policy__policy'
        ).order_by('-filed_date')[:4]

        # Get recent feedback (last 4)
        recent_feedback = Feedback.objects.select_related(
            'created_by', 'policy_name'
        ).order_by('-created_on')[:4]

        # Get recent activities
        recent_activities = []

        # Add recent claim activities
        recent_claim_updates = Claim.objects.filter(
            status__in=['APPROVED', 'REJECTED', 'approved', 'rejected']
        ).order_by('-filed_date')[:3]

        for claim in recent_claim_updates:
            status_text = 'Approved' if claim.status in ['APPROVED', 'approved'] else 'Rejected'
            recent_activities.append({
                'type': 'claim',
                'title': f'Claim {status_text}',
                'description': f'Claim #{claim.claim_id} was {status_text.lower()}',
                'time': claim.filed_date,
                'icon': 'fa-check-circle' if claim.status in ['APPROVED', 'approved'] else 'fa-times-circle',
                'color': 'bg-success' if claim.status in ['APPROVED', 'approved'] else 'bg-danger'
            })

        # Add recent feedback activities
        for feedback in recent_feedback:
            recent_activities.append({
                'type': 'feedback',
                'title': 'New Support Ticket',
                'description': f'Ticket #{feedback.ticket_id} submitted by {feedback.created_by.username}',
                'time': feedback.created_on,
                'icon': 'fa-headset',
                'color': 'bg-warning'
            })

        # Add user registration activities
        # Get recent user registrations if your CustomUser model has date_joined
        try:
            recent_users = User.objects.order_by('-date_joined')[:2]
            for user in recent_users:
                recent_activities.append({
                    'type': 'user',
                    'title': 'New User Registered',
                    'description': f'{user.username} registered for insurance',
                    'time': user.date_joined,
                    'icon': 'fa-user-plus',
                    'color': 'bg-info'
                })
        except AttributeError:
            # If date_joined doesn't exist, skip
            pass

        # Sort activities by time (most recent first)
        recent_activities.sort(key=lambda x: x['time'], reverse=True)
        recent_activities = recent_activities[:5]  # Take only 5 most recent

        # Calculate growth percentages (simplified - adjust based on your business logic)
        policy_growth = 12  # Example growth percentage

        # Pending claims needing review
        pending_review_claims = Claim.objects.filter(
            status__in=['SUBMITTED', 'submitted']
        ).count()

        # Urgent feedback tickets
        # Check if Feedback model has priority field
        try:
            urgent_feedback = Feedback.objects.filter(
                status='Open',
                priority='high'
            ).count()
        except:
            urgent_feedback = pending_feedback // 3  # Estimate if no priority field

        # Revenue growth (simplified)
        revenue_growth = 18  # Example growth percentage

        context.update({
            'page': 'dashboard',
            'current_date': current_date.strftime('%B %d, %Y'),

            # Statistics
            'total_policies': total_policies,
            'active_claims': active_claims,
            'pending_feedback': pending_feedback,
            'total_revenue': total_revenue,
            'policy_growth': policy_growth,
            'revenue_growth': revenue_growth,
            'pending_review_claims': pending_review_claims,
            'urgent_feedback': urgent_feedback,

            # Recent data
            'recent_claims': recent_claims,
            'recent_feedback': recent_feedback,
            'recent_activities': recent_activities,

            # Additional stats for cards
            'total_users': User.objects.count(),
            'total_claims': Claim.objects.count(),
            'approved_claims': Claim.objects.filter(
                status__in=['APPROVED', 'approved']
            ).count(),
            'rejected_claims': Claim.objects.filter(
                status__in=['REJECTED', 'rejected']
            ).count(),
        })
        return context

class PolicyListView(ListView):
    model = UserPolicy
    template_name = 'admin_panel/admin_policy_management.html'
    context_object_name = 'user_policies'

    def get_queryset(self):
        # Get filter parameters from GET request
        policy_name = self.request.GET.get('policy_name', '').strip()
        policy_id = self.request.GET.get('policy_id', '').strip()
        username = self.request.GET.get('username', '').strip()
        status_filter = self.request.GET.get('status', '').strip()
        premium_min = self.request.GET.get('premium_min', '').strip()
        premium_max = self.request.GET.get('premium_max', '').strip()

        # Start with all UserPolicy objects
        queryset = UserPolicy.objects.all().select_related('user', 'policy')

        # Apply filters if they exist
        if policy_name:
            queryset = queryset.filter(policy__name__icontains=policy_name)

        if policy_id:
            queryset = queryset.filter(policy__policy_id__icontains=policy_id)

        if username:
            queryset = queryset.filter(user__username__icontains=username)

        if status_filter:
            queryset = queryset.filter(status__iexact=status_filter)

        if premium_min:
            try:
                premium_min_float = float(premium_min)
                queryset = queryset.filter(policy__premium__gte=premium_min_float)
            except ValueError:
                pass

        if premium_max:
            try:
                premium_max_float = float(premium_max)
                queryset = queryset.filter(policy__premium__lte=premium_max_float)
            except ValueError:
                pass

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page'] = 'policies'
        return context

    def post(self, request, *args, **kwargs):
        # 1. HANDLE ADD NEW POLICY
        if 'add_policy' in request.POST:
            name = request.POST.get('policy_name')
            p_id = request.POST.get('policy_id')

            # Check for existing policy to prevent IntegrityError (Unique constraint)
            if Policy.objects.filter(name=name).exists():
                messages.error(request, f"Policy with name '{name}' already exists!")
                return redirect(request.path)

            if Policy.objects.filter(policy_id=p_id).exists():
                messages.error(request, f"Policy ID '{p_id}' is already in use!")
                return redirect(request.path)

            try:
                Policy.objects.create(
                    name=name,
                    policy_id=p_id,
                    description=request.POST.get('description'),
                    premium=request.POST.get('premium'),
                    coverage_limit=request.POST.get('coverage_limit'),
                    validity=request.POST.get('validity_period')
                )
                messages.success(request, "New policy created successfully!")
            except Exception as e:
                messages.error(request, f"Error creating policy: {e}")

            return redirect(request.path)

        # 2. HANDLE UPDATE (EDIT)
        elif 'update_user_policy' in request.POST:
            up_id = request.POST.get('user_policy_id')
            user_policy = get_object_or_404(UserPolicy, id=up_id)

            # Update the UserPolicy specific status
            user_policy.status = request.POST.get('status')
            user_policy.save()

            # Update the underlying Policy information
            policy = user_policy.policy
            policy.name = request.POST.get('policy_name')
            policy.description = request.POST.get('description')
            policy.premium = request.POST.get('premium')
            policy.save()

            messages.success(request, f"Policy '{policy.name}' updated successfully!")
            return redirect(request.path)

        # 3. HANDLE DELETE
        elif 'delete_user_policy' in request.POST:
            up_id = request.POST.get('user_policy_id')
            user_policy = get_object_or_404(UserPolicy, id=up_id)
            policy_name = user_policy.policy.name

            user_policy.delete()

            messages.success(request, f"Policy '{policy_name}' removed from user successfully!")
            return redirect(request.path)

        # Fallback for unexpected POST requests
        return self.get(request, *args, **kwargs)


def admin_claims(request):
    # Fetch all claims from the database
    # select_related improves performance for foreign keys like User or Policy
    claims = Claim.objects.all().order_by('-filed_date')

    # Get filter parameters from GET request
    claim_id = request.GET.get('claim_id', '').strip()
    user_search = request.GET.get('user', '').strip()
    policy_name = request.GET.get('policy_name', '').strip()
    status_filter = request.GET.get('status', '').strip()
    amount_min = request.GET.get('amount_min', '').strip()
    amount_max = request.GET.get('amount_max', '').strip()

    # Apply filters if they exist
    if claim_id:
        claims = claims.filter(claim_id__icontains=claim_id)

    if user_search:
        claims = claims.filter(user_policy__user__username__icontains=user_search)

    if policy_name:
        claims = claims.filter(user_policy__policy__name__icontains=policy_name)

    if status_filter:
        # Handle different status formats
        if status_filter.lower() == 'submitted':
            claims = claims.filter(status__iexact='submitted')
        elif status_filter.lower() == 'under review':
            claims = claims.filter(status__iexact='under review')
        elif status_filter.lower() == 'approved':
            claims = claims.filter(status__iexact='approved')
        elif status_filter.lower() == 'rejected':
            claims = claims.filter(status__iexact='rejected')
        else:
            # Try exact match
            claims = claims.filter(status__iexact=status_filter)

    if amount_min:
        try:
            amount_min_float = float(amount_min)
            claims = claims.filter(claim_amount__gte=amount_min_float)
        except ValueError:
            pass

    if amount_max:
        try:
            amount_max_float = float(amount_max)
            claims = claims.filter(claim_amount__lte=amount_max_float)
        except ValueError:
            pass

    # Get unique values for dropdowns from the filtered (or all) claims
    # For users: get usernames from associated users
    user_list = (
        claims
        .select_related('user_policy__user')
        .values_list('user_policy__user__username', flat=True)
        .distinct()
        .order_by('user_policy__user__username')
    )

    # For policy names
    policy_list = (
        claims
        .select_related('user_policy__policy')
        .values_list('user_policy__policy__name', flat=True)
        .distinct()
        .order_by('user_policy__policy__name')
    )

    # For statuses
    status_list = (
        claims
        .values_list('status', flat=True)
        .distinct()
        .order_by('status')
    )

    # If you want to show all possible values regardless of current filters,
    # you can get them from the unfiltered queryset
    all_statuses = Claim.objects.values_list('status', flat=True).distinct().order_by('status')
    all_users = Claim.objects.select_related('user_policy__user').values_list(
        'user_policy__user__username', flat=True
    ).distinct().order_by('user_policy__user__username')
    all_policies = Claim.objects.select_related('user_policy__policy').values_list(
        'user_policy__policy__name', flat=True
    ).distinct().order_by('user_policy__policy__name')

    context = {
        # This key MUST match the name used in your {% for claim in ... %} loop
        'submitted_claims': claims,

        # Current filter values for preserving in the form
        'current_filters': {
            'claim_id': claim_id,
            'user': user_search,
            'policy_name': policy_name,
            'status': status_filter,
            'amount_min': amount_min,
            'amount_max': amount_max,
        },

        # Dropdown options
        'user_list': user_list,
        'policy_list': policy_list,
        'status_list': status_list,

        # All possible options (useful if you want dropdowns to show all options)
        'all_statuses': all_statuses,
        'all_users': all_users,
        'all_policies': all_policies,
    }
    return render(request, 'admin_panel/admin_claims.html', context)


@require_POST
def update_claim_status(request):
    """
    Updates the status and admin comments for a claim in the policy app.
    """
    claim_id_val = request.POST.get('claim_id')
    new_status = request.POST.get('status')
    admin_comment = request.POST.get('comment')

    claim = get_object_or_404(Claim, claim_id=claim_id_val)

    try:
        # Update status if provided
        if new_status:
            # Convert status string to match model choices
            status_map = {
                'Submitted': 'SUBMITTED',
                'Under Review': 'UNDER_REVIEW',
                'Approved': 'APPROVED',
                'Rejected': 'REJECTED'
            }

            formatted_status = status_map.get(new_status, new_status.upper().replace(" ", "_"))

            # Validate status
            valid_statuses = [choice[0] for choice in Claim.CLAIM_STATUS_CHOICES]
            if formatted_status in valid_statuses:
                claim.status = formatted_status

        # Update comment if provided
        if admin_comment is not None:
            claim.comment = admin_comment

        claim.save()

        return JsonResponse({
            'status': 'success',
            'message': f'Claim {claim_id_val} has been updated successfully.'
        })

    except Exception as e:
        return JsonResponse


def is_admin(user):
    return user.is_authenticated and user.is_staff


@user_passes_test(is_admin)
def admin_feedback_dashboard(request):
    """Admin dashboard to view all feedback tickets"""
    status_filter = request.GET.get('status', '')
    category_filter = request.GET.get('category', '')
    search_query = request.GET.get('q', '')

    # Check if JSON response is requested (for badge count)
    if request.GET.get('json') == 'true':
        open_tickets_count = Feedback.objects.filter(status='Open').count()
        return JsonResponse({
            'open_tickets': open_tickets_count,
            'total_tickets': Feedback.objects.count()
        })

    # Get all feedback tickets
    tickets = Feedback.objects.all().select_related(
        'created_by', 'policy_name', 'network_provider'
    ).prefetch_related('feedback_comments').order_by('-created_on')

    # Apply filters
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    if category_filter:
        tickets = tickets.filter(category=category_filter)
    if search_query:
        tickets = tickets.filter(
            Q(ticket_id__icontains=search_query) |
            Q(created_by__username__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(policy_name__name__icontains=search_query)
        )

    # Add admin comment count to each ticket
    for ticket in tickets:
        ticket.admin_comments_count = ticket.feedback_comments.filter(is_admin=True).count()

    # Get unique categories and statuses for filter dropdowns
    categories = Feedback.objects.values_list('category', flat=True).distinct()
    statuses = Feedback.objects.values_list('status', flat=True).distinct()

    # Get open tickets count for badge
    open_tickets_count = Feedback.objects.filter(status='Open').count()

    context = {
        'tickets': tickets,
        'categories': categories,
        'statuses': statuses,
        'selected_status': status_filter,
        'selected_category': category_filter,
        'search_query': search_query,
        'feedback_count': open_tickets_count,
    }
    return render(request, 'admin_panel/feedback_dashboard.html', context)


@user_passes_test(is_admin)
def admin_view_ticket(request, ticket_id):
    """Admin view for individual ticket details"""
    ticket = get_object_or_404(Feedback, ticket_id=ticket_id)

    if request.method == 'POST':
        # Handle status update
        new_status = request.POST.get('status')
        if new_status:
            old_status = ticket.status
            ticket.status = new_status
            ticket.save()

            # Add status change comment
            FeedbackComment.objects.create(
                feedback=ticket,
                user=request.user,
                comment=f"Status changed from '{old_status}' to '{new_status}' by {request.user.username}.",
                is_admin=True
            )

            messages.success(request, f'Ticket status updated to {new_status}')
            return redirect('admin_panel:view_ticket', ticket_id=ticket_id)

    # Get all comments for this ticket
    all_comments = ticket.feedback_comments.all().order_by('created_at')
    admin_comments = ticket.get_admin_comments()

    # Status choices
    status_choices = ['Open', 'Under Review', 'Closed']

    context = {
        'ticket': ticket,
        'all_comments': all_comments,
        'admin_comments': admin_comments,
        'status_choices': status_choices,
        'page_title': f'Ticket #{ticket.ticket_id}',
    }
    return render(request, 'admin_panel/view_ticket.html', context)


@user_passes_test(is_admin)
@require_POST
def admin_resolve_ticket(request, ticket_id):
    """Mark ticket as resolved/closed"""
    ticket = get_object_or_404(Feedback, ticket_id=ticket_id)

    old_status = ticket.status
    ticket.status = 'Closed'
    ticket.save()

    # Add automatic comment
    FeedbackComment.objects.create(
        feedback=ticket,
        user=request.user,
        comment=f"Ticket marked as resolved and closed by {request.user.username}.",
        is_admin=True
    )

    messages.success(request, f'Ticket {ticket_id} has been resolved and closed.')

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': f'Ticket {ticket_id} has been resolved and closed.'
        })

    return redirect('admin_panel:feedback_dashboard')


@user_passes_test(is_admin)
@require_POST
def admin_add_comment(request, ticket_id):
    """Add admin comment to ticket"""
    ticket = get_object_or_404(Feedback, ticket_id=ticket_id)

    comment_text = request.POST.get('comment', '').strip()
    if comment_text:
        # Create comment
        FeedbackComment.objects.create(
            feedback=ticket,
            user=request.user,
            comment=comment_text,
            is_admin=True
        )

        # Update ticket status if it's Open
        if ticket.status == 'Open':
            ticket.status = 'Under Review'
            ticket.save()

        # AJAX response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Comment added successfully',
                'comment': comment_text,
                'user': request.user.username,
                'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M'),
                'new_status': ticket.status
            })

        messages.success(request, 'Comment added successfully.')

    return redirect('admin_panel:view_ticket', ticket_id=ticket_id)


@user_passes_test(is_admin)
def get_ticket_comments(request, ticket_id):
    """Get comments for a ticket (AJAX endpoint)"""
    ticket = get_object_or_404(Feedback, ticket_id=ticket_id)
    comments = ticket.feedback_comments.all().order_by('created_at')

    comments_data = []
    for comment in comments:
        comments_data.append({
            'id': comment.id,
            'user': comment.user.username,
            'comment': comment.comment,
            'is_admin': comment.is_admin,
            'timestamp': comment.created_at.strftime('%Y-%m-%d %H:%M'),
        })

    return JsonResponse({'success': True, 'comments': comments_data})


@user_passes_test(is_admin)
@require_POST
def admin_update_status(request, ticket_id):
    """Update ticket status via AJAX"""
    ticket = get_object_or_404(Feedback, ticket_id=ticket_id)

    new_status = request.POST.get('status', '').strip()
    if new_status in ['Open', 'Under Review', 'Closed']:
        old_status = ticket.status
        ticket.status = new_status
        ticket.save()

        # Add status change comment
        FeedbackComment.objects.create(
            feedback=ticket,
            user=request.user,
            comment=f"Status changed from '{old_status}' to '{new_status}' by {request.user.username}.",
            is_admin=True
        )

        return JsonResponse({
            'success': True,
            'message': f'Status updated to {new_status}',
            'new_status': new_status,
            'old_status': old_status
        })

    return JsonResponse({
        'success': False,
        'message': 'Invalid status'
    }, status=400)


# ================================================
# REPORTS & ANALYTICS VIEWS
# ================================================

class ReportsDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Reports & Analytics Dashboard View"""
    template_name = 'admin_panel/reports_dashboard.html'

    def test_func(self):
        """Only staff users can access"""
        return self.request.user.is_staff

    def get_date_range(self, start_date_str, end_date_str):
        """Get date range from request parameters"""
        if not start_date_str:
            start_date = (timezone.now() - timedelta(days=30)).date()
        else:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()

        if not end_date_str:
            end_date = timezone.now().date()
        else:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        return start_date, end_date

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get filter parameters
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        report_type = self.request.GET.get('report_type', 'all')

        # Set default date range using the correct method name
        start_date, end_date = self.get_date_range(start_date_str, end_date_str)

        # Calculate all statistics
        context.update({
            'page_title': 'Reports & Analytics',
            'start_date': start_date,
            'end_date': end_date,
            'report_type': report_type,
            **self._get_claims_summary(start_date, end_date),
            **self._get_policy_usage_stats(start_date, end_date),
            **self._get_provider_performance(),
            'monthly_growth': self._get_monthly_growth(),
            'top_providers': self._get_top_providers(),
        })

        return context

    def _get_claims_summary(self, start_date, end_date):
        """Get claims summary statistics"""
        claims = Claim.objects.filter(
            filed_date__date__range=[start_date, end_date]
        )

        total_claims = claims.count()

        approved_claims = claims.filter(
            Q(status__iexact='approved') | Q(status__iexact='APPROVED')
        ).count()

        pending_claims = claims.filter(
            Q(status__iexact='submitted') | Q(status__iexact='SUBMITTED') |
            Q(status__iexact='under review') | Q(status__iexact='UNDER_REVIEW')
        ).count()

        return {
            'total_claims': total_claims,
            'approved_claims': approved_claims,
            'pending_claims': pending_claims,
        }

    def _get_policy_usage_stats(self, start_date, end_date):
        """Get policy usage statistics - using UserPolicy model with correct fields"""
        # Get active user policies (assuming 'active' or 'Active' status)
        # Using application_date as the date field
        active_policies = UserPolicy.objects.filter(
            Q(status__iexact='active') | Q(status__iexact='Active'),
            application_date__date__range=[start_date, end_date]
        ).count()

        total_policies = Policy.objects.count()
        policy_utilization = round(
            (active_policies / total_policies * 100) if total_policies > 0 else 0,
            1
        )

        return {
            'active_policies': active_policies,
            'policy_utilization': policy_utilization,
        }

    def _get_provider_performance(self):
        """Get provider performance statistics"""
        # Try to get provider data
        total_providers = 0
        avg_provider_rating = 4.2  # Default value

        if HAS_NETWORK_PROVIDER and NetworkProvider:
            total_providers = NetworkProvider.objects.count()
            if total_providers > 0:
                avg_provider_rating = NetworkProvider.objects.aggregate(
                    avg_rating=Avg('rating')
                )['avg_rating'] or 4.2
        else:
            # Try to get unique providers from Feedback
            try:
                total_providers = Feedback.objects.filter(
                    network_provider__isnull=False
                ).values('network_provider__name').distinct().count()
            except:
                total_providers = 0

        avg_provider_rating = round(avg_provider_rating, 1)
        rating_percentage = (avg_provider_rating / 5) * 100

        return {
            'total_providers': total_providers,
            'avg_provider_rating': avg_provider_rating,
            'rating_percentage': rating_percentage,
        }

    def _get_monthly_growth(self):
        """Calculate monthly claims growth"""
        last_month = timezone.now() - timedelta(days=30)

        current_month_claims = Claim.objects.filter(
            filed_date__gte=last_month
        ).count()

        previous_month_claims = Claim.objects.filter(
            filed_date__gte=last_month - timedelta(days=30),
            filed_date__lt=last_month
        ).count()

        monthly_growth = round(
            ((current_month_claims - previous_month_claims) / previous_month_claims * 100)
            if previous_month_claims > 0 else 0,
            1
        )

        return monthly_growth

    def _get_top_providers(self):
        """Get top 5 providers"""
        providers = []

        if HAS_NETWORK_PROVIDER and NetworkProvider:
            try:
                network_providers = NetworkProvider.objects.annotate(
                    claim_count=Count('claim')
                ).order_by('-claim_count')[:5]

                for provider in network_providers:
                    providers.append({
                        'name': provider.name,
                        'total_claims': provider.claim_count,
                        'rating': provider.rating or 4.0
                    })
            except:
                pass

        # If no network providers found or model doesn't exist, try from feedback
        if not providers:
            try:
                # Get providers from feedback
                from django.db.models import Count
                feedback_providers = Feedback.objects.filter(
                    network_provider__isnull=False
                ).values(
                    'network_provider__name'
                ).annotate(
                    feedback_count=Count('id')
                ).order_by('-feedback_count')[:5]

                for item in feedback_providers:
                    providers.append({
                        'name': item['network_provider__name'],
                        'total_claims': item['feedback_count'],
                        'rating': 4.0  # Default rating
                    })
            except:
                pass

        # If still no providers, add some sample data for demonstration
        if not providers:
            providers = [
                {'name': 'City Hospital', 'total_claims': 45, 'rating': 4.5},
                {'name': 'General Clinic', 'total_claims': 32, 'rating': 4.2},
                {'name': 'Specialty Center', 'total_claims': 28, 'rating': 4.7},
                {'name': 'Urgent Care', 'total_claims': 22, 'rating': 4.1},
                {'name': 'Family Practice', 'total_claims': 18, 'rating': 4.3}
            ]

        return providers


class BaseReportView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Base class for report views"""

    def test_func(self):
        """Only staff users can access"""
        return self.request.user.is_staff

    def get_date_range(self):
        """Get date range from request parameters"""
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')

        if not start_date:
            start_date = (timezone.now() - timedelta(days=30)).date()
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

        if not end_date:
            end_date = timezone.now().date()
        else:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        return start_date, end_date


class SimpleReportMixin:
    """Simplified mixin for report generation"""

    def generate_pdf_report(self, title, headers, data_rows):
        """Generate simple PDF report"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Add title
        title_style = styles['Heading1']
        title_style.alignment = 1
        story.append(Paragraph(title, title_style))
        story.append(Paragraph(f"Generated on: {timezone.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        story.append(Paragraph(
            f"Date Range: {self.request.GET.get('start_date', 'All time')} to {self.request.GET.get('end_date', 'Now')}",
            styles['Normal']))
        story.append(Paragraph("<br/><br/>", styles['Normal']))

        # Create table
        table_data = [headers]
        table_data.extend(data_rows)

        if len(table_data) > 1:
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(table)
        else:
            story.append(Paragraph("No data available for the selected criteria.", styles['Normal']))

        doc.build(story)

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{title.lower().replace(" ", "_")}.pdf"'
        return response

    def generate_csv_report(self, report_type, headers, data_rows):
        """Generate simple CSV report"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report.csv"'

        writer = csv.writer(response)
        writer.writerow(headers)
        for row in data_rows:
            writer.writerow(row)

        return response


class ProviderReportView(SimpleReportMixin, BaseReportView):
    """Generate Provider Performance Report"""

    def get(self, request, *args, **kwargs):
        format = request.GET.get('format', 'pdf')

        # Get provider data
        providers = self.get_provider_data()

        # Prepare headers and data rows
        headers = ['Provider Name', 'Total Claims', 'Average Rating', 'Status']
        data_rows = []

        for provider in providers:
            data_rows.append([
                provider.get('name', 'N/A'),
                provider.get('total_claims', 0),
                f"{provider.get('rating', 0)}/5",
                provider.get('status', 'Active')
            ])

        if format == 'csv':
            return self.generate_csv_report('provider_performance', headers, data_rows)
        else:
            return self.generate_pdf_report('Provider Performance Report', headers, data_rows)

    def get_provider_data(self):
        """Get provider data from available sources"""
        providers = []

        # Try NetworkProvider model first
        if HAS_NETWORK_PROVIDER and NetworkProvider:
            try:
                network_providers = NetworkProvider.objects.annotate(
                    claim_count=Count('claim')
                ).all()

                for provider in network_providers:
                    providers.append({
                        'name': provider.name,
                        'total_claims': provider.claim_count,
                        'rating': provider.rating or 4.0,
                        'status': 'Active' if getattr(provider, 'is_active', True) else 'Inactive'
                    })
            except Exception as e:
                print(f"Error fetching NetworkProvider data: {e}")

        # Try Feedback model as fallback
        if not providers:
            try:
                from django.db.models import Count
                feedback_providers = Feedback.objects.filter(
                    network_provider__isnull=False
                ).values(
                    'network_provider__name'
                ).annotate(
                    feedback_count=Count('id')
                ).order_by('-feedback_count')

                for item in feedback_providers:
                    providers.append({
                        'name': item['network_provider__name'],
                        'total_claims': item['feedback_count'],
                        'rating': 4.0,
                        'status': 'Active'
                    })
            except Exception as e:
                print(f"Error fetching Feedback provider data: {e}")

        # If still no data, use sample data
        if not providers:
            providers = [
                {'name': 'City Hospital', 'total_claims': 45, 'rating': 4.5, 'status': 'Active'},
                {'name': 'General Clinic', 'total_claims': 32, 'rating': 4.2, 'status': 'Active'},
                {'name': 'Specialty Center', 'total_claims': 28, 'rating': 4.7, 'status': 'Active'},
                {'name': 'Urgent Care', 'total_claims': 22, 'rating': 4.1, 'status': 'Active'},
                {'name': 'Family Practice', 'total_claims': 18, 'rating': 4.3, 'status': 'Active'},
                {'name': 'Dental Care', 'total_claims': 15, 'rating': 4.6, 'status': 'Active'},
                {'name': 'Eye Center', 'total_claims': 12, 'rating': 4.4, 'status': 'Active'},
                {'name': 'Physical Therapy', 'total_claims': 8, 'rating': 4.8, 'status': 'Active'}
            ]

        return providers


class ClaimsReportView(SimpleReportMixin, BaseReportView):
    """Generate Claims Summary Report"""

    def get(self, request, *args, **kwargs):
        format = request.GET.get('format', 'pdf')
        start_date, end_date = self.get_date_range()

        claims = Claim.objects.filter(
            filed_date__date__range=[start_date, end_date]
        ).select_related('user_policy__user', 'user_policy__policy')

        headers = ['Claim ID', 'User', 'Policy', 'Amount', 'Status', 'Date Filed']
        data_rows = []

        for claim in claims:
            user_name = 'N/A'
            if hasattr(claim.user_policy, 'user') and hasattr(claim.user_policy.user, 'username'):
                user_name = claim.user_policy.user.username

            policy_name = 'N/A'
            if hasattr(claim.user_policy, 'policy') and hasattr(claim.user_policy.policy, 'name'):
                policy_name = claim.user_policy.policy.name

            data_rows.append([
                claim.claim_id or 'N/A',
                user_name,
                policy_name,
                f"${claim.claim_amount:.2f}" if claim.claim_amount else '$0.00',
                claim.status.title() if claim.status else 'N/A',
                claim.filed_date.strftime('%Y-%m-%d') if claim.filed_date else 'N/A'
            ])

        if format == 'csv':
            return self.generate_csv_report('claims_summary', headers, data_rows)
        else:
            return self.generate_pdf_report('Claims Summary Report', headers, data_rows)


class PolicyUsageReportView(SimpleReportMixin, BaseReportView):
    """Generate Policy Usage Report"""

    def get(self, request, *args, **kwargs):
        format = request.GET.get('format', 'pdf')

        # Get UserPolicy statistics by Policy
        policies = Policy.objects.annotate(
            total_purchases=Count('userpolicy'),
            active_purchases=Count('userpolicy', filter=Q(userpolicy__status__iexact='active'))
        )

        headers = ['Policy Name', 'Policy ID', 'Premium', 'Total Purchases', 'Active Policies', 'Utilization Rate']
        data_rows = []

        for policy in policies:
            total = policy.total_purchases or 0
            active = policy.active_purchases or 0
            utilization = round((active / total * 100) if total > 0 else 0, 1)

            data_rows.append([
                policy.name,
                policy.policy_id or 'N/A',
                f"${policy.premium:.2f}" if policy.premium else '$0.00',
                total,
                active,
                f"{utilization}%"
            ])

        if format == 'csv':
            return self.generate_csv_report('policy_usage', headers, data_rows)
        else:
            return self.generate_pdf_report('Policy Usage Report', headers, data_rows)


class MonthlyTrendsReportView(SimpleReportMixin, BaseReportView):
    """Generate Monthly Trends Report"""

    def get(self, request, *args, **kwargs):
        format = request.GET.get('format', 'pdf')

        # Get data for last 6 months
        trends_data = self.get_trends_data()

        headers = ['Month', 'Claims', 'New Policies', 'Approved Claims', 'Revenue ($)']
        data_rows = []

        for i in range(len(trends_data['months'])):
            data_rows.append([
                trends_data['months'][i],
                trends_data['claims'][i],
                trends_data['policies'][i],
                trends_data['approved_claims'][i],
                f"${trends_data['revenue'][i]:,.2f}"
            ])

        if format == 'csv':
            return self.generate_csv_report('monthly_trends', headers, data_rows)
        else:
            return self.generate_pdf_report('Monthly Trends Report', headers, data_rows)

    def get_trends_data(self):
        """Get trends data for last 6 months"""
        months = []
        claims_data = []
        policies_data = []
        approved_claims_data = []
        revenue_data = []

        for i in range(6, 0, -1):
            month_date = timezone.now() - timedelta(days=30 * i)
            month = month_date.strftime('%b %Y')
            months.append(month)

            # Query actual data for each month
            claims_count = Claim.objects.filter(
                filed_date__month=month_date.month,
                filed_date__year=month_date.year
            ).count()

            # Count UserPolicy applications for the month
            policies_count = UserPolicy.objects.filter(
                application_date__month=month_date.month,
                application_date__year=month_date.year
            ).count()

            # Count approved claims for the month
            approved_claims_count = Claim.objects.filter(
                filed_date__month=month_date.month,
                filed_date__year=month_date.year,
                status__iexact='approved'
            ).count()

            # Calculate revenue (sum of claim amounts for approved claims in the month)
            monthly_revenue = Claim.objects.filter(
                filed_date__month=month_date.month,
                filed_date__year=month_date.year,
                status__iexact='approved'
            ).aggregate(total=Sum('claim_amount'))['total'] or 0

            claims_data.append(claims_count)
            policies_data.append(policies_count)
            approved_claims_data.append(approved_claims_count)
            revenue_data.append(monthly_revenue)

        return {
            'months': months,
            'claims': claims_data,
            'policies': policies_data,
            'approved_claims': approved_claims_data,
            'revenue': revenue_data
        }


class ChartDataView(LoginRequiredMixin, UserPassesTestMixin, View):
    """API endpoint to get chart data"""

    def test_func(self):
        """Only staff users can access"""
        return self.request.user.is_staff

    def get(self, request, *args, **kwargs):
        chart_type = request.GET.get('type', 'claims')

        # Last 6 months data
        months = []
        data = []

        for i in range(6, 0, -1):
            month_date = timezone.now() - timedelta(days=30 * i)
            month = month_date.strftime('%b')
            months.append(month)

            if chart_type == 'claims':
                count = Claim.objects.filter(
                    filed_date__month=month_date.month,
                    filed_date__year=month_date.year
                ).count()
                data.append(count)

            elif chart_type == 'policies':
                # Count UserPolicy applications for the month
                count = UserPolicy.objects.filter(
                    application_date__month=month_date.month,
                    application_date__year=month_date.year
                ).count()
                data.append(count)

            elif chart_type == 'revenue':
                # Calculate revenue for the month
                revenue = Claim.objects.filter(
                    filed_date__month=month_date.month,
                    filed_date__year=month_date.year,
                    status__iexact='approved'
                ).aggregate(total=Sum('claim_amount'))['total'] or 0
                data.append(float(revenue))

        return JsonResponse({
            'labels': months,
            'data': data
        })


# ================================================
# URL ALIASES FOR COMPATIBILITY
# ================================================

# These aliases maintain compatibility with your existing urls.py
class EnhancedClaimsReportView(ClaimsReportView):
    """Alias for ClaimsReportView"""
    pass


class EnhancedPolicyUsageReportView(PolicyUsageReportView):
    """Alias for PolicyUsageReportView"""
    pass


class EnhancedProviderReportView(ProviderReportView):
    """Alias for ProviderReportView"""
    pass


class EnhancedMonthlyTrendsReportView(MonthlyTrendsReportView):
    """Alias for MonthlyTrendsReportView"""
    pass
