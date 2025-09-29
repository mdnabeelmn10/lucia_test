from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views 
# from .views.donation_details import get_donation_by_id
# from .views.donation_details import DonationDetailView


router = DefaultRouter()
router.register(r'dafs', views.DAFViewSet, basename='daf')
router.register(r'donations', views.DonationViewSet, basename='donation')
router.register(r'charities', views.CharityViewSet, basename='charity')

urlpatterns = [
    # --- Authentication Endpoints ---
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('auth/register/', views.register_user_view, name='register'),

    # --- Donor-Specific Endpoints ---
    path('dashboard/', views.donor_dashboard_view, name='dashboard'),
    path('dashboard/update-goal/', views.update_goal_view, name='update-goal'),
    path('donations/<uuid:donation_id>/', views.get_donation_by_id, name='get_donation_by_id'),
    path("director-dashboard/", views.director_dashboard_view, name="director-dashboard"),
    path('donations/<uuid:donation_id>/documents/', views.upload_donation_document, name='upload-donation-document'),

    # path('donations/<uuid:pk>/', DonationDetailView.as_view(), name='donation-detail'),
    path('donations/', views.create_donation, name='create_donation'),
    path('donations/<uuid:id>/status/', views.update_donation_status, name='update_donation_status'),
    path('<uuid:id>/votes/', views.cast_vote, name='cast_vote'),
    path("charities/", views.create_charity, name="create-charity"),
    path("funding-requests/", views.submit_funding_request, name="submit-funding-request"),
    path("funding-requests/all/", views.list_all_funding_requests, name="list-all-funding-requests"),
    path("funding-requests/<uuid:id>/", views.get_funding_request, name="get-funding-request"),

    path('admin-dashboard/', views.admin_dashboard, name='admin-dashboard'),

    # path('chatbot/', views.NLQueryAPIView.as_view(), name='chatbot'),
    path('chatbot/', views.NLQueryPandasAPIView.as_view(), name='chatbot'),
    path("verify-charity/", views.verify_charity, name="verify_charity"),


    # --- General API Endpoints ---
    path('api/', include(router.urls)),
]
