# account/urls.py
from django.urls import path

from .views import delete_account, edit_info, get_info, login, register

urlpatterns = [
    path('login', login, name='login'),
    path('register', register, name='register'),
    path('get_info', get_info, name="get_info"),
    path('edit_info', edit_info, name='edit_info'),
    path('delete_account', delete_account ,name='delete_account')
]
