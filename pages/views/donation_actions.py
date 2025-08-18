# views/donation_actions.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from ..models import Donation, DonationStatus, Vote
from ..serializers import DonationWriteSerializer, DonationReadSerializer, VoteSerializer
from ..permissions import IsDonorAdvisor, IsLuciaAdmin, IsLuciaDirector


@api_view(['POST'])
@permission_classes([IsDonorAdvisor])
def create_donation(request):
    serializer = DonationWriteSerializer(data=request.data)
    if serializer.is_valid():
        donation = serializer.save(
            recommending_user=request.user,
            status=DonationStatus.PENDING_REVIEW
        )
        return Response(DonationReadSerializer(donation).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PATCH'])
@permission_classes([IsLuciaAdmin])
def update_donation_status(request, id):
    donation = get_object_or_404(Donation, id=id)
    new_status = request.data.get("status")

    if new_status not in DonationStatus.values:
        return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)

    donation.status = new_status
    donation.save()
    return Response(DonationReadSerializer(donation).data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsLuciaDirector])
def cast_vote(request, id):
    donation = get_object_or_404(Donation, id=id)
    serializer = VoteSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(donation=donation, director=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
