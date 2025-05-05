from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# Custom User Model
class CustomUser(AbstractUser):
    donor = models.ForeignKey('Donor', on_delete=models.CASCADE, null=True, blank=True)
    role = models.CharField(max_length=20, choices=[
        ('admin', 'Admin'),
        ('donor', 'Donor'),
    ])

# Donor Model
class Donor(models.Model):
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    goal_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name

# DAF Account Model
class DAFAccount(models.Model):
    donor = models.ForeignKey(Donor, on_delete=models.CASCADE)
    brokerage_url = models.URLField()
    balance = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"DAF Account for {self.donor.full_name}"

# Organization Model
class Organization(models.Model):
    name = models.CharField(max_length=255)
    ein = models.CharField(max_length=50)
    address = models.TextField()
    website = models.URLField()
    created_by_donor = models.ForeignKey(Donor, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

# Donation Recommendation Model
class DonationRecommendation(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    daf_account = models.ForeignKey(DAFAccount, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    purpose = models.TextField()
    is_anonymous = models.BooleanField(default=False)
    public_acknowledgement = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Recommendation to {self.organization.name}"

# Admin Model (For managing donations and recommendations)
class Admin(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=100)

    def __str__(self):
        return self.name

# Donation Request Model
class DonationRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    recommendation = models.ForeignKey(DonationRecommendation, null=True, blank=True, on_delete=models.SET_NULL)
    donor = models.ForeignKey(Donor, on_delete=models.CASCADE)
    daf_account = models.ForeignKey(DAFAccount, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(Admin, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Donation Request by {self.donor.full_name}"

# Donation Model
class Donation(models.Model):
    donation_request = models.OneToOneField(DonationRequest, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    approved_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Donation to {self.donation_request.organization.name}"

# Donation Receipt Model
class DonationReceipt(models.Model):
    donation = models.OneToOneField(Donation, on_delete=models.CASCADE)
    received_at = models.DateTimeField()
    signed_pdf_url = models.URLField()
    signed_by_name = models.CharField(max_length=255)

    def __str__(self):
        return f"Receipt for Donation {self.donation.id}"

# Vote Model (For admins voting on donations)
class Vote(models.Model):
    DECISION_CHOICES = (
        ('approve', 'Approve'),
        ('disapprove', 'Disapprove'),
        ('abstain', 'Abstain'),
    )

    recommendation = models.ForeignKey(DonationRecommendation, on_delete=models.CASCADE)
    admin = models.ForeignKey(Admin, on_delete=models.CASCADE)
    decision = models.CharField(max_length=20, choices=DECISION_CHOICES)
    comment = models.TextField()
    voted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Vote on {self.recommendation}"

# Message Model (For communications between donor and admin)
class Message(models.Model):
    donor = models.ForeignKey(Donor, on_delete=models.CASCADE)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.donor.full_name}"

# Password Reset Model
class PasswordReset(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"Password Reset for {self.user.username}"
