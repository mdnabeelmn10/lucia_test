# In your app's serializers.py

from rest_framework import serializers
from .models import User, DAF, Charity, Donation, Vote

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

class DonationReadSerializer(serializers.ModelSerializer):
    """ Serializer for reading donation data with nested details. """
    recipient_charity = CharitySerializer(read_only=True)
    source_daf = DAFSerializer(read_only=True)
    class Meta:
        model = Donation
        fields = ['id', 'amount', 'purpose', 'is_anonymous', 'status', 'date_recommended', 'recipient_charity', 'source_daf']

class CharityNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Charity
        fields = ['name', 'tin', 'address', 'website', 'contact_name', 'contact_email', 'contact_telephone']
        extra_kwargs = {
            'tin': {'validators': []},
        }

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
    """ Serializer for recording votes. """
    class Meta:
        model = Vote
        fields = ('vote',)