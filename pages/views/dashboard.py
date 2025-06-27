from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Sum
from ..models import UserRole, DAF, Donation, DonationStatus
from ..serializers import DonationReadSerializer

def _get_dashboard_data(user):
    """ Helper function to build the dashboard JSON response. """
    if user.role != UserRole.DONOR_ADVISOR:
        return {"detail": "Only Donor Advisors have a dashboard."}, 403

    primary_daf = DAF.objects.filter(advisors=user).first()
    if not primary_daf:
        return {"detail": "You are not an advisor for any DAF."}, 404

    total_donated = Donation.objects.filter(source_daf=primary_daf, status=DonationStatus.COMPLETED).aggregate(total=Sum('amount'))['total'] or 0
    goal_amount = primary_daf.annual_giving_target or 0
    percentage_donated = round(100 * (float(total_donated) / float(goal_amount)), 2) if goal_amount > 0 else 0
    balance_amount = float(goal_amount) - float(total_donated)
    recent_donations_qs = Donation.objects.filter(source_daf=primary_daf).order_by('-date_recommended')

    return {
        "user": { "id": user.id, "username": user.username },
        "goalAmount": float(goal_amount),
        "currentDonatedAmount": float(total_donated),
        "donations": DonationReadSerializer(recent_donations_qs, many=True).data,
        "percentageDonated": percentage_donated,
        "balanceAmount": balance_amount
    }, 200

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def donor_dashboard_view(request):
    """ View to get the dashboard data. """
    data, http_status = _get_dashboard_data(request.user)
    return Response(data, status=http_status)


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def update_goal_view(request):
    """ View to update the donor's annual giving goal. """
    user = request.user
    primary_daf = DAF.objects.filter(advisors=user).first()
    if not primary_daf:
        return Response({"detail": "DAF not found."}, status=status.HTTP_404_NOT_FOUND)

    new_goal_amount = request.data.get('goalAmount')
    print(type(request.data))
    print(new_goal_amount)
    # print(request.data['goalAmount'])
    if new_goal_amount is None:
        return Response({"detail": "'goalAmount' is required.", "payload": request}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        primary_daf.annual_giving_target = float(new_goal_amount)
        primary_daf.save()
    except (ValueError, TypeError):
        return Response({"detail": "Invalid 'goalAmount' format."}, status=status.HTTP_400_BAD_REQUEST)
    
    data, http_status = _get_dashboard_data(user)
    return Response(data, status=http_status)