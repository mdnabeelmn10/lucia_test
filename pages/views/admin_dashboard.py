from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model

from ..models import DAF, Charity, Donation, Funding_Request
from ..serializers import (
    UserSerializer,
    DAFSerializer,
    CharitySerializer,
    DonationReadSerializer,
    FundingRequestSerializer
)
from ..permissions import IsLuciaAdmin

User = get_user_model()


@api_view(['GET'])
@permission_classes([IsLuciaAdmin])
def admin_dashboard(request):
    
    users_count = User.objects.count()
    dafs_count = DAF.objects.count()
    charities_count = Charity.objects.count()
    donations_count = Donation.objects.count()
    funding_requests_count = Funding_Request.objects.count()

    data = {
        "summary": {
            "total_users": users_count,
            "total_dafs": dafs_count,
            "total_charities": charities_count,
            "total_donations": donations_count,
            "total_funding_requests": funding_requests_count,
        },
        "endpoints": {
            "users": "/users/",
            "dafs": "/dafs/",
            "charities": "/charities/",
            "donations": "/donations/",
            "funding_requests": "/funding_requests/all/"
        }
    }
    return Response(data, status=status.HTTP_200_OK)
