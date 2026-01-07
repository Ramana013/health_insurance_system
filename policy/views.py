# policy/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Policy, UserPolicy
from django.contrib import messages
from django.utils import timezone

# Note: For role checking, you might eventually use:
# from django.contrib.auth.models import User 

@login_required(login_url='/')  # Redirects unauthenticated users to the home_login path
def policy_management_view(request):
    context = {
        'policies': SAMPLE_POLICIES,
    }
    return render(request, 'policy_management.html', context)


@login_required
def my_policies_view(request):
    # Fetch UserPolicy instances linked to this user
    # .select_related('policy') prevents multiple database hits for each policy name
    user_policies = UserPolicy.objects.filter(user=request.user).select_related('policy')

    return render(request, 'my_policies.html', {
        'user_policies': user_policies
    })

@login_required(login_url='/')
def policy_details_view(request, policy_id):
    # This fetches the specific policy based on the ID in the URL
    policy = get_object_or_404(Policy, id=policy_id)

    # The key is 'policy': policy - this makes data available in HTML
    return render(request, 'policy_details.html', {'policy': policy})


@login_required
def apply_policy_view(request, policy_id):
    policy = get_object_or_404(Policy, id=policy_id)

    if request.method == "POST":
        # 1. Create the UserPolicy record (or get existing if they clicked back/forth)
        user_policy, created = UserPolicy.objects.get_or_create(
            user=request.user,
            policy=policy,
            defaults={'status': 'APPLIED'}
        )

        # 2. Simulate Payment Success and Activate
        user_policy.activate_policy(payment_ref=f"TXN-{timezone.now().timestamp()}")

        return render(request, 'payment_success.html', {'policy': policy})

    return redirect('policy_details', policy_id=policy_id)

# You will also need a basic policy_management_view (GET)
@login_required
def policy_management_view(request):
    """View to display all available policies."""
    policies = Policy.objects.filter(is_active=True)
    context = {'policies': policies}
    return render(request, 'policy_management.html', context)


@login_required
def withdraw_policy(request, policy_id):
    if request.method == 'POST':
        # Get the record belonging to the logged-in user
        user_policy = get_object_or_404(UserPolicy, id=policy_id, user=request.user)

        # Delete or update status
        user_policy.delete()

        # FIX: Added 'policy:' prefix here
        return redirect('policy:my_policies')

    return redirect('policy:my_policies')


