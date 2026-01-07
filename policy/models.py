# policy/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
# Get the User model based on settings (assuming settings.AUTH_USER_MODEL is used)
User = settings.AUTH_USER_MODEL


class Policy(models.Model):
    """
    Model to store available insurance plans (Admin managed).
    This corresponds to the table visible to the Policy Holder.
    """
    # Policy Id is typically the primary key, but if it needs a specific format (e.g., PLM001),
    # we can make it a CharField and use a standard AutoField for the primary key.
    policy_id = models.CharField(max_length=10, unique=True)  # e.g., PLM001
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    premium = models.DecimalField(max_digits=10, decimal_places=2)  # e.g., 993.00
    coverage_limit = models.CharField(max_length=50)  # Stored as text (e.g., '5 Lakh', '20 Lakh')
    validity = models.CharField(max_length=50)  # Stored as text (e.g., '2 Years', '1 Year')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class UserPolicy(models.Model):
    STATUS_CHOICES = (
        ('APPLIED', 'Applied/Pending Payment'),
        ('ACTIVE', 'Active'),
        ('WITHDRAWN', 'Withdrawn'),
        ('EXPIRED', 'Expired'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_policies')
    policy = models.ForeignKey('Policy', on_delete=models.CASCADE)
    application_date = models.DateTimeField(auto_now_add=True)

    # New fields to track actual activation and payment
    payment_id = models.CharField(max_length=100, null=True, blank=True)
    activation_date = models.DateTimeField(null=True, blank=True)

    # Dates for the coverage period
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='APPLIED')

    class Meta:
        verbose_name_plural = "User Policies"
        # Prevents duplicate active applications for the same policy
        unique_together = ('user', 'policy')

    def __str__(self):
        return f"{self.user.username}'s {self.policy.name} ({self.status})"

    def activate_policy(self, payment_ref=None):
        """
        Call this method in your view after a successful payment
        to move the status from APPLIED to ACTIVE.
        """
        self.status = 'ACTIVE'
        self.payment_id = payment_ref
        self.activation_date = timezone.now()
        self.start_date = timezone.now().date()

        # Example logic: set end date based on policy validity (e.g., 365 days)
        self.end_date = self.start_date + timedelta(days=365)
        self.save()
class Claim(models.Model):
    """
    Model to handle policy claims submitted by policy holders (User).
    This aligns with the Claim Management module requirements.
    """
    CLAIM_STATUS_CHOICES = (
        ('SUBMITTED', 'Submitted'),             # 1. Submitted - User Form Submitted
        ('UNDER_REVIEW', 'Under Review'),       # 2. Under Review - Admin started review
        ('APPROVED', 'Approved'),               # 3. Approved - If all are done then admin approved
        ('REJECTED', 'Rejected'),               # 4. Rejected If claim Rejected with comment.
    )

    # Automatically generate claim ID format (e.g., CLM0001) - implementation varies.
    claim_id = models.CharField(max_length=10, unique=True, blank=True)

    # Policy being claimed. Should ideally be linked to UserPolicy, not just Policy.
    user_policy = models.ForeignKey(UserPolicy, on_delete=models.CASCADE, related_name='claims')

    filed_date = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(verbose_name="Reason for Claim")  # User input field
    document = models.FileField(upload_to='claim_documents/', null=True, blank=True)  # User upload field
    claim_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Amount requested

    status = models.CharField(max_length=20, choices=CLAIM_STATUS_CHOICES, default='SUBMITTED')
    comment = models.TextField(blank=True, null=True, verbose_name="Admin Comment")  # Admin comment field

    def __str__(self):
        return f"Claim {self.claim_id} for {self.user_policy.policy.name}"

    # Example logic for generating custom ID (requires overriding save method)
    def save(self, *args, **kwargs):
        if not self.claim_id:
            # Simple placeholder for auto-generation logic
            last_claim = Claim.objects.all().order_by('id').last()
            if last_claim:
                new_id_int = int(last_claim.claim_id.replace('CLM', '')) + 1
            else:
                new_id_int = 1
            self.claim_id = f'CLM{new_id_int:04d}'
        super().save(*args, **kwargs)