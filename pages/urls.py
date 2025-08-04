from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views # This line now imports from your new views folder

router = DefaultRouter()
router.register(r'dafs', views.DAFViewSet, basename='daf')
router.register(r'donations', views.DonationViewSet, basename='donation')
router.register(r'charities', views.CharityViewSet, basename='charity')

urlpatterns = [
    # --- Authentication Endpoints ---
    path('auth/login/', views.login_view, name='login'),
    path('auth/register/', views.register_user_view, name='register'),

    # --- Donor-Specific Endpoints ---
    path('dashboard/', views.donor_dashboard_view, name='dashboard'),
    path('dashboard/update-goal/', views.update_goal_view, name='update-goal'),

    # --- General API Endpoints ---
    path('api/', include(router.urls)),
]
