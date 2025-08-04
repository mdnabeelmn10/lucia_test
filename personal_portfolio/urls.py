"""
URL configuration for personal_portfolio project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # This single line correctly includes all your app's URLs at the root.
    # All other `include('pages.urls')` lines should be deleted.
    path('', include('pages.urls')),
]