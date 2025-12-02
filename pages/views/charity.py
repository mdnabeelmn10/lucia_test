from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework import status
from django.shortcuts import get_object_or_404
import json, re, requests
from bs4 import BeautifulSoup
from ..models import Charity
from ..serializers import CharitySerializer

from ..models import Charity, Funding_Request, FundingRequestStatus
from ..serializers import CharitySerializer, FundingRequestSerializer
from ..permissions import IsLuciaAdmin
from .pagination import CharityPagination

class CharityPagination(PageNumberPagination):
    page_size = 50

@api_view(['POST','GET'])
@permission_classes([])
def create_charity(request):
    if request.method == 'POST':
        print(request.data)
        serializer = CharitySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    else:
        # charity = Charity.objects.get(many = True)
        # serialized_charity = CharitySerializer(charity, many=True).data
        # return Response(serialized_charity, status=status.HTTP_200_OK)
        charity = Charity.objects.all()
        paginator = CharityPagination()
        page = paginator.paginate_queryset(charity, request)
        serializer = CharitySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

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

@api_view(["POST"])
@permission_classes([])  # public lookup
def find_charity(request):
    name = request.data.get("name", "").strip()
    tin = request.data.get("tin", "").strip()
    address = request.data.get("address", "").strip()

    # ---- 1️⃣  Check local Lucia DB ------------------------------------------
    
    exists = Charity.objects.filter(tin__iexact=tin).exists()
    # if not charity and name:
    #     charity = Charity.objects.filter(name__iexact=name).first()
    print(exists)
    return Response({"exists": exists}, status=200)
    # if charity:
    #     data = CharitySerializer(charity).data
    #     return Response(data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([]) 
def get_charities(request):
    charities = Charity.objects.all().order_by('id')
    paginator = CharityPagination()
    result_page = paginator.paginate_queryset(charities, request)
    serializer = CharitySerializer(result_page, many=True, context={'request': request})
    return paginator.get_paginated_response(serializer.data)
