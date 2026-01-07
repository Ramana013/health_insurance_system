from django.contrib import admin
from .models import NetworkProvider
# Register your models here.

@admin.register(NetworkProvider)
class NetworkProviderAdmin(admin.ModelAdmin):
    # Fields to display in the admin list view
    list_display = ('provider_id', 'hospital_name', 'location', 'network_type', 'coverage_limit', 'status')

    # Filters to find providers easily
    list_filter = ('status', 'network_type')

    # Search functionality for hospital name or ID
    search_fields = ('hospital_name', 'provider_id', 'location')

    # Ensures the admin follows your model's ordering
    ordering = ('provider_id',)