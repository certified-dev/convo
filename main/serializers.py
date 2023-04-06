from rest_framework import serializers
from django.contrib.humanize.templatetags.humanize import naturalday

from .models import User, Conversation, Message


class CreateUserSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(max_length=30, write_only=True)
    last_name = serializers.CharField(max_length=30, write_only=True)
    email = serializers.EmailField(max_length=50, write_only=True)
    password = serializers.CharField(max_length=15, write_only=True)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', 'password')

    def create(self, validated_data):
        user = User(username=validated_data['username'],
                    email=validated_data['email'],
                    first_name=validated_data['first_name'],
                    last_name=validated_data['last_name']
                    )

        user.set_password(validated_data['password'])
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', 'display_photo')


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer()
    recipient = UserSerializer()

    class Meta:
        model = Message
        fields = ('id', 'sender', 'recipient', 'content', 'created_at', 'state', 'read')


class ConservationSerializer(serializers.ModelSerializer):
    other_user = serializers.SerializerMethodField('get_other_user')
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ('id', 'name', 'type', 'other_user', 'last_message', 'created_at', 'updated_at')

    def get_last_message(self, conversation):
        message = conversation.messages.last()
        if not message:
            return None
        return MessageSerializer(message).data

    def get_other_user(self, conversation):
        request = self.context['request']
        other_user = conversation.users.exclude(username=request.user.username)
        return UserSerializer(other_user.first()).data
