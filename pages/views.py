from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Item
from .serializers import ItemSerializer
@api_view(['GET'])
def hello_world(request):
    return Response({"message": "Hello, Shiney"})
@api_view(['GET'])    
def home(request):
    return Response("Welcome to the Home Page!")


@api_view(['POST'])
def create_item(request):
    serializer = ItemSerializer(data=request.data)
    if serializer.is_valid():
        #serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
@api_view(['POST'])
def validate_login(request):
    """Validate login credentials from Elementor form."""
    allowed_passwords = {"abcde", "12345"}

    print("Raw DATA: ", request.data)

    # Try getting from structured 'form_fields[field]' first
    email = request.data.get('form_fields[email]')
    password = request.data.get('form_fields[password]')

    # Fallbacks for direct fields
    if not email:
        email = request.data.get('email') or request.POST.get('email') or request.data.get('Email') or request.POST.get('Email')
    if not password:
        password = request.data.get('password') or request.POST.get('password') or request.data.get('Password') or request.POST.get('Password')

    # Check if email and password exist
    if not email or not password:
        return Response({
            "success": False,
            "data": {
                "message": "Email and password are required.",
                "errors": [],
                "data": []
            }
        }, status=status.HTTP_400_BAD_REQUEST)

    if password in allowed_passwords:
        return Response({
            'success': True,
            'message': 'Login successful',
            'login_status': 'valid'
        })
    else:
        return Response({
            'success': False,
            'message': 'Invalid login',
            'login_status': 'invalid'
        })
