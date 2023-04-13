from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import permission_classes
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from .models import Conversation, User, Message
from .pagination import MessagePagination
from .serializers import ConservationSerializer, CreateUserSerializer, UserSerializer, MessageSerializer


class CustomObtainAuthTokenView(ObtainAuthToken):

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, created = Token.objects.get_or_create(user=user)
        last = Conversation.objects.filter(id=user.last_conversation).first()
        serializer = ConservationSerializer(last, context={'user': user})
        return Response({
            "username": user.username,
            "token": token.key,
            "last_conversation": serializer.data or None
        })


class UserView(APIView):
    """
    create new user.
    """

    @permission_classes([IsAuthenticated, ])
    def get(self, request, obj_id=id):
        user = User.objects.get(id=obj_id)
        if not user:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = CreateUserSerializer(data=request.data)

        if serializer.is_valid():
            account = serializer.save()
            token = Token.objects.get(user=account).key
            response_data = {'token': token}
            response_data.update(serializer.data)

            return Response(response_data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UsersView(APIView):
    """
    create new user.
    """

    @permission_classes([IsAuthenticated, ])
    def get(self, request):
        serializer = UserSerializer(User.objects.exclude(username=request.user.username), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ConversationView(APIView):
    permission_classes = [IsAuthenticated, ]

    """
    get conversations
    """

    def get(self, request):
        conversation = Conversation.objects.filter(users__in=[request.user]).order_by("-created_at")
        serializer = ConservationSerializer(conversation, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        try:
            other_user = User.objects.filter(username=request.data['username'])
            conversation = Conversation.objects.get_or_create_personal_conversation(request.user, other_user)
        except KeyError:
            room_name = request.data['room_name']
            group_type = request.data['group_type']
            conversation = Conversation.objects.get_or_create_group_conversation(request.user, room_name, group_type)
        finally:
            serializer = ConservationSerializer(conversation, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)


class MessagesView(APIView):
    permission_classes = [IsAuthenticated, ]
    pagination_class = MessagePagination

    """
    get conversation messages
    """

    def get(self, request, username):
        user2 = User.objects.get(username=username)
        conversation = Conversation.objects.get_or_create_personal_conversation(request.user, user2)
        serializer = MessageSerializer(conversation.messages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MessageViewSet(ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, ]
    serializer_class = MessageSerializer
    queryset = Message.objects.none()
    pagination_class = MessagePagination

    def get_queryset(self):
        conversation_name = self.request.GET.get("conversation")
        queryset = (
            Message.objects.filter(
                conversation__name__contains=self.request.user.username,
            )
            .filter(conversation__name=conversation_name)
            .order_by("-created_at")
        )
        return queryset


class UserLogoutView(APIView):
    permission_classes = [IsAuthenticated, ]

    def post(self, request):
        request.user.last_conversation = request.data['id']
        request.user.save()
        return Response(status=status.HTTP_200_OK)
