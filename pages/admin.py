# In your app's admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User,
    DAF,
    DAF_Advisor,
    Charity,
    Donation,
    Recurring_Donation,
    Vote,
    Document,
    Funding_Request,
    Pledge,
    Message
)

# --- Inlines for a Better Admin Experience ---

class DAFAdvisorInline(admin.TabularInline):
    """Allows managing which users advise a DAF directly from the DAF or User page."""
    model = DAF_Advisor
    extra = 1 # Shows one empty slot for easily adding a new advisor.

class VoteInline(admin.TabularInline):
    """Allows for viewing all votes for a donation directly on the donation's page."""
    model = Vote
    extra = 0 # Don't show empty slots for new votes by default.
    readonly_fields = ('director', 'vote', 'voted_at') # Votes can't be changed here.
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

# --- Main ModelAdmin Configurations ---

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    A custom admin for our User model. It adds the 'role' to the display
    and allows for editing DAF associations inline.
    """
    # Add our custom 'role' field to the main user form
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Custom User Info', {'fields': ('role',)}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Custom User Info', {'fields': ('role',)}),
    )
    list_display = ('id', 'username', 'email', 'first_name', 'last_name', 'role', 'is_staff')
    list_filter = BaseUserAdmin.list_filter + ('role',)
    inlines = [DAFAdvisorInline]

@admin.register(DAF)
class DAFAdmin(admin.ModelAdmin):
    """Admin view for Donor Advised Funds."""
    list_display = ('id', 'name', 'annual_giving_target', 'is_public_profile_active')
    search_fields = ('name',)
    inlines = [DAFAdvisorInline]

@admin.register(Charity)
class CharityAdmin(admin.ModelAdmin):
    """Admin view for recipient charities."""
    list_display = ('id', 'name', 'tin', 'address')
    search_fields = ('name', 'tin')

@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    """
    Admin view for Donations. This is a central place to monitor the
    donation lifecycle from recommendation to completion.
    """
    list_display = ('id', 'source_daf', 'recipient_charity', 'amount', 'status', 'date_recommended')
    list_filter = ('status', 'is_anonymous', 'is_recurring')
    search_fields = ('id__iexact', 'source_daf__name', 'recipient_charity__name', 'purpose')
    readonly_fields = ('date_recommended', 'date_approved', 'date_disbursed')
    inlines = [VoteInline] # Show votes cast for this donation. 

@admin.register(Recurring_Donation)
class RecurringDonationAdmin(admin.ModelAdmin):
    """Admin view for recurring donation schedules."""
    list_display = ('donation', 'interval', 'special_instructions')

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    """
    Admin view for Votes. Allows admins to see the voting history, which corresponds
    to the director voting process. 
    """
    list_display = ('id', 'donation', 'director', 'vote', 'voted_at')
    list_filter = ('vote',)
    search_fields = ('donation__id', 'director__username')

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Admin view for all uploaded documents like receipts and tax letters."""
    list_display = ('id', 'document_type', 'file_url', 'donation', 'funding_request')
    list_filter = ('document_type',)

@admin.register(Funding_Request)
class FundingRequestAdmin(admin.ModelAdmin):
    """
    Admin view for inbound funding requests from charities.
    This is where a manager can vet new requests. 
    """
    list_display = ('id', 'requesting_organization_name', 'amount_requested', 'status', 'is_crowdfund', 'target_daf')
    list_filter = ('status', 'is_crowdfund')
    search_fields = ('requesting_organization_name', 'purpose')

@admin.register(Pledge)
class PledgeAdmin(admin.ModelAdmin):
    """
    Admin view for crowdfunding pledges.
    Tracks which DAFs have "chipped in" to a project. 
    """
    list_display = ('id', 'funding_request', 'pledging_daf', 'amount_pledged', 'is_contingent')
    list_filter = ('is_contingent',)
    search_fields = ('funding_request__requesting_organization_name', 'pledging_daf__name')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Admin view for the internal messaging system."""
    list_display = ('id', 'recipient', 'subject', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('recipient__username', 'subject')