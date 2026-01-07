import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from policy.models import UserPolicy, Claim
from django.http import JsonResponse, Http404
from django.conf import settings
import os


class ClaimDashboardView(LoginRequiredMixin, View):
    def get(self, request):
        # Fetch policies belonging to the user
        user_policies = UserPolicy.objects.filter(user=request.user, status='ACTIVE')

        # FIX: Filter claims by reaching the user through the user_policy relationship
        submitted_claims = Claim.objects.filter(user_policy__user=request.user)

        context = {
            'user_policies': user_policies,
            'submitted_claims': submitted_claims,
        }
        return render(request, 'claims/claim_dashboard.html', context)


def get_claim_details(request, claim_id):
    # Ensure the user can only see their own claims
    claim = get_object_or_404(Claim, id=claim_id, user_policy__user=request.user)

    # Get document URL safely
    document_url = ""
    if claim.document and hasattr(claim.document, 'url'):
        document_url = request.build_absolute_uri(claim.document.url)

    data = {
        'claim_id': claim.claim_id,
        'status': claim.get_status_display(),
        'status_raw': claim.status,  # Add raw status for JS
        'amount': f"{claim.claim_amount:,}",
        'reason': claim.reason,
        'comment': claim.comment if claim.comment else "No comments from admin yet.",
        'filed_date': claim.filed_date.strftime('%B %d, %Y'),
        'has_document': bool(claim.document),
        'document_url': document_url
    }
    return JsonResponse(data)


def download_claim_document(request, claim_id):
    try:
        claim = Claim.objects.get(id=claim_id, user_policy__user=request.user)

        if claim.document and claim.document.name:
            file_path = os.path.join(settings.MEDIA_ROOT, str(claim.document.name))

            if os.path.exists(file_path):
                response = FileResponse(open(file_path, 'rb'))
                response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                return response
            else:
                raise Http404("File not found")
        else:
            raise Http404("No document available")

    except Claim.DoesNotExist:
        raise Http404("Claim not found")

class SubmitClaimView(LoginRequiredMixin, View):
    def post(self, request):
        import uuid
        user_policy_id = request.POST.get('user_policy_id')
        reason = request.POST.get('reason')
        claim_amount = request.POST.get('claim_amount')
        document = request.FILES.get('document')

        user_policy = UserPolicy.objects.get(id=user_policy_id)

        # Create the claim using your specific model fields
        Claim.objects.create(
            user_policy=user_policy,
            claim_id=f"CLM{uuid.uuid4().hex[:4].upper()}",
            reason=reason,
            claim_amount=claim_amount,
            document=document,
            status='Submitted'  # Default status from your wireframe
        )

        messages.success(request, "Your claim has been submitted successfully!")
        return redirect('claims:claim_dashboard')