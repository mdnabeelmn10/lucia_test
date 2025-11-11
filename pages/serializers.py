from rest_framework import serializers
from .models import User, DAF, Charity, Donation, Vote, Funding_Request,Document
from .utils import is_majority_approved

class UserRegisterSerializer(serializers.ModelSerializer):
    """ Serializer for creating a new user. """
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class LoginSerializer(serializers.Serializer):
    """ Serializer for validating login credentials. """
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)

class UserSerializer(serializers.ModelSerializer):
    """ Serializer for reading user data. """
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'role']

class DAFSerializer(serializers.ModelSerializer):
    """ Serializer for the DAF model. """
    class Meta:
        model = DAF
        fields = '__all__'

class CharitySerializer(serializers.ModelSerializer):
    """ Serializer for the Charity model. """
    class Meta:
        model = Charity
        fields = '__all__'


class CharityNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Charity
        fields = ['name', 'tin', 'address', 'website', 'contact_name', 'contact_email', 'contact_telephone']
        extra_kwargs = {
            'tin': {'validators': []},
        }

class DonationReadSerializer(serializers.ModelSerializer):
    recipient_charity = CharitySerializer(read_only=True)
    source_daf = DAFSerializer(read_only=True)
    director_vote = serializers.SerializerMethodField()
    all_votes = serializers.SerializerMethodField()
    is_approved = serializers.SerializerMethodField()

    class Meta:
        model = Donation
        fields = [
            'id',
            'amount',
            'purpose',
            'is_anonymous',
            'status',
            'date_recommended',
            'recipient_charity',
            'source_daf',
            'director_vote',
            'all_votes',
            'is_approved',
        ]

    def get_director_vote(self, obj):
        request = self.context.get('request', None)
        if not request or not hasattr(request, "user"):
            return None
        user = request.user
        vote = obj.votes.filter(director=user).first()
        return vote.vote if vote else None

    def get_all_votes(self, obj):
        votes = obj.votes.all()
        return [
            {"director": v.director.username, "vote": v.vote, "voted_at": v.voted_at}
            for v in votes
        ]

    def get_is_approved(self, obj):
        return is_majority_approved(obj)


# class DonationReadSerializer(serializers.ModelSerializer):
#     """Serializer for reading donation data with nested details + director's vote."""
#     recipient_charity = CharitySerializer(read_only=True)
#     source_daf = DAFSerializer(read_only=True)
#     director_vote = serializers.SerializerMethodField()

#     class Meta:
#         model = Donation
#         fields = [
#             'id',
#             'amount',
#             'purpose',
#             'is_anonymous',
#             'status',
#             'date_recommended',
#             'recipient_charity',
#             'source_daf',
#             'director_vote',
#         ]

#     def get_director_vote(self, obj):
#         """Return the current director's vote if available, otherwise None."""
#         request = self.context.get('request', None)
#         if request is None or not hasattr(request, "user"):
#             return None

#         user = request.user
#         vote = obj.votes.filter(director=user).first()
#         return vote.vote if vote else None


class DonationWriteSerializer(serializers.ModelSerializer):
    recipient_charity = serializers.SlugRelatedField(
        slug_field='tin',
        queryset=Charity.objects.all()
    )
    class Meta:
        model = Donation
        fields = [
            'source_daf',
            'recipient_charity',
            'amount',
            'purpose',
            'is_anonymous',
            'is_recurring',
            'is_shareable_in_catalog'
        ]

class VoteSerializer(serializers.ModelSerializer):
    """
    Serializer for director votes.
    """
    class Meta:
        model = Vote
        fields = ['id', 'donation', 'director', 'vote', 'voted_at']
        read_only_fields = ['id', 'donation', 'director', 'voted_at']

# class VoteSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Vote
#         fields = ['id', 'donation', 'director', 'vote', 'voted_at']
#         read_only_fields = ['id', 'donation', 'director', 'voted_at']


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'donation', 'funding_request', 'document_type', 'file_url']
        read_only_fields = ['id', 'donation', 'funding_request']


class FundingRequestSerializer(serializers.ModelSerializer):
    """ Full serializer for internal/admin use. """
    class Meta:
        model = Funding_Request
        fields = [
            'id',
            'requesting_organization_name',
            'contact_person',
            'organization_address',
            'purpose',
            'amount_requested',
            'status',
            'is_crowdfund',
            'target_daf',
        ]
        read_only_fields = ['id', 'status']  # status handled internally


class FundingRequestPublicSerializer(serializers.ModelSerializer):
    """ Restricted serializer for public viewing. """
    class Meta:
        model = Funding_Request
        fields = [
            'id',
            'requesting_organization_name',
            'contact_person',
            'organization_address',
            'purpose',
            'amount_requested',
            'is_crowdfund',
        ]

class CharityVerificationSerializer(serializers.Serializer):
    name = serializers.CharField(allow_null=True, required=False)
    tin = serializers.CharField(allow_null=True, required=False)
    address = serializers.CharField(allow_null=True, required=False)
    website = serializers.URLField(allow_null=True, required=False)
    contactEmail = serializers.EmailField(allow_null=True, required=False)
    contactTelephone = serializers.CharField(allow_null=True, required=False)
    irs_revoked = serializers.BooleanField(default=False)
    source = serializers.ListField(child=serializers.CharField())
