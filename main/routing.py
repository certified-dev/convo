from django.urls import path
from .consumers import RoomChatConsumer, PersonalChatConsumer, NotificationConsumer

websocket_urlpatterns = [
    path('ws/notifications/', NotificationConsumer.as_asgi()),
    path('ws/chat/<str:username>/', PersonalChatConsumer.as_asgi()),
    path('ws/chat/room/<str:room_name>/', RoomChatConsumer.as_asgi()),
]
