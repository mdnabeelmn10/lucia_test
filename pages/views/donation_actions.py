# views/donation_actions.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from ..models import Donation, DonationStatus, Vote, Document
from ..serializers import DonationWriteSerializer, DonationReadSerializer, VoteSerializer,DocumentSerializer
from ..permissions import IsDonorAdvisor, IsLuciaAdmin, IsLuciaDirector


@api_view(['GET', 'POST'])
@permission_classes([IsDonorAdvisor | IsLuciaAdmin])
def create_donation(request):
    if request.method == 'POST':
        serializer = DonationWriteSerializer(data=request.data)
        if serializer.is_valid():
            donation = serializer.save(
                recommending_user=request.user,
                status=DonationStatus.PENDING_REVIEW
            )
            return Response(DonationReadSerializer(donation).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    if request.method == 'GET':
        donations = Donation.objects.all()
        serialized_donations = DonationReadSerializer(donations, many=True).data
        return Response(serialized_donations, status=status.HTTP_200_OK)

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


# @api_view(['POST'])
# @permission_classes([IsLuciaDirector])
# def cast_vote(request, id):
#     donation = get_object_or_404(Donation, id=id)
#     serializer = VoteSerializer(data=request.data)
#     if serializer.is_valid():
#         serializer.save(donation=donation, director=request.user)
#         return Response(serializer.data, status=status.HTTP_201_CREATED)
#     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# @api_view(['POST'])
# @permission_classes([IsLuciaDirector])
# def cast_vote(request, id):
#     donation = get_object_or_404(Donation, id=id)

#     # prevent duplicate votes by the same director
#     if Vote.objects.filter(donation=donation, director=request.user).exists():
#         return Response(
#             {"detail": "You have already voted on this donation."},
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     serializer = VoteSerializer(data=request.data)
#     if serializer.is_valid():
#         vote = serializer.save(donation=donation, director=request.user)
#         return Response(
#             VoteSerializer(vote).data,
#             status=status.HTTP_201_CREATED
#         )

#     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsLuciaDirector])
def cast_vote(request, id):
    donation = get_object_or_404(Donation, id=id)

    # prevent duplicate votes
    if Vote.objects.filter(donation=donation, director=request.user).exists():
        return Response(
            {"detail": "You have already voted on this donation."},
            status=status.HTTP_400_BAD_REQUEST
        )

    serializer = VoteSerializer(data=request.data)
    if serializer.is_valid():
        vote = serializer.save(donation=donation, director=request.user)

        # Optional: also update donation.director_vote for convenience
        donation.director_vote = vote.vote
        donation.save(update_fields=["director_vote"])

        return Response(VoteSerializer(vote).data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(['POST'])
@permission_classes([IsLuciaAdmin])
def upload_donation_document(request, donation_id):
    try:
        donation = Donation.objects.get(pk=donation_id)
    except Donation.DoesNotExist:
        return Response({"error": "Donation not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = DocumentSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(donation=donation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
