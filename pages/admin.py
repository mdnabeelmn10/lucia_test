from django.contrib import admin
from .models import (
    Donor, 
    CustomUser, 
    DAFAccount, 
    Organization, 
    DonationRecommendation, 
    DonationRequest,
    Donation,
    DonationReceipt, 
    Vote,
    Message, 
    PasswordReset, 
    Admin
)

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'role', 'donor')
    search_fields = ('username', 'email')
    list_filter = ('role',)

@admin.register(Donor)
class DonorAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'email', 'phone', 'goal_amount', 'created_at')
    search_fields = ('full_name', 'email')

@admin.register(DAFAccount)
class DAFAccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'donor', 'brokerage_url', 'balance', 'created_at')
    search_fields = ('donor__full_name',)

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'ein', 'website', 'created_by_donor', 'created_at')
    search_fields = ('name', 'ein')

@admin.register(DonationRecommendation)
class DonationRecommendationAdmin(admin.ModelAdmin):
    list_display = ('id', 'daf_account', 'organization', 'amount', 'status', 'submitted_at')
    list_filter = ('status',)
    search_fields = ('organization__name',)

@admin.register(DonationRequest)
class DonationRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'donor', 'daf_account', 'organization', 'amount', 'status', 'submitted_at', 'reviewed_at', 'reviewed_by')
    list_filter = ('status',)
    search_fields = ('donor__full_name', 'organization__name')

@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('id', 'donation_request', 'amount', 'approved_at', 'sent_at')
    search_fields = ('donation_request__donor__full_name',)

@admin.register(DonationReceipt)
class DonationReceiptAdmin(admin.ModelAdmin):
    list_display = ('id', 'donation', 'received_at', 'signed_by_name')
    search_fields = ('signed_by_name',)

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'recommendation', 'admin', 'decision', 'voted_at')
    list_filter = ('decision',)
    search_fields = ('admin__name',)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'donor', 'subject', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('donor__full_name', 'subject')

@admin.register(PasswordReset)
class PasswordResetAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'token', 'created_at', 'expires_at')
    search_fields = ('user__username',)

@admin.register(Admin)
class AdminAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'role')
    search_fields = ('name', 'email')

