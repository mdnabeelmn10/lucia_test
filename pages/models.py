# Updated models.py for Lucia Charitable

import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# ---- ENUMS (using Django's TextChoices for clarity) ----

class UserRole(models.TextChoices):
    DONOR_ADVISOR = 'donor_advisor', 'Donor Advisor'
    LUCIA_DIRECTOR = 'lucia_director', 'Lucia Director'
    LUCIA_ADMIN = 'lucia_admin', 'Lucia Admin'

class DonationStatus(models.TextChoices):
    PENDING_REVIEW = 'pending_review', 'Pending Review'
    COMPLETED = 'completed', 'Completed'
    REJECTED = 'rejected', 'Rejected'
    APPROVED = 'approved', 'Approved'

class VoteType(models.TextChoices):
    APPROVE = 'approve', 'Approve'
    DISAPPROVE = 'disapprove', 'Disapprove'
    ABSTAIN = 'abstain', 'Abstain'
    MORE_INFO = 'more_info', 'More Info'

class DocumentType(models.TextChoices):
    SIGNED_RECEIPT = 'signed_receipt', 'Signed Receipt'
    TAX_DETERMINATION_LETTER = 'tax_determination_letter', 'Tax Determination Letter'
    SUPPORTING_DOCUMENTATION = 'supporting_documentation', 'Supporting Documentation'

class FundingRequestStatus(models.TextChoices):
    PENDING_VETTING = 'pending_vetting', 'Pending Vetting'
    PENDING_DONOR_APPROVAL = 'pending_donor_approval', 'Pending Donor Approval'
    CROWDFUND_ACTIVE = 'crowdfund_active', 'Crowdfund Active'
    REJECTED = 'rejected', 'Rejected'


# ---- MODELS ----

class User(AbstractUser):
    """ The "Members List" notebook. It keeps track of every person who can log in. """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.DONOR_ADVISOR, help_text="Defines user permissions within the system (RBAC).")
    mfa_secret = models.CharField(max_length=255, blank=True, null=True, help_text="Secret key for Multi-Factor Authentication for secure login.")

class DAF(models.Model):
    """ The "Charity Accounts" logbook. It lists all the special Donor Advised Fund (DAF) accounts. """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text='The special name for the account, like "The Dr. Shiney Jeyaraj Family Fund".')
    advisors = models.ManyToManyField(User, related_name='advised_dafs', through='DAF_Advisor')
    altruist_account_id = models.CharField(max_length=255, blank=True, null=True, help_text="ID for the corresponding brokerage account at Altruist.com.")
    annual_giving_target = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="The yearly donation goal a donor can set for themselves.")
    is_public_profile_active = models.BooleanField(default=False, help_text="A yes/no switch to mark if the DAF should be listed publicly for charities to see.")
    public_profile_description = models.TextField(blank=True, null=True, help_text="If the profile is public, this field holds a brief description of the DAF's interests and priorities.")

class DAF_Advisor(models.Model):
    """ A simple "Account Connector." Its only job is to link people from the Users notebook to the DAFs they manage. """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    daf = models.ForeignKey(DAF, on_delete=models.CASCADE)
    class Meta:
        unique_together = ('user', 'daf')

class Charity(models.Model):
    """ The "Address Book for Charities." It keeps a directory of all the charities that have been recommended. """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True, help_text="The official name of the charitable organization.")
    tin = models.CharField(max_length=20, unique=True, help_text="The charity's unique Tax Identification Number.")
    address = models.TextField(help_text="The mailing address for the charity.")
    website = models.URLField(max_length=200, blank=True, null=True, help_text="The charity's official website.")
    contact_name = models.CharField(max_length=255, blank=True, null=True, help_text="A contact person at the organization.")
    contact_email = models.EmailField(blank=True, null=True, help_text="The contact person's email address.")
    contact_telephone = models.CharField(max_length=20, blank=True, null=True, help_text="The contact person's telephone number.")
    tax_exempt = models.BooleanField(default=False,help_text="Is the charity exempted from tax?")

