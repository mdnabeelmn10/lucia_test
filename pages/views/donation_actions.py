# views/donation_actions.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from ..models import Donation, DonationStatus, Vote, Document
from ..serializers import DonationWriteSerializer, DonationReadSerializer, VoteSerializer,DocumentSerializer
from ..permissions import IsDonorAdvisor, IsLuciaAdmin, IsLuciaDirector
from .pagination import DonationPagination


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
        serialized_donations = DonationReadSerializer(donations, many=True,context={'request': request}).data
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

    serializer = VoteSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # ✅ Normalize the incoming vote value so frontend "disapprove" or "reject" both work
    vote_value = serializer.validated_data.get("vote", "").lower().strip()

    # Accept flexible vote values from frontend
    if vote_value in ["reject", "rejected"]:
        vote_value = "rejected"
    elif vote_value in ["disapprove", "disapproved"]:
        vote_value = "disapprove"
    elif vote_value in ["approve", "approved"]:
        vote_value = "approve"
    elif vote_value in ["moreinfo", "more_info"]:
        vote_value = "more_info"
    elif vote_value in ["abstain", "abstained"]:
        vote_value = "abstain"

    # ✅ Check if this director already voted
    existing_vote = Vote.objects.filter(donation=donation, director=request.user).first()

    if existing_vote:
        # ✅ Update existing vote instead of rejecting
        existing_vote.vote = vote_value
        existing_vote.save(update_fields=["vote", "voted_at"])
        return Response(
            {"message": f"Vote updated to '{vote_value}'.", "data": VoteSerializer(existing_vote).data},
            status=status.HTTP_200_OK
        )

    # ✅ Otherwise, create a new vote
    vote = serializer.save(donation=donation, director=request.user, vote=vote_value)
    return Response(
        {"message": f"Vote '{vote_value}' recorded successfully.", "data": VoteSerializer(vote).data},
        status=status.HTTP_201_CREATED
    )


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

@api_view(['GET'])
def get_donations(request):
    donations = Donation.objects.all().order_by('id')
    paginator = DonationPagination()
    result_page = paginator.paginate_queryset(donations, request)
    serializer = DonationReadSerializer(result_page, many=True, context={'request': request})
    return paginator.get_paginated_response(serializer.data)
