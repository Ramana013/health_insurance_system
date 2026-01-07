from django.contrib import admin
from .models import Category, Status, Policy, NetworkProvider, Feedback

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(NetworkProvider)
class NetworkProviderAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ['ticket_id', 'category', 'status', 'policy_name', 'network_provider', 'created_on']
    list_filter = ['category', 'status', 'created_on']
    search_fields = ['ticket_id', 'description']
    readonly_fields = ['ticket_id', 'created_on', 'updated_on']