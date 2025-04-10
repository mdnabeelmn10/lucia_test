from django.urls import path
from pages import views
from .views import home,create_item,validate_login
urlpatterns = [
    path('', home, name='home'),  # Root URL
    path('items/create/', create_item, name='create_item'),
    path('login/validate/', validate_login, name='validate_login'),
    path('home/',home,name='home'),
]