class Donation(models.Model):
    """ The "Donation Logbook." This is the most important table, tracking every donation from start to finish. """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recommending_user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='donations')
    source_daf = models.ForeignKey(DAF, on_delete=models.PROTECT, related_name='donations')
    recipient_charity = models.ForeignKey(Charity, on_delete=models.PROTECT, related_name='donations')
    status = models.CharField(max_length=20, choices=DonationStatus.choices, default=DonationStatus.PENDING_REVIEW, help_text='A label showing the current stage of the donation.')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    purpose = models.TextField(default='General Support', help_text="A note explaining the reason for the donation.")
    is_anonymous = models.BooleanField(default=False, help_text="A yes/no switch for if the gift should be anonymous (from Lucia Charitable) or from their DAF.")
    is_recurring = models.BooleanField(default=False, help_text="A yes/no switch for if the donor wants this to be a recurring donation.")
    is_shareable_in_catalog = models.BooleanField(default=False, help_text="A yes/no switch for if the donor wants to recommend this charity to other donors.")
    date_recommended = models.DateTimeField(auto_now_add=True)
    date_approved = models.DateTimeField(null=True, blank=True)
    date_disbursed = models.DateTimeField(null=True, blank=True)

class Recurring_Donation(models.Model):
    """ The "Automatic Payments Scheduler." It holds the schedule for recurring gifts. """
    donation = models.OneToOneField(Donation, primary_key=True, on_delete=models.CASCADE)
    interval = models.CharField(max_length=50, help_text='Notes how often the donation should be made (e.g., "monthly", "annually").')
    special_instructions = models.TextField(blank=True, null=True, help_text='Holds any other special notes about the schedule.')

class Vote(models.Model):
    """ The "Voting Tally Sheet." It records how each Lucia director votes on a recommendation. """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    donation = models.ForeignKey(Donation, on_delete=models.CASCADE, related_name='votes')
    director = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': UserRole.LUCIA_DIRECTOR})
    vote = models.CharField(max_length=20, choices=VoteType.choices, help_text='The actual vote: "approve", "disapprove", or "more_info".')
    voted_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('donation', 'director')

class Document(models.Model):
    """ The "Digital Filing Cabinet." It keeps links to all important files. """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    donation = models.ForeignKey(Donation, on_delete=models.CASCADE, null=True, blank=True, related_name='documents')
    funding_request = models.ForeignKey('Funding_Request', on_delete=models.CASCADE, null=True, blank=True, related_name='documents')
    document_type = models.CharField(max_length=50, choices=DocumentType.choices)
    file_url = models.URLField(max_length=1024, help_text="The actual web link to where the document is securely stored.")

class Funding_Request(models.Model):
    """ The "Incoming Mailbox from Charities." It holds funding requests submitted by charities. """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requesting_organization_name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255)
    organization_address = models.TextField()
    purpose = models.TextField()
    amount_requested = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=30, choices=FundingRequestStatus.choices, default=FundingRequestStatus.PENDING_VETTING, help_text='The current stage of the request, such as "pending_vetting" by a Lucia Manager.')
    is_crowdfund = models.BooleanField(default=False, help_text="A yes/no switch to show if this is a general request for the crowdfunding platform.")
    target_daf = models.ForeignKey(DAF, on_delete=models.CASCADE, null=True, blank=True, help_text="If the request is for one specific DAF, this links to that DAF's account.")

class Pledge(models.Model):
    """ The "Group Project Pledge Tracker." It tracks which donors have "chipped in" on a crowdfunding project. """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    funding_request = models.ForeignKey(Funding_Request, on_delete=models.CASCADE, related_name='pledges')
    pledging_daf = models.ForeignKey(DAF, on_delete=models.CASCADE, related_name='pledges')
    amount_pledged = models.DecimalField(max_digits=12, decimal_places=2)
    is_contingent = models.BooleanField(default=False, help_text="A yes/no switch for if the pledge only counts if the project's overall funding goal is met.")

class Message(models.Model):
    """ Corresponds to the internal message center for communicating with donors. """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages')
    subject = models.CharField(max_length=255)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class PasswordResetToken(models.Model):
    """ A temporary token to allow a user to reset their password securely. """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()