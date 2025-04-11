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
    """Validate login credentials."""
    allowed_passwords = {"abcde", "12345"}
    
    email = request.data.get('email') or request.POST.get('email')
    password = request.data.get('password') or request.POST.get('password')

    if not email or not password:
        return Response({'error': 'Email and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

    if password in allowed_passwords:
        return Response({'valid': 1}, status=status.HTTP_200_OK)
    else:
        return Response({'valid': 0}, status=status.HTTP_200_OK)
