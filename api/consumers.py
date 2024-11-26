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
import os
# from pydub import AudioSegment

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
        content_type = text_data_json["content_type"]

        # handel receive voice message
        if content_type == 'voice':
            await database_sync_to_async(UploadImage.objects.create)(image_file=content)
        # Send image to room group
            await self.channel_layer.group_send(
                    self.room_group_name, {
                        "type": "chat_message", 
                        "conversation_id": conversation_id,
                        "content": content,
                        "content_type": content_type,
                    }
                )

            # print(dir_path)
            # with open(dir_path+'\\hussam.mp3', 'r', encoding='utf-8') as voice:
            #     voice.read()
            # print(voice)

        # handel receive image
        if content.startswith('image:'):
            decoded_image = base64.b64decode(content[6:])
            image_file = ContentFile(decoded_image, name='received_image.jpg')
            await database_sync_to_async(UploadImage.objects.create)(image_file=image_file)
        # Send image to room group
            await self.channel_layer.group_send(
                self.room_group_name, {
                    "type": "chat_message", 
                    "conversation_id": conversation_id,
                    "content": content,
                    "content_type": content_type,
                }
            )
        
        # handel receive video
        elif content.startswith('video:'):
            decoded_video = base64.b64decode(content[6:])
            image_file = ContentFile(decoded_video, name='video_received.mp4')
            await database_sync_to_async(UploadImage.objects.create)(image_file=image_file)
        # Send video to room group
            await self.channel_layer.group_send(
                self.room_group_name, {
                    "type": "chat_message", 
                    "conversation_id": conversation_id,
                    "content": content,
                    "content_type": content_type,
                }
            )

        # Send message to room group
        else:
            await self.channel_layer.group_send(
                self.room_group_name, {
                    "type": "chat_message", 
                    "conversation_id": conversation_id,
                    "content": content,
                    "content_type": content_type,
                }
            )
    # Receive message from room group
    async def chat_message(self, event):
        conversation_id = event["conversation_id"]
        content = event["content"]
        content_type = event["content_type"]

        if content_type == 'voice':
            await self.send(text_data=json.dumps({
                    "conversation_id": conversation_id,
                    "content": content,
                    "content_type": content_type,
                }))

        # handel image
        if content.startswith('image:'):
            await self.send(text_data=json.dumps({
                    "conversation_id": conversation_id,
                    "content": content[6:],
                    "content_type": content_type,
                }))
        # handle video
        elif content.startswith('video:'):
            await self.send(text_data=json.dumps({
                    "conversation_id": conversation_id,
                    "content": content[6:],
                    "content_type": content_type,
                }))
        # handel message  
        else:
            await self.send(text_data=json.dumps({
                    "conversation_id": conversation_id,
                    "content": content,
                    "content_type": content_type,
                }))


class DocumentConsumers(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room']
        self.room_group_name = "chat_%s" % self.room_name
        self.document_data = []

        await self.channel_layer.group_add(self.room_group_name, self.channel_layer)

        return self.accept()
    
    async def disconnect(self, code):
        return await super().disconnect(code)
    
    async def receive(self, text_data=None, bytes_data=None):
        text_data_json = json.loads(text_data)
        chunk = text_data_json.get('chunk', '')
        last_chunk = text_data_json.get('last_chunk', '')

        self.document_data.append(chunk)

        if last_chunk != '':
            document_data = ''.join(self.document_data)

    
# def split_base64_into_chunks(base64_string, chunk_size=5 * 1024 * 1024): 
#     return [base64_string[i:i + chunk_size] for i in range(0, len(base64_string), chunk_size)]