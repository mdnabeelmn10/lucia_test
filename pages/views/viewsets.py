# In your pages/views/viewsets.py file

from rest_framework import viewsets, permissions, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from ..models import DAF, Donation, Vote, Charity, UserRole, DonationStatus, VoteType
from ..serializers import (
    DAFSerializer, DonationReadSerializer, DonationWriteSerializer,
    VoteSerializer, CharitySerializer
)
from ..permissions import IsLuciaAdmin, IsLuciaDirector, IsOwnerOfObject



class DAFViewSet(viewsets.ModelViewSet):
    """
    Handles all operations for DAFs (Charity Accounts).
    This ViewSet is now secured with object-level permissions.
    """
    serializer_class = DAFSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """ This method ensures users only see a LIST of DAFs they are allowed to see. """
        user = self.request.user
        if user.role == UserRole.LUCIA_ADMIN:
            return DAF.objects.all()
        return DAF.objects.filter(advisors=user)

    def get_permissions(self):
        """ This method adds extra security for viewing or editing a SINGLE DAF. """
        if self.action in ['update', 'partial_update', 'retrieve']:
            # For actions on a single DAF, check if the user is an owner.
            self.permission_classes = [permissions.IsAuthenticated, IsOwnerOfObject]
        elif self.action in ['create', 'destroy']:
            # Only Admins should be able to create or delete DAFs.
            self.permission_classes = [IsLuciaAdmin]
        else:
            # For the 'list' action, just being authenticated is enough.
            self.permission_classes = [permissions.IsAuthenticated]
        return super().get_permissions()




class DonationViewSet(viewsets.ModelViewSet):
    """
    Handles all operations for Donations.
    This ViewSet is now secured with object-level permissions and creation checks.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        # Use a different serializer for writing data vs. reading it.
        if self.action in ['create', 'update', 'partial_update']:
            return DonationWriteSerializer
        return DonationReadSerializer

    def get_queryset(self):
        """ This method filters the LIST of donations based on the user's role. """
        user = self.request.user
        if user.role == UserRole.LUCIA_ADMIN:
            return Donation.objects.all()
        if user.role == UserRole.LUCIA_DIRECTOR:
            # Directors see all pending donations to vote on them.
            return Donation.objects.filter(status=DonationStatus.PENDING_REVIEW)
        # Donors only see donations they recommended.
        return Donation.objects.filter(recommending_user=user)

    def get_permissions(self):
        """ This method adds extra security for viewing a SINGLE donation. """
        if self.action == 'retrieve':
            # To view a single donation, you must be the one who created it.
            self.permission_classes = [permissions.IsAuthenticated, IsOwnerOfObject]
        elif self.action in ['update', 'partial_update', 'destroy']:
            # For now, only Admins can modify or delete a donation record after it's made.
            self.permission_classes = [IsLuciaAdmin]
        else:
            # For list and create, basic authentication is sufficient.
            self.permission_classes = [permissions.IsAuthenticated]
        return super().get_permissions()

    def perform_create(self, serializer):
        """
        Custom logic to create a donation, with a crucial security check.
        The charity lookup is now handled automatically by the serializer.
        """
        # SECURITY CHECK: Is the logged-in user an advisor for the DAF?
        source_daf = serializer.validated_data['source_daf']
        user = self.request.user
        if not DAF.objects.filter(id=source_daf.id, advisors=user).exists():
            raise serializers.ValidationError(
                {"source_daf": "You are not an authorized advisor for this DAF account."}
            )
        serializer.save(recommending_user=self.request.user)
    


    @action(detail=True, methods=['post'], permission_classes=[IsLuciaDirector])
    def vote(self, request, pk=None):
        """ Custom action for a Director to vote. POST to /api/donations/{id}/vote/ """
        donation = self.get_object()
        serializer = VoteSerializer(data=request.data)
        if serializer.is_valid():
            Vote.objects.update_or_create(
                donation=donation,
                director=request.user,
                defaults={'vote': serializer.validated_data['vote']}
            )
            return Response({'status': 'vote recorded'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class CharityViewSet(viewsets.ModelViewSet):
    """ API endpoint for charities. """
    queryset = Charity.objects.all()
    serializer_class = CharitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        # Any authenticated user can view the list of charities.
        # However, only admins can create, edit, or delete them from the master list.
        if self.action not in ['list', 'retrieve']:
            return [IsLuciaAdmin()]
        return [permissions.IsAuthenticated()]
