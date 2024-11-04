# import json
# from .models import *
# from channels.generic.websocket import AsyncWebsocketConsumer
# from channels.db import database_sync_to_async
# from django.core.files.storage import default_storage
# from django.core.files.base import ContentFile
# import base64

# class ChatConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
#         self.room_group_name = "chat_%s" % self.room_name

#         # Join room group
#         await self.channel_layer.group_add(self.room_group_name, self.channel_name)

#         await self.accept()
#         # for message in messages:
#         #     await self.send(text_data=json.dupms(messages))

#     async def disconnect(self, close_code):
#         # Leave room group
#         await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

#     # Receive message from WebSocket
#     async def receive(self, text_data):
#         text_data_json = json.loads(text_data)
#         # message = text_data_json["message"]
#         if text_data.startswith('image:'):
#            image_data = text_data[:6]
#            image_bytes = base64.b64decode(image_data)
#            filename = 'received_image.png'
#            path = default_storage.save(filename, ContentFile(image_bytes))
#            await self.send(text_data=f"image received and save")
#         # Send message to room group
#         # await self.channel_layer.group_send(
#         #     self.room_group_name, {"type": "chat_message", "message": message}
#         # )

#     # Receive message from room group
#     # async def chat_message(self, event):
#     #     # message = event["message"]

#     #     # Send message to WebSocket
#     #     await self.create_message(message)
#     #     await self.send(text_data=json.dumps({"message": message}))

#     @database_sync_to_async
#     def create_message(self, message):
#         ms = MessageChat.objects.create(message=message)

#     # @database_sync_to_async
#     # def get_msgs_chat(self):
#     #     messages = MessageChat.objects.all()
#     #     serializer = MessageChatSerializer(messages, many=True)
#     #     return serializer.data



import json
from .models import *
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = "chat_%s" % self.room_name

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name, {"type": "chat_message", "message": message}
        )

    # Receive message from room group
    async def chat_message(self, event):
        message = event["message"]

        # Send message to WebSocket
        await self.create_message(message)
        await self.send(text_data=json.dumps({"message": message}))

    @database_sync_to_async
    def create_message(self, message):
        ms = MessageChat.objects.create(message=message)