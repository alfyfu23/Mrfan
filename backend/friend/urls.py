# chat/urls.py
from django.urls import path
from .views import befriend, search, agree, list_friends, disagree, delete_friend, check_friendship
from .views import create_friend_group, list_groups, add_to_group, remove_from_group, rename_group, delete_group

urlpatterns = [
    path('add/<int:id>', befriend, name='befriend'),
    path('search/<str:username>', search, name="search"),
    path('agree/<int:id>', agree, name='agree'),
    path('list', list_friends, name='list_friends'),
    path('disagree/<int:id>', disagree, name='disagree'),
    path('delete/<int:id>', delete_friend, name='delete_friend'),
    path('check/<int:id>', check_friendship, name='check_friendship'),
    # friend group management
    path('group/create', create_friend_group, name='create_friend_group'),
    path('group/list', list_groups, name='list_groups'),
    path('group/add', add_to_group, name='add_to_group'),
    path('group/remove', remove_from_group, name='remove_from_group'),
    path('group/rename', rename_group, name='rename_group'),
    path('group/delete', delete_group, name='delete_group'),
]