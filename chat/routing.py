from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Подключаемся по адресу ws://domain/ws/chat/<ID_комнаты>/
    re_path(r'ws/chat/(?P<room_id>\w+)/$', consumers.ChatConsumer.as_asgi()),
]