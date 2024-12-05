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
        self.user = self.scope['user']
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
        media_name = text_data_json["media_name"]
        type_content_receive = text_data_json["type_content_receive"]

        # handel receive voice message
        if content_type == 'voice':
            decoded_voice = base64.b64decode(content)
            voice_file = ContentFile(decoded_voice, name=media_name)
            await database_sync_to_async(UploadImage.objects.create)(image_file=voice_file)
        # Send image to room group
            await self.channel_layer.group_send(
                    self.room_group_name, {
                        "type": "chat_message", 
                        "conversation_id": conversation_id,
                        "content": content,
                        "content_type": content_type,
                    }
                )


        # handel receive image
        elif content_type == 'image':
            decoded_image = base64.b64decode(content)
            image_file = ContentFile(decoded_image, name=media_name)
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
        elif content_type == 'video':
            decoded_video = base64.b64decode(content)
            video_file = ContentFile(decoded_video, name=media_name)
            await database_sync_to_async(UploadImage.objects.create)(image_file=video_file)
        # Send video to room group
            await self.channel_layer.group_send(
                self.room_group_name, {
                    "type": "chat_message", 
                    "conversation_id": conversation_id,
                    "content": content,
                    "content_type": content_type,
                }
            )

        # Send document to room group
        elif content_type == 'document':
            decoded_document = base64.b64decode(content)
            document_file = ContentFile(decoded_document, name=media_name)
            await database_sync_to_async(UploadImage.objects.create)(image_file=document_file)
        # Send document to room group
            await self.channel_layer.group_send(
                self.room_group_name, {
                    "type": "chat_message", 
                    "conversation_id": conversation_id,
                    "content": content,
                    "content_type": content_type,
                    "type_content_receive":type_content_receive,
                }
            )
        # Send message to room group
        elif content_type == 'text':
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
        type_content_receive = event["type_content_receive"]

        #handel voice
        if content_type == 'voice':
            await self.send(text_data=json.dumps({
                    "conversation_id": conversation_id,
                    "content": content,
                    "content_type": content_type,
                }))

        #handel document
        elif content_type == 'document':
            await self.send(text_data=json.dumps({
                    "conversation_id": conversation_id,
                    "content": content,
                    "content_type": content_type,
                    "type_content_receive":type_content_receive
                }))


        # handel image
        elif content_type == 'image':
            await self.send(text_data=json.dumps({
                    "conversation_id": conversation_id,
                    "content":content,
                    "content_type": content_type,
                }))
            
        # handle video
        elif content_type == 'video':
            await self.send(text_data=json.dumps({
                    "conversation_id": conversation_id,
                    "content": content,
                    "content_type": content_type,
                }))
            
        # handel message  
        elif content_type == 'text':
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