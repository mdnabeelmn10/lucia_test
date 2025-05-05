from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from .permissions import IsAdminUser, IsDonorUser
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from django.utils import timezone
from .models import DonationRecommendation, Donation, DonationReceipt, Message
from .serializers import (
    DonationRecommendationSerializer,
    DonationSerializer,
    DonationReceiptSerializer,
    UserRegisterSerializer,
    CustomUser
)

from pprint import pprint
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework_simplejwt.tokens import RefreshToken

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



# Endpoint to login and get JWT token
@api_view(['POST'])
@permission_classes([IsAuthenticated])  # Only authenticated users can get a token
def login_view(request):
    refresh = RefreshToken.for_user(request.user)
    return Response({
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    })



# Create donation recommendation
@api_view(['POST'])
@permission_classes([IsDonorUser])
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
@permission_classes([IsAdminUser])
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
@permission_classes([IsAdminUser])
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
@permission_classes([IsAdminUser])
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
@permission_classes([IsDonorUser])
def direct_donation(request):
    data = request.data
    donation = Donation.objects.create(
        recommendation=None,
        daf_account_id=data['daf_account_id'],
        organization_id=data['organization_id'],
        amount=data['amount']
    )
    return Response(DonationSerializer(donation).data, status=201)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_donor_dashboard(request, user_id):
    try:
        user = CustomUser.objects.get(id=user_id)
        donor = user.donor
        if not donor:
            return Response({"detail": "No donor linked to this user."}, status=404)
    except CustomUser.DoesNotExist:
        return Response({"detail": "User not found."}, status=404)

    donations = Donation.objects.filter(donation_request__donor=donor).order_by('approved_at')

    donation_data = []
    running_total = 0

    for donation in donations:
        amount = donation.amount
        running_total += amount

        donation_data.append({
            "id": donation.id,
            "amount": amount,
            "approvedAt": donation.approved_at,
            "sentAt": donation.sent_at,
            "dafAccountId": donation.donation_request.daf_account.id,
            "organisation": {
                "id": donation.donation_request.organization.id,
                "name": str(donation.donation_request.organization.name)
            },
            "currentDonatedAmount": running_total,
            "balanceAmount": float(donor.goal_amount) - float(running_total)
        })

    return Response({
        "userId": user.id,
        "goalAmount": float(donor.goal_amount),
        "currentDonatedAmount": float(running_total),
        "donations": donation_data
    })