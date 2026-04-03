import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Инициализируем Django до импорта роутов
django_asgi_app = get_asgi_application()

from chat.middleware import JwtAuthMiddleware
from chat.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    # Стандартные HTTP запросы (наш REST API)
    "http": django_asgi_app,
    
    # WebSocket запросы (Чат)
    "websocket": JwtAuthMiddleware(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})