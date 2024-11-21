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
from django.core.files.base import ContentFile
import base64

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
        conversation_id = text_data_json["conversation_id"]
        content = text_data_json["content"]
        # media_url = text_data_json["media_url"]
        content_type = text_data_json["content_type"]

        image_data = text_data_json['image']

        # decode base64 string to bytes
        decoded_image = base64.b64decode(image_data)

        # Create ContentFile object with the decoded image data

        with open('test_chat.txt', 'a') as test:
            test.write(f'''{conversation_id}---{content}---{content_type}''')
        # await self.get_conversation_id(conversation_id)

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name, {
                "type": "chat_message", 
                "conversation_id": conversation_id,
                "content": content,
                # "media_url": media_url,
                "content_type": content_type,
                "decoded_image":decoded_image
                }
        )

    # Receive message from room group
    async def chat_message(self, event):
        conversation_id = event["conversation_id"]
        content = event["content"]
        # media_url = event["media_url"]
        content_type = event["content_type"]
        decoded_image = event["decoded_image"]
        dat = "hello"
        image_file = ContentFile(decoded_image, name='received_image.jpg')
        await database_sync_to_async(UploadImage.objects.create)(image_file=image_file)

        await self.send(text_data=json.dumps({
                "conversation_id": conversation_id,
                "content": content,
                # "media_url": media_url,
                "content_type": content_type,
            }))

    # @database_sync_to_async
    # def create_message(self, message):
    #     ms = MessageChat.objects.create(message=message)

    # @database_sync_to_async
    # def get_conversation_id(self, conversation_id):
    #     conversation_id = Conversation.objects.get(conversation_id=conversation_id)
    #     return conversation_id.conversation_id
    