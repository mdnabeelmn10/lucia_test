from django.urls import path
from pages import views
from .views import home,create_item
urlpatterns = [
    path('', home, name='home'),  # Root URL
    path('items/create/', create_item, name='create_item'),
]
