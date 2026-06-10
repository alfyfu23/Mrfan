# account/urls.py
from django.urls import path
from .views import login, register, get_info, edit_info, delete_account

urlpatterns = [
    path('login', login, name='login'),
    path('register', register, name='register'),
    path('get_info', get_info, name="get_info"),
    path('edit_info', edit_info, name='edit_info'),
    path('delete_account', delete_account ,name='delete_account')
]