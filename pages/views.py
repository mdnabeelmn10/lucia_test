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
    
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework import status

@api_view(['POST'])
@parser_classes([FormParser, MultiPartParser])
def validate_login(request):
    """Validate login credentials."""
    allowed_passwords = {"abcde", "12345"}

    print("Request DATA:", request.data)
    print("Request POST:", request.POST)
    print("Request body:", request.body)

    # Elementor often nests form fields
    email = (
        request.data.get("form_fields[email]") or
        request.POST.get("form_fields[email]") or
        request.data.get("email") or
        request.POST.get("email")
    )
    password = (
        request.data.get("form_fields[password]") or
        request.POST.get("form_fields[password]") or
        request.data.get("password") or
        request.POST.get("password")
    )

    if not email or not password:
        return Response({'error': 'Email and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

    if password in allowed_passwords:
        return Response({'valid': 1}, status=status.HTTP_200_OK)
    else:
        return Response({'valid': 0}, status=status.HTTP_200_OK)
