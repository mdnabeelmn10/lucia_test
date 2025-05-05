from rest_framework.permissions import BasePermission

class IsAdminUser(BasePermission):
    """
    Custom permission to only allow admins to access the view.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_staff

class IsDonorUser(BasePermission):
    """
    Custom permission to only allow donors to access the view.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and not request.user.is_staff
