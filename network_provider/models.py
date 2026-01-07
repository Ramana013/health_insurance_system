from django.db import models
from django.utils import timezone
from django.conf import settings

class NetworkProvider(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    ]

    NETWORK_TYPE_CHOICES = [
        ('Cashless', 'Cashless'),
        ('Reimbursement', 'Reimbursement'),
        ('Cashless / Reimbursement', 'Cashless / Reimbursement'),
    ]

    TYPE_CHOICES = [
        ('Hospital', 'Hospital'),
        ('Clinic', 'Clinic'),
        ('Diagnostic Center', 'Diagnostic Center'),
        ('Pharmacy', 'Pharmacy'),
        ('Dental Clinic', 'Dental Clinic'),
        ('Eye Care', 'Eye Care'),
    ]

    provider_id = models.CharField(max_length=20, unique=True, verbose_name="Provider ID")
    hospital_name = models.CharField(max_length=200, verbose_name="Hospital Name")
    location = models.CharField(max_length=300, verbose_name="Location")
    contact = models.CharField(max_length=20, verbose_name="Contact")
    type = models.CharField(max_length=100, choices=TYPE_CHOICES, verbose_name="Type")
    network_type = models.CharField(max_length=50, choices=NETWORK_TYPE_CHOICES, verbose_name="Network Type")
    coverage_limit = models.CharField(max_length=50, verbose_name="Coverage Limit")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active', verbose_name="Status")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='my_providers',
        null=True, blank=True
    )

    class Meta:
        ordering = ['provider_id']
        verbose_name = "Network Provider"
        verbose_name_plural = "Network Providers"

    def __str__(self):
        return f"{self.provider_id} - {self.hospital_name}"