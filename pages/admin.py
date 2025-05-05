from django.contrib import admin
from .models import (
    Donor, 
    CustomUser, 
    DAFAccount, 
    Organization, 
    DonationRecommendation, 
    DonationRequest,
    Donation,
    DonationReceipt, Vote,
    Message, PasswordReset, Admin
)

admin.site.register(Donor)
admin.site.register(CustomUser)
admin.site.register(DAFAccount)
admin.site.register(Organization)
admin.site.register(DonationRecommendation)
admin.site.register(DonationRequest)
admin.site.register(Donation)
admin.site.register(DonationReceipt)
admin.site.register(Vote)
admin.site.register(Message)
admin.site.register(PasswordReset)
admin.site.register(Admin)

