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

@api_view(["POST","GET"])
@permission_classes([])  # public lookup
def find_charity(request):
    """
    Find a charity either from Lucia DB or by scraping IRS / Guidestar.
    """
    if request.method == "GET":
        # Temporary test data
        data = {
            "name": "Red Cross",
            "tin": "123456789",
            "status": "active"
        }
        return Response(data)
    name = request.data.get("name", "").strip()
    tin = request.data.get("tin", "").strip()
    address = request.data.get("address", "").strip()

    # ---- 1️⃣  Check local Lucia DB ------------------------------------------
    charity = None
    if tin:
        charity = Charity.objects.filter(tin__iexact=tin).first()
    if not charity and name:
        charity = Charity.objects.filter(name__icontains=name).first()

    if charity:
        data = CharitySerializer(charity).data
        data.update({"found_in_db": True, "found_via_scrape": False})
        return Response(data, status=status.HTTP_200_OK)

    # ---- 2️⃣  Try IRS.gov Search --------------------------------------------
    if tin:
        try:
            irs_url = f"https://apps.irs.gov/app/eos/details/{tin}"
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(irs_url, headers=headers, timeout=10)

            if r.status_code == 200 and "Employer Identification Number" in r.text:
                soup = BeautifulSoup(r.text, "html.parser")
                name_tag = soup.find("h2")
                addr_tag = soup.find("p", class_="address")

                result = {
                    "found_in_db": False,
                    "found_via_scrape": True,
                    "name": name_tag.text.strip() if name_tag else name,
                    "tin": tin,
                    "address": addr_tag.text.strip() if addr_tag else "",
                    "website": "",
                    "contactName": "",
                    "contactEmail": "",
                    "contactTelephone": "",
                    "source": "ai",
                    "fetched_from_external": True,
                }
                return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            print("IRS scrape failed:", e)

    # ---- 3️⃣  Try Guidestar search ------------------------------------------
    if name:
        try:
            search_url = f"https://www.guidestar.org/search?q={requests.utils.quote(name)}"
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(search_url, headers=headers, timeout=10)

            soup = BeautifulSoup(r.text, "html.parser")
            first_result = soup.select_one(".search-result .org-name")

            if first_result:
                found_name = first_result.get_text(strip=True)
                result = {
                    "found_in_db": False,
                    "found_via_scrape": True,
                    "name": found_name,
                    "tin": tin,
                    "address": "",
                    "website": "",
                    "contactName": "",
                    "contactEmail": "",
                    "contactTelephone": "",
                    "source": "ai",
                    "fetched_from_external": True,
                }
                return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            print("Guidestar scrape failed:", e)

    # ---- 4️⃣  No result ------------------------------------------------------
    return Response(
        {"found_in_db": False, "found_via_scrape": False},
        status=status.HTTP_404_NOT_FOUND,
    )

@api_view(['GET'])
@permission_classes([]) 
def get_charities(request):
    charities = Charity.objects.all().order_by('id')
    paginator = CharityPagination()
    result_page = paginator.paginate_queryset(charities, request)
    serializer = CharitySerializer(result_page, many=True, context={'request': request})
    return paginator.get_paginated_response(serializer.data)
