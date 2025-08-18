from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from ..models import Charity, Funding_Request, FundingRequestStatus
from ..serializers import CharitySerializer, FundingRequestSerializer
from ..permissions import IsLuciaAdmin

@api_view(['POST'])
@permission_classes([IsLuciaAdmin])
def create_charity(request):
    serializer = CharitySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([])  # public endpoint
def submit_funding_request(request):
    serializer = FundingRequestSerializer(data=request.data)
    if serializer.is_valid():
        # Force all new requests into "pending_vetting" status
        serializer.save(status=FundingRequestStatus.PENDING_VETTING)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsLuciaAdmin])
def list_all_funding_requests(request):
    requests = Funding_Request.objects.all()
    serializer = FundingRequestSerializer(requests, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([])  # anyone can view
def get_funding_request(request, id):
    funding_request = get_object_or_404(Funding_Request, id=id)
    serializer = FundingRequestSerializer(funding_request)
    return Response(serializer.data, status=status.HTTP_200_OK)