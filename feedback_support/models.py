from django.db import models
from django.utils import timezone
from django.conf import settings
from policy.models import Policy as PolicyModel

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"


class Status(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Statuses"


class FeedbackComment(models.Model):
    feedback = models.ForeignKey('Feedback', on_delete=models.CASCADE, related_name='feedback_comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment = models.TextField()
    is_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on {self.feedback.ticket_id}"


class Feedback(models.Model):
    ticket_id = models.CharField(max_length=20, unique=True, editable=False)
    category = models.CharField(max_length=100)
    description = models.TextField()
    status = models.CharField(max_length=50, default='Open')
    policy_name = models.ForeignKey('Policy', on_delete=models.PROTECT)
    network_provider = models.ForeignKey('NetworkProvider', on_delete=models.PROTECT)
    created_on = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    updated_on = models.DateTimeField(auto_now=True)

    def get_admin_comments(self):
        """Get all admin comments for this feedback"""
        return self.feedback_comments.filter(is_admin=True).order_by('created_at')

    def get_latest_admin_comment(self):
        """Get the most recent admin comment"""
        return self.get_admin_comments().last()

    def save(self, *args, **kwargs):
        if not self.ticket_id:
            last_feedback = Feedback.objects.order_by('-id').first()
            if last_feedback and last_feedback.ticket_id:
                try:
                    last_number = int(last_feedback.ticket_id[4:])
                    new_number = last_number + 1
                except (ValueError, IndexError):
                    new_number = 1
            else:
                new_number = 1
            self.ticket_id = f"TCKT{new_number:03d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ticket_id} - {self.category}"

class Policy(models.Model):
    policy_ref = models.ForeignKey(PolicyModel, on_delete=models.PROTECT, null=True, blank=True)
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Policies"


class NetworkProvider(models.Model):
    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.name