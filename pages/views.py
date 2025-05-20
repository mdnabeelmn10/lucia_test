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

from pprint import pprint
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view

# Registration view for creating a new user
@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    if request.method == 'POST':
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Generate token for new user
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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



# Create donation recommendation
@api_view(['POST'])
@permission_classes([AllowAny])
def create_recommendation(request):
    data = request.data
    rec = DonationRecommendation.objects.create(
        daf_account_id=data['daf_account_id'],
        organization_id=data['organization_id'],
        amount=data['amount'],
        purpose=data.get('purpose', ''),
        is_anonymous=data.get('is_anonymous', False),
        public_acknowledgement=data.get('public_acknowledgement', False),
        status='pending',
        submitted_at=timezone.now()
    )
    return Response(DonationRecommendationSerializer(rec).data, status=201)



# Admin can update the recommendation status
@api_view(['PATCH'])
@permission_classes([AllowAny])
def update_recommendation_status(request, id):
    rec = DonationRecommendation.objects.get(id=id)
    status = request.data['status']
    rec.status = status
    rec.save()

    if status == 'rejected':
        Message.objects.create(
            donor_id=rec.daf_account.donor.id,
            subject="Recommendation Rejected",
            body=f"Your recommendation to {rec.organization.name} was rejected.",
            is_read=False,
            created_at=timezone.now()
        )
    return Response({'status': rec.status})



# Admin approves or rejects donations
@api_view(['PATCH'])
@permission_classes([AllowAny])
def update_donation_status(request, id):
    donation = Donation.objects.get(id=id)
    action = request.data['action']  # 'approve' or 'reject'

    if action == 'approve':
        donation.approved_at = timezone.now()
        donation.sent_at = timezone.now()
        donation.save()
    else:
        Message.objects.create(
            donor_id=donation.daf_account.donor.id,
            subject="Donation Rejected",
            body=f"Your donation to {donation.organization.name} was rejected.",
            is_read=False,
            created_at=timezone.now()
        )
        donation.delete()
        return Response({'status': 'deleted'}, status=204)

    return Response(DonationSerializer(donation).data)



# Admin uploads receipt
@api_view(['POST'])
@permission_classes([AllowAny])
def upload_receipt(request):
    data = request.data
    receipt = DonationReceipt.objects.create(
        donation_id=data['donation_id'],
        received_at=timezone.now(),
        signed_pdf_url=data['signed_pdf_url'],
        signed_by_name=data['signed_by_name']
    )
    return Response(DonationReceiptSerializer(receipt).data, status=201)



# Direct donation without recommendation but admin approval required
@api_view(['POST'])
@permission_classes([AllowAny])
def direct_donation(request):
    data = request.data
    donation = Donation.objects.create(
        recommendation=None,
        daf_account_id=data['daf_account_id'],
        organization_id=data['organization_id'],
        amount=data['amount']
    )
    return Response(DonationSerializer(donation).data, status=201)


# Dashboard View
@api_view(['GET'])
# @permission_classes([AllowAny])
def public_donor_dashboard(request, user_id):
    try:
        user = CustomUser.objects.get(id=user_id)
        donor = user.donor
        if not donor:
            return Response({"detail": "No donor linked to this user."}, status=404)
    except CustomUser.DoesNotExist:
        return Response({"detail": "User not found."}, status=404)

    donations_qs = Donation.objects.filter(donation_request__donor=donor).order_by('approved_at')

    donation_data = []
    running_total = 0
    total_donated = sum(d.amount for d in donations_qs)

    for donation in donations_qs:
        running_total += donation.amount
        donation_data.append({
            "id": donation.id,
            "amount": donation.amount,
            "approvedAt": donation.approved_at,
            "sentAt": donation.sent_at,
            "status": 'Accepted',
            "dafAccountId": donation.donation_request.daf_account.id,
            "organisation": {
                "id": donation.donation_request.organization.id,
                "name": str(donation.donation_request.organization.name)
            },
            "balanceAmount": float(donor.goal_amount) - float(running_total)
        })

    return Response({
        "userName": user.username,
        "donorName": donor.full_name,
        "goalAmount": float(donor.goal_amount),
        "currentDonatedAmount": float(total_donated),
        "donations": donation_data,
        "percentageDonated": round(100 * (float(total_donated) / float(donor.goal_amount)), 3),
        "balanceAmount": float(donor.goal_amount) - float(total_donated)
    })
