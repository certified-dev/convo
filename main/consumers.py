from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer

from .models import User, Conversation, Message
from .serializers import MessageSerializer


class NotificationConsumer(JsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.notification_group_name = None
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

        unread_count = Message.objects.filter(recipient=self.user, read=False).count()
        conversations = Conversation.objects.filter(users__in=[self.user]).order_by("-created_at")
        conversations_unread_counts = [
            {"id": conversation.id, "count": conversation.get_unread_messages_count(self.user)}
            for conversation in conversations
        ]
        self.send_json(
            {
                "type": "unread_count",
                "unread_count": unread_count,
                "conversations_unread_counts": conversations_unread_counts
            }
        )

        self.send_json(
            {
                "type": "unread_count",
                "unread_count": unread_count,
                "conversations_unread_counts": conversations_unread_counts
            }
        )

    def disconnect(self, code):
        async_to_sync(self.channel_layer.group_discard)(
            self.notification_group_name,
            self.channel_name,
        )
        return super().disconnect(code)

    def unread_count(self, event):
        self.send_json(event)

    def new_message_notification(self, event):
        self.send_json(event)


class PersonalChatConsumer(JsonWebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.room_name = None
        self.conversation = None
        self.conversation_name = None
        self.user_conversations = None
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
        self.user_conversations = Conversation.objects.filter(users__in=[self.user]).order_by("-created_at")

        async_to_sync(self.channel_layer.group_add)(
            self.conversation_name,
            self.channel_name
        )

        self.send_json(
            {
                "type": "online_user_list",
                "users": list(self.conversation.online.all().values_list('username', flat=True)),
            }
        )
        async_to_sync(self.channel_layer.group_send)(
            self.conversation_name,
            {
                "type": "user_join",
                "user": self.user.username,
            },
        )

        self.conversation.online.add(self.user)

        self.send_json({
            "type": "welcome_message",
            "message": "Hey there! You've successfully connected!",
        })

        messages = self.conversation.messages.all().order_by("-created_at")[:50]
        message_count = self.conversation.messages.all().count()
        self.send_json({
            "type": "last_50_messages",
            "messages": MessageSerializer(messages, many=True).data,
            "has_more": message_count > 50
        })

    def disconnect(self, close_code):
        if self.user.is_authenticated:
            async_to_sync(self.channel_layer.group_send)(
                self.conversation_name,
                {
                    "type": "user_leave",
                    "user": self.user.username,
                },
            )
            self.conversation.online.remove(self.user)
        return super().disconnect(close_code)

    def receive_json(self, content, **kwargs):
        message_type = content['type']
        if message_type == "chat_message":
            message = self.store_message(content['message'])

            async_to_sync(self.channel_layer.group_send)(
                self.conversation_name,
                {
                    'type': 'chat_message',
                    'message': MessageSerializer(message).data,
                    'conversation_id': self.conversation.id

                })

            notification_group_name = self.user2.username + "__notifications"
            async_to_sync(self.channel_layer.group_send)(
                notification_group_name,
                {
                    "type": "new_message_notification",
                    "name": self.user.username,
                    "id": self.conversation.id
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
            messages_to_me = self.conversation.messages.filter(recipient=self.user)
            messages_to_me.update(read=True, status="seen")

            # Update the unread message count
            unread_count = Message.objects.filter(recipient=self.user, read=False).count()
            conversations_unread_counts = [
                {"id": conversation.id, "count": conversation.get_unread_messages_count(self.user)}
                for conversation in self.user_conversations
            ]
            async_to_sync(self.channel_layer.group_send)(
                self.user.username + "__notifications",
                {
                    "type": "unread_count",
                    "unread_count": unread_count,
                    "conversations_unread_counts": conversations_unread_counts

                },
            )
            async_to_sync(self.channel_layer.group_send)(
                self.conversation_name,
                {
                    'type': 'seen_message',
                    'user': self.user.username
                })

        return super().receive_json(content, **kwargs)

    def user_join(self, event):
        self.send_json(event)

    def user_leave(self, event):
        self.send_json(event)

    def new_message_notification(self, event):
        self.send_json(event)

    def chat_message(self, event):
        self.send_json(event)

    def seen_message(self, event):
        self.send_json(event)

    def typing(self, event):
        self.send_json(event)

    def unread_count(self, event):
        self.send_json(event)

    def store_message(self, message):
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user,
            recipient=self.user2,
            content=message
        )
        return message


class RoomChatConsumer(JsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.room_group_name = None
        self.room_name = None
        self.conversation = None
        self.conversation_name = None
        self.user_conversations = None
        self.user = None

    def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            return

        self.accept()

        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.conversation = Conversation.objects.get_or_create_group_conversation(self.user, self.room_name, "", "", None, None)
        self.conversation_name = self.conversation.name
        self.user_conversations = Conversation.objects.filter(users__in=[self.user]).order_by("-created_at")

        async_to_sync(self.channel_layer.group_add)(
            self.conversation_name,
            self.channel_name
        )

        self.send_json(
            {
                "type": "online_user_list",
                "users": list(self.conversation.online.all().values_list('username', flat=True)),
            }
        )
        async_to_sync(self.channel_layer.group_send)(
            self.conversation_name,
            {
                "type": "user_join",
                "user": self.user.username,
            },
        )

        self.conversation.online.add(self.user)

        self.send_json({
            "type": "welcome_message",
            "message": "Hey there! You've successfully connected!",
        })

        messages = self.conversation.messages.all().order_by("-created_at")[:50]
        message_count = self.conversation.messages.all().count()
        self.send_json({
            "type": "last_50_messages",
            "messages": MessageSerializer(messages, many=True).data,
            "has_more": message_count > 50
        })

    def disconnect(self, close_code):
        if self.user.is_authenticated:
            async_to_sync(self.channel_layer.group_send)(
                self.conversation_name,
                {
                    "type": "user_leave",
                    "user": self.user.username,
                },
            )
            self.conversation.online.remove(self.user)
        return super().disconnect(close_code)

    def receive_json(self, content, **kwargs):
        message_type = content['type']
        if message_type == "chat_message":
            message = self.store_message(content['message'])

            async_to_sync(self.channel_layer.group_send)(
                self.conversation_name,
                {
                    'type': 'chat_message',
                    'message': MessageSerializer(message).data,
                    'conversation_id': self.conversation.id

                })

            for user in self.conversation.users.all():
                notification_group_name = user.username + "__notifications"
                async_to_sync(self.channel_layer.group_send)(
                    notification_group_name,
                    {
                        "type": "new_message_notification",
                        "name": self.user.username,
                        "id": self.conversation.id
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
            messages_to_me = self.conversation.messages.filter(recipient=self.user)
            messages_to_me.update(read=True, status="seen")

            # Update the unread message count
            unread_count = Message.objects.filter(recipient=self.user, read=False).count()
            conversations_unread_counts = [
                {"id": conversation.id, "count": conversation.get_unread_messages_count(self.user)}
                for conversation in self.user_conversations
            ]
            async_to_sync(self.channel_layer.group_send)(
                self.user.username + "__notifications",
                {
                    "type": "unread_count",
                    "unread_count": unread_count,
                    "conversations_unread_counts": conversations_unread_counts

                },
            )
            async_to_sync(self.channel_layer.group_send)(
                self.conversation_name,
                {
                    'type': 'seen_message',
                    'user': self.user.username
                })

        return super().receive_json(content, **kwargs)

    def user_join(self, event):
        self.send_json(event)

    def user_leave(self, event):
        self.send_json(event)

    def new_message_notification(self, event):
        self.send_json(event)

    def chat_message(self, event):
        self.send_json(event)

    def seen_message(self, event):
        self.send_json(event)

    def typing(self, event):
        self.send_json(event)

    def unread_count(self, event):
        self.send_json(event)

    def store_message(self, message):
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user,
            content=message
        )
        return message
