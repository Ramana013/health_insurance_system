from django.contrib import admin
from .models import Policy, UserPolicy, Claim
# Register your models here.



@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    # Columns to show in the list view
    list_display = ('policy_id', 'name', 'premium', 'coverage_limit', 'validity', 'is_active')
    # Filters on the right sidebar
    list_filter = ('is_active', 'validity')
    # Search box functionality
    search_fields = ('policy_id', 'name', 'description')
    # Make the list editable directly from the table
    list_editable = ('is_active', 'premium')


@admin.register(UserPolicy)
class UserPolicyAdmin(admin.ModelAdmin):
    list_display = ('user', 'policy', 'status', 'application_date', 'start_date')
    list_filter = ('status', 'application_date')
    search_fields = ('user__username', 'policy__name')
    # Organize fields into sections in the detail view
    fieldsets = (
        ('User Info', {'fields': ('user', 'policy', 'status')}),
        ('Dates', {'fields': ('start_date', 'end_date')}),
    )


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ('claim_id', 'get_user', 'get_policy', 'claim_amount', 'status', 'filed_date')
    list_filter = ('status', 'filed_date')
    search_fields = ('claim_id', 'user_policy__user__username', 'reason')
    # readonly_fields makes the claim_id visible but not editable manually
    readonly_fields = ('claim_id', 'filed_date')

    # Custom methods to show related data in the list view
    def get_user(self, obj):
        return obj.user_policy.user.username

    get_user.short_description = 'User'

    def get_policy(self, obj):
        return obj.user_policy.policy.name

    get_policy.short_description = 'Policy'