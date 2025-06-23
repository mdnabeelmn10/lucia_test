from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from .permissions import IsAdminUser, IsDonorUser
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from django.utils import timezone
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from .models import DonationRecommendation, Donation, DonationReceipt, Message
from .serializers import (
    DonationRecommendationSerializer,
    DonationSerializer,
    DonationReceiptSerializer,
    LoginSerializer,
    UserRegisterSerializer,
    CustomUser
)
from decimal import Decimal, InvalidOperation
from pprint import pprint
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view


@api_view(['POST'])
@permission_classes([AllowAny])
def update_password_by_email(request):
    email = request.data.get('email')
    new_password = request.data.get('new_password')

    if not email or not new_password:
        return Response(
            {"detail": "Email and new_password are required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    User = get_user_model()

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response(
            {"detail": "User with this email does not exist."},
            status=status.HTTP_404_NOT_FOUND
        )

    user.set_password(new_password)
    user.save()

    return Response(
        {"detail": "Password updated successfully."},
        status=status.HTTP_200_OK
    )



@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data['email']
    password = serializer.validated_data['password']

    try:
        User = get_user_model()
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response(
            {"detail": "Invalid email or password."},
            status=status.HTTP_401_UNAUTHORIZED
        )

    user = authenticate(request, username=user.username, password=password)

    if user is None:
        return Response(
            {"detail": "Invalid email or password."},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.is_active:
        return Response(
            {"detail": "User account is disabled."},
            status=status.HTTP_403_FORBIDDEN
        )

    # Get donor ID from related object
    donor_id = getattr(user.donor, 'id', None)  # Safe access to related Donor object

    refresh = RefreshToken.for_user(user)

    return Response({
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': getattr(user, 'role', None),
            'donorId': donor_id,
        }
    }, status=status.HTTP_200_OK)



# Helper function to generate dashboard data
def _get_donor_dashboard_data(donor, user):
    """
    Generates the dictionary for the donor dashboard response.
    """
    donations_qs = Donation.objects.filter(donation_request__donor=donor).order_by('approved_at')

    donation_data = []
    running_total = 0
    total_donated = sum(d.amount for d in donations_qs)

    # Avoid division by zero if the goal amount is 0
    percentage_donated = 0
    if float(donor.goal_amount) > 0:
        percentage_donated = round(100 * (float(total_donated) / float(donor.goal_amount)), 3)

    for donation in donations_qs:
        running_total += donation.amount
        donation_data.append({
            "id": donation.id,
            "amount": donation.amount,
            "approvedAt": donation.approved_at,
            "sentAt": donation.sent_at,
            "purpose": "Purpose",
            "dafAccountId": donation.donation_request.daf_account.id,
            "organisation": {
                "id": donation.donation_request.organization.id,
                "name": str(donation.donation_request.organization.name)
            },
            "balanceAmount": float(donor.goal_amount) - float(running_total)
        })

    return {
        "user": {
            "id": user.id,
            "userName": user.username,
        },
        "donorName": donor.full_name,
        "goalAmount": float(donor.goal_amount),
        "currentDonatedAmount": float(total_donated),
        "donations": donation_data,
        "percentageDonated": percentage_donated,
        "balanceAmount": float(donor.goal_amount) - float(total_donated)
    }


# Refactored Dashboard View
@api_view(['GET'])
# @permission_classes([AllowAny])
def public_donor_dashboard(request, user_id):
    """
    Retrieves the public dashboard data for a specific donor.
    """
    try:
        user = CustomUser.objects.get(id=user_id)
        donor = user.donor
        if not donor:
            return Response({"detail": "No donor linked to this user."}, status=status.HTTP_404_NOT_FOUND)
    except CustomUser.DoesNotExist:
        return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    # Generate and return the dashboard data using the helper
    dashboard_data = _get_donor_dashboard_data(donor, user)
    
    return Response(dashboard_data)



@api_view(['PUT'])
# @permission_classes([AllowAny])
def update_donor_dashboard(request, user_id):
    """
    Updates the goal amount for a specific donor and returns the
    refreshed dashboard data.
    """
    try:
        user = CustomUser.objects.get(id=user_id)
        donor = user.donor
        if not donor:
            return Response(
                {"detail": "No donor linked to this user."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
    except CustomUser.DoesNotExist:
        return Response(
            {"detail": "User not found."}, 
            status=status.HTTP_404_NOT_FOUND
        )

    # 1. Get new goal amount from request body
    new_goal_amount_str = request.data.get('goalAmount')
    if new_goal_amount_str is None:
        return Response(
            {"detail": "The 'goalAmount' field is required in the request body."}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    # 2. Validate the new goal amount
    try:
        new_goal_amount = float(new_goal_amount_str)
        if new_goal_amount < 0:
            return Response(
                {"detail": "The 'goalAmount' must be a positive number."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except (ValueError, TypeError):
        return Response(
            {"detail": "Invalid 'goalAmount' format. Must be a valid number."}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    # 3. Update the donor's goal amount and save
    donor.goal_amount = new_goal_amount
    donor.save()

    # 4. Generate and return the updated dashboard data using the helper
    dashboard_data = _get_donor_dashboard_data(donor, user)
    
    return Response(dashboard_data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_donation_details(request, donation_id):
    """
    Retrieves the details of a single donation by its unique ID.
    """
    try:
        # Updated .select_related() to fetch only the necessary related objects.
        donation = Donation.objects.select_related(
            'donation_request__organization',
            'donation_request__daf_account'
        ).get(id=donation_id)

    except Donation.DoesNotExist:
        # If no donation is found, return a standard 404 error.
        return Response(
            {"detail": f"Donation with ID {donation_id} not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    # Construct the response dictionary without the balanceAmount field.
    response_data = {
        "id": donation.id,
        "amount": donation.amount,
        "approvedAt": donation.approved_at,
        "sentAt": donation.sent_at,
        "purpose": 'Purpose',
        "dafAccountId": donation.donation_request.daf_account.id,
        "organisation": {
            "id": donation.donation_request.organization.id,
            "name": str(donation.donation_request.organization.name)
        }
    }

    return Response(response_data, status=status.HTTP_200_OK)



@api_view(['PUT'])
# @permission_classes([IsAuthenticated]) # Secure this endpoint appropriately
def update_donation_details(request, donation_id):
    """
    Updates the details of a single donation by its unique ID.
    Accepts 'amount', 'approved_at', 'sent_at', and 'purpose' in the request body.
    """
    try:
        # Fetch the donation object that needs to be updated.
        donation = Donation.objects.select_related(
            'donation_request'
        ).get(id=donation_id)
        
    except Donation.DoesNotExist:
        return Response(
            {"detail": f"Donation with ID {donation_id} not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    # --- Update Fields based on Request Data ---
    data = request.data
    donation_request = donation.donation_request # Get the related request object
    
    # Update 'amount' if provided and valid
    if 'amount' in data:
        try:
            donation.amount = Decimal(data['amount'])
        except (InvalidOperation, TypeError):
            return Response({"detail": "Invalid format for 'amount'."}, status=status.HTTP_400_BAD_REQUEST)

    # Update 'approved_at' if provided
    if 'approved_at' in data:
        # Note: You may want to add date parsing/validation here if needed
        donation.approved_at = data['approved_at']

    # Update 'sent_at' if provided
    if 'sent_at' in data:
        donation.sent_at = data['sent_at']
        
    # Update 'purpose' on the related DonationRequest model
    if 'purpose' in data:
        donation_request.purpose = data['purpose']

    # Save the updated objects to the database
    donation.save()
    donation_request.save()

    # --- Construct and Return the Updated Data ---
    # The response format matches the GET endpoint for consistency.
    response_data = {
        "id": donation.id,
        "amount": donation.amount,
        "approvedAt": donation.approved_at,
        "sentAt": donation.sent_at,
        "purpose": donation_request.purpose, # Get purpose from the request object
        "dafAccountId": donation.donation_request.daf_account.id,
        "organisation": {
            "id": donation.donation_request.organization.id,
            "name": str(donation.donation_request.organization.name)
        }
    }

    return Response(response_data, status=status.HTTP_200_OK)