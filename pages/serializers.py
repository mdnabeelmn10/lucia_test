from rest_framework import serializers
from .models import (
    DonationRecommendation, 
    Donation, 
    DonationReceipt,
    CustomUser
)

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password']

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user
    
class DonationRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DonationRecommendation
        fields = '__all__'

class DonationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Donation
        fields = '__all__'

class DonationReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = DonationReceipt
        fields = '__all__'