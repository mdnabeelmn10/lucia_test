from django.urls import path
from pages import views

urlpatterns = [
    # Donor-facing endpoints
    path('register/', views.register_user, name='register_user'),
    path('login/', views.login_view, name='login_user'),
    path('dashboard/<int:user_id>/', views.public_donor_dashboard, name='public_donor_dashboard'),

    # path('logout/', views.logout_user, name='logout_user'),
    path('recommendation/create/', views.create_recommendation, name='create_recommendation'),
    path('donation/direct/', views.direct_donation, name='direct_donation'),

    # Admin-only endpoints
    path('admin/recommendation/<int:id>/update/', views.update_recommendation_status, name='update_recommendation_status'),
    path('admin/donation/<int:id>/update/', views.update_donation_status, name='update_donation_status'),
    path('admin/receipt/upload/', views.upload_receipt, name='upload_receipt'),

    # Password Reset (optional)
    # path('password_reset/', views.password_reset_request, name='password_reset'),

    # Optional endpoints for listing donations and recommendations
    # path('donations/', views.list_user_donations, name='list_user_donations'),
    # path('recommendations/', views.list_user_recommendations, name='list_user_recommendations'),
    # path('admin/donations/', views.admin_list_donations, name='admin_list_donations'),
    # path('admin/recommendations/', views.admin_list_recommendations, name='admin_list_recommendations'),
]
