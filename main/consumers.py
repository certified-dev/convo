import json

from asgiref.sync import async_to_sync, sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer, AsyncJsonWebsocketConsumer
from .models import User, Conversation, Message


class PersonalChatConsumer(AsyncJsonWebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.room_name = None
        self.conversation_name = None
        self.user = None

    async def connect(self):
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            return

        user2_username = self.scope['url_route']['kwargs']['username']
        # user2 = await sync_to_async(User.objects.get)(username=user2_username)

        await self.accept()
        
        # self.conversation = await sync_to_async(Conversation.objects.get_or_create_personal_conversation)(user1, user2)
        # self.conversation_name = conversation.name
        # await self.channel_layer.group_add(
        #     self.converstion_name,
        #     self.channel_name
        # )


        # self.room_name = 'personal_conversation_%s' % self.conversation.id
        # await self.channel_layer.group_add(
        #     self.converstion_name,
        #     self.channel_name
        # )


        await self.send_json({
                "type": "welcome_message",
                "message": "Hey there! You've successfully connected!",
            })


    async def disconnect(self, close_code):
        print('disconnected')
        # await self.channel_layer.group_discard(
        #     self.conversdation_name,
        #     self.channel_name
        # )

    async def receive_json(self, content):
        print(content)

        # await self.store_message(content['message'])

        # await self.channel_layer.group_send(
        #     self.conversation_name,
        #     {
        #         'type': 'chat_message',
        #         'posted_by': content['posted_by'],
        #         'message': message['posted_by']
        #     })

    async def chat_message(self, event):
        await self.send(event)

    @database_sync_to_async
    def store_message(self, message):
        Message.objects.create(
            conversation=self.conversation,
            sender=self.scope['user'],
            text=message
        )


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

