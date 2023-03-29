import json

from asgiref.sync import async_to_sync, sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer, JsonWebsocketConsumer
from .models import User, Conversation, Message
from .serializers import MessageSerializer


class NotificationConsumer(JsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.user = None

    def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            return

        self.accept()

        self.notification_group_name = self.user.username + "__notifications"
        async_to_sync(self.channel_layer.group_add)(
            self.notification_group_name,
            self.channel_name,
        )

        unread_count = Message.objects.filter(to_user=self.user, read=False).count()
        self.send_json(
            {
                "type": "unread_count",
                "unread_count": unread_count,
            }
        )

    def disconnect(self, code):
        async_to_sync(self.channel_layer.group_discard)(
            self.notification_group_name,
            self.channel_name,
        )
        return super().disconnect(code)

    def new_message_notification(self, event):
        self.send_json(event)



class PersonalChatConsumer(JsonWebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.room_name = None
        self.conversation_name = None
        self.user = None
        self.user2 = None


    def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            return

        user2_username = self.scope['url_route']['kwargs']['username']
        self.user2 = User.objects.get(username=user2_username)
        self.accept()

        self.conversation = Conversation.objects.get_or_create_personal_conversation(self.user, self.user2)
        self.conversation_name = self.conversation.name
        async_to_sync(self.channel_layer.group_add)(
            self.conversation_name,
            self.channel_name
        )

        self.send_json({
            "type": "welcome_message",
            "message": "Hey there! You've successfully connected!",
        })

        messages = self.conversation.messages.all().order_by("-created_at")[0:50]
        message_count = self.conversation.messages.all().count()
        self.send_json({
            "type": "last_50_messages",
            "messages": MessageSerializer(messages, many=True).data,
            "has_more": message_count > 50
        })

    def disconnect(self, close_code):
        return super().disconnect(close_code)

    def receive_json(self, content,  **kwargs):
        message_type = content['type']
        if message_type == "chat_message":
            message = self.store_message(content['message'])

            async_to_sync(self.channel_layer.group_send)(
                self.conversation_name,
                {
                    'type': 'chat_message',
                    'message': MessageSerializer(message).data
                })

            notification_group_name = self.user2.username + "__notifications"
            async_to_sync(self.channel_layer.group_send)(
                notification_group_name,
                {
                    "type": "new_message_notification",
                    "name": self.user.username,
                    "message": MessageSerializer(message).data,
                },
            )

        if message_type == "typing":
            async_to_sync(self.channel_layer.group_send)(
                self.conversation_name,
                {
                    "type": "typing",
                    "user": self.user.username,
                    "typing": content["typing"],
                },
            )

        if message_type == "read_messages":
            messages_to_me = self.conversation.messages.filter(reciepient=self.user)
            messages_to_me.update(read=True)

            # Update the unread message count
            unread_count = Message.objects.filter(reciepient=self.user, read=False).count()
            async_to_sync(self.channel_layer.group_send)(
                self.user.username + "__notifications",
                {
                    "type": "unread_count",
                    "unread_count": unread_count,
                },
            )

        return super().receive_json(content, **kwargs)

    def new_message_notification(self, event):
        self.send_json(event)

    def chat_message(self, event):
        self.send_json(event)

    def typing(self, event):
        self.send_json(event)

    def store_message(self, message):
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user,
            reciepient=self.user2,
            content=message
        )

        return message


class RoomChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = 'chat_%s' % self.room_name

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        print('connected')

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        print('disconnected')

    # Receive message from WebSocket
    async def receive(self, text_data):
        print('recieved message from %s' % json.loads(text_data)['posted_by'])
        text_data_json = json.loads(text_data)
        posted_by, message = text_data_json['posted_by'], text_data_json['message']

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'posted_by': posted_by,
                'message': message
            })

    # Receive message from room group
    async def chat_message(self, event):
        posted_by, message = event['posted_by'], event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'posted_by': posted_by
        }))
        print('msg sent to %s' % self.channel_name)
