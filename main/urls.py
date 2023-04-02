from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import UserView, ConversationView, MessagesView, MessageViewSet

# router.register("messages", MessageViewSet)

urlpatterns = [
    path('user/add', UserView.as_view(), name='user_add'),
    path('user/<str:id>', UserView.as_view(), name='user_view'),
    path('chats', ConversationView.as_view(), name='conversation_view'),
    path('chat/<str:username>/messages', MessagesView.as_view(), name='messages_view'),
    path('messages', MessageViewSet.as_view({'get': 'list'}))

]


