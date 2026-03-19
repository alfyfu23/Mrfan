"""
ASGI config for im project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'im.settings')
django.setup()

# Import routing after Django is configured to avoid accessing models/app registry too early
import chat.routing

django_asgi_app = get_asgi_application()

django_asgi_app = get_asgi_application()  # ✅ 确保 Django 已初始化

import chat.routing  # ✅ 放到后面再导入

application = ProtocolTypeRouter({
    "http": django_asgi_app,  # HTTP 支持
    "websocket": AuthMiddlewareStack(
        URLRouter(chat.routing.websocket_urlpatterns)
    ),
})
