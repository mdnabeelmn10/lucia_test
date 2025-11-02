from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from ..models import User, DAF
from ..serializers import LoginSerializer, UserRegisterSerializer

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register_user_view(request):
    """ Handles user registration. """
    serializer = UserRegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        # Create a DAF for the new donor
        DAF.objects.create(name=f"{user.first_name}'s Fund", advisors=[user])
        return Response({"message": "User registered successfully."}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    """ Handles user login and returns JWT tokens. """
    print(request.data)
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data['email'].lower()
    password = serializer.validated_data['password']
    print(password)

    try:
        user = User.objects.get(email=email)
        authenticated_user = authenticate(request, username=user.username, password=password)
    except User.DoesNotExist:
        authenticated_user = None

    if authenticated_user is None:
        return Response({"detail": "Invalid email or password."}, status=status.HTTP_401_UNAUTHORIZED)

    refresh = RefreshToken.for_user(authenticated_user)
    daf = DAF.objects.filter(advisors=authenticated_user).first()

    return Response({
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'user': {
            'id': authenticated_user.id,
            'username': authenticated_user.username,
            'email': authenticated_user.email,
            'role': authenticated_user.role,
            'dafId': daf.id if daf else None,
        }
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    """ Handles user logout by blacklisting the refresh token. """
    try:
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "Refresh token required."}, status=status.HTTP_400_BAD_REQUEST)

        token = RefreshToken(refresh_token)
        token.blacklist()

        return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"detail": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)
