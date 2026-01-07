from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

# Create your models here.
class CustomUser(AbstractUser):
    ROLE_CHOICES = (
    ('policy_holder', 'Policy Holder'),
    ('network_provider', 'Network Provider'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True, null=True)
    dob = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.username} ({self.role})"
