from django.urls import re_path

from .consumers import ChatConsumer

# Frontend will pass conversation id as query param (e.g. /ws/chat?token=xxx&c=123)
websocket_urlpatterns = [
    re_path(r'ws/chat/?$', ChatConsumer.as_asgi()),
]

