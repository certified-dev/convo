from django.urls import re_path
from .consumers import RoomChatConsumer, PersonalChatConsumer, NotificationConsumer

websocket_urlpatterns = [
    re_path(r'ws/notifications/', NotificationConsumer.as_asgi()),
    re_path(r'ws/chat/(?P<username>\w+)/$', PersonalChatConsumer.as_asgi()),
    re_path(r'ws/chat/room/(?P<room_name>\w+)/$', RoomChatConsumer.as_asgi()),
]