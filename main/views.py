from django.shortcuts import render

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated

from rest_framework.authtoken.models import Token

from .models import Conversation ,User, Message
from .serializers import ConservationSerializer,CreateUserSerializer,UserSerializer, MessageSerializer

from rest_framework.authtoken.views import ObtainAuthToken


class CustomObtainAuthTokenView(ObtainAuthToken):
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, created = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "username": user.username})


class UserView(APIView):
    """
    create new user.
    """

    @permission_classes([IsAuthenticated, ])
    def get(self, request, id=id, format=None):
        user = User.objects.get(id=id)
        if not user:
            return Response(serializer.errors, status=status.HTTP_404_NOT_FOUND)

        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


    def post(self, request, format=None):
        serializer = CreateUserSerializer(data=request.data)

        if serializer.is_valid():
            account = serializer.save()
            token = Token.objects.get(user=account).key
            response_data = {'acess_token': token }
            response_data.update(serializer.data)

            return Response(response_data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class ConversationView(APIView):
    permission_classes = [IsAuthenticated,]

    """
    get conversations
    """
    def get(self, request, format=None):
        conversation = Conversation.objects.filter(users__in=[request.user])
        serializer = ConservationSerializer(conversation, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class MessagesView(APIView):
    permission_classes = [IsAuthenticated,]

    """
    get conversation messages
    """
    def get(self, request, username, format=None):
        user2 = User.objects.get(username=username)
        conversation = Conversation.objects.get_or_create_personal_conversation(request.user, user2)
        serializer = MessageSerializer(conversation.messages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
