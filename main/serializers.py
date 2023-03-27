from rest_framework import serializers
from django.contrib.humanize.templatetags.humanize import naturalday

from .models import User, Conversation, Message


class CreateUserSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(max_length=30, write_only=True)
    last_name = serializers.CharField(max_length=30, write_only=True)
    email = serializers.EmailField(max_length=50,write_only=True)
    password = serializers.CharField(max_length=15, write_only=True)
    display_photo = serializers.ImageField(write_only=True)

    class Meta:
        model = User
        fields = ('first_name','last_name','username','email','password','display_photo')

    def create(self, validated_data):

        user = User(username=validated_data['username'],
                    email=validated_data['email'],
                    first_name=validated_data['first_name'],
                    last_name=validated_data['last_name'],
                    display_photo=validated_data['display_photo']
                    )

        user.set_password(validated_data['password'])
        user.save()
        return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('first_name','last_name','username','email','display_photo')


class MessageSerializer(serializers.ModelSerializer):
    # conversation = serializers.PrimaryKeyRelatedField(read_only=True)
    sender = serializers.StringRelatedField()

    class Meta:
        model = Message
        # fields = ('sender','text','created_at','updated_at','conversation')
        fields = ('id','sender','text','created_at','updated_at')


class ConservationSerializer(serializers.ModelSerializer):
    peer = serializers.SerializerMethodField('get_peer')
    # users = serializers.StringRelatedField()

    class Meta:
        model = Conversation
        fields = ('id','name','type','peer','created_at','updated_at')
        # fields = ('name','type','users','created_at','updated_at')


    def get_peer(self, conversation):
        request = self.context['request']
        other_user = conversation.users.exclude(username=request.user.username)
        return other_user.first().username


# class ConservationMessagesSerializer(serializers.ModelSerializer):
#     messages = MessageSerializer(read_only=True, many=True)
#
#     class Meta:
#         model = Conversation
#         fields = ('id','name','type','messages','created_at','updated_at')
