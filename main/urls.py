from django.urls import path

from .views import UserView, ConversationView, MessagesView, MessageViewSet, UsersView

urlpatterns = [
    path('user/add', UserView.as_view(), name='user_add'),
    path('user/<str:obj_id>', UserView.as_view(), name='user_view'),
    path('users/all', UsersView.as_view(), name='users_view'),
    path('chats', ConversationView.as_view(), name='conversation_view'),
    path('chats/add', ConversationView.as_view(), name='conversation_add_view'),
    path('chat/<str:username>/messages', MessagesView.as_view(), name='messages_view'),
    path('messages', MessageViewSet.as_view({'get': 'list'}))
]


