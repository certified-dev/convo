from django.urls import path

from .views import UserView, ConversationView, MessagesView, MessageViewSet, FriendsView, UserLogoutView

urlpatterns = [
    path('user/add', UserView.as_view(), name='user_add'),
    path('user/<int:obj_id>', UserView.as_view(), name='user_view'),
    path('friends', FriendsView.as_view(), name='friends_view'),
    path('chats', ConversationView.as_view(), name='conversation_view'),
    path('chats/add', ConversationView.as_view(), name='conversation_add_view'),
    path('chat/<str:username>/messages', MessagesView.as_view(), name='messages_view'),
    path('messages', MessageViewSet.as_view({'get': 'list'})),
    path('user/logout', UserLogoutView.as_view(), name='user_logout'),
]

