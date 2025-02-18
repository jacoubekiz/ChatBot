import json
from .models import *
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.files.base import ContentFile
from .serializers import ChatMessageSerializer
import base64
from .utils import *

# from pydub import AudioSegment

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.contact_phonenumber = self.scope["url_route"]["kwargs"]["contact_phonenumber"]
        self.user = self.scope['user']
        print(self.user.id)
        if self.user.is_authenticated:
            self.room_group_name = "chat_%s" % f"{self.conversation_id}-{self.contact_phonenumber}"
            # Join room group
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()
            # messages = await self.get_messages(self.conversation_id)
            # for message in messages:
            #     await self.send(text_data=json.dumps(message))
        else:
            await self.close()


    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        # conversation_id = self.conversation_id
        
        content_type = text_data_json["content_type"]
        from_bot = text_data_json['from_bot']
        wamid = text_data_json["wamid"]



        match content_type:
            # handel receive voice message
            case "voice":
                content = text_data_json["content"]
                media_name = text_data_json["media_name"]
                decoded_voice = base64.b64decode(content)
                voice_file = ContentFile(decoded_voice, name=media_name)
                await database_sync_to_async(UploadImage.objects.create)(image_file=voice_file)
            # Send image to room group
                await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message",
                            "conversation_id": self.conversation_id,
                            "content": content,
                            "content_type": content_type,
                        }
                    )

            # handel receive image
            case 'image':
                caption = text_data_json["caption"]
                if from_bot == "True":
                    content = text_data_json["content"]
                    media_name = text_data_json["media_name"]
                    decoded_image = base64.b64decode(content)
                    image_file = ContentFile(decoded_image, name=media_name)
                    image = await self.create_file(image_file)
                    message_id = await self.create_chat_image(self.conversation_id, content_type, caption, wamid, f"https://chatbot.icsl.me{image}")
                    # Send image to room group
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message_image",
                            "conversation_id": self.conversation_id,
                            "content": content,
                            "caption": caption,
                            "content_type": content_type,
                            "from_bot": from_bot,
                            "wamid": wamid,
                            "message_id": message_id,
                        }
                    )
                    send_message(
                        message_content= caption,
                        to= await self.get_phonenumber(self.conversation_id),
                        wa_id= await self.get_waid(self.conversation_id),
                        bearer_token= await self.get_token(self.conversation_id),
                        chat_id=self.conversation_id,
                        platform="whatsapp",
                        question='',
                        type="image",
                        source=f"http://127.0.0.1:8000{image}",
                    )
                else:
                    media_url = text_data_json["media_url"]
                    created_at = text_data_json["created_at"]
                    message_id = text_data_json["message_id"]
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message_image",
                            "conversation_id": self.conversation_id,
                            "caption": caption,
                            "content_type": content_type,
                            "from_bot": from_bot,
                            "wamid": wamid,
                            "message_id": message_id,
                            "media_url" : media_url,
                            "created_at": created_at
                        }
                    )
            # handel receive video
            case 'video':
                caption = text_data_json["caption"]
                if from_bot == "True":
                    content = text_data_json["content"]
                    media_name = text_data_json["media_name"]
                    decoded_image = base64.b64decode(content)
                    image_file = ContentFile(decoded_image, name=media_name)
                    image = await self.create_file(image_file)
                    message_id = await self.create_chat_image(self.conversation_id, content_type, caption, wamid, f"https://chatbot.icsl.me{image}")
                    # Send image to room group
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message_video",
                            "conversation_id": self.conversation_id,
                            "content": content,
                            "caption": caption,
                            "content_type": content_type,
                            "from_bot": from_bot,
                            "wamid": wamid,
                            "message_id": message_id,
                        }
                    )
                    print("hello")
                    send_message(
                        message_content= '',
                        to= await self.get_phonenumber(self.conversation_id),
                        wa_id= await self.get_waid(self.conversation_id),
                        bearer_token= await self.get_token(self.conversation_id),
                        chat_id=self.conversation_id,
                        platform="whatsapp",
                        question={"label":caption},
                        type="video",
                        source="https://chatbot.icsl.me/media/chat_message/WhatsApp_Video_2025-02-04_at_08.43.04_df95132d.mp4",
                    )
                else:
                    media_url = text_data_json["media_url"]
                    created_at = text_data_json["created_at"]
                    message_id = text_data_json["message_id"]
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message_image",
                            "conversation_id": self.conversation_id,
                            "caption": caption,
                            "content_type": content_type,
                            "from_bot": from_bot,
                            "wamid": wamid,
                            "message_id": message_id,
                            "media_url" : media_url,
                            "created_at": created_at
                        }
                    )
            # Send document to room group
            case 'document':
                content = text_data_json["content"]
                media_name = text_data_json["media_name"]
                type_content_receive = text_data_json["type_content_receive"]
                decoded_document = base64.b64decode(content)
                document_file = ContentFile(decoded_document, name=media_name)
                await database_sync_to_async(UploadImage.objects.create)(image_file=document_file)
            # Send document to room group
                await self.channel_layer.group_send(
                    self.room_group_name, {
                        "type": "chat_message",
                        "conversation_id": self.conversation_id,
                        "content": content,
                        "content_type": content_type,
                        "type_content_receive":type_content_receive,
                    }
                )
            # Send message to room group
            case 'text':
                content = text_data_json["content"]
                message_id = text_data_json["message_id"]
                created_at = text_data_json['created_at']
                await self.channel_layer.group_send(
                    self.room_group_name, {
                        "type": "chat_message",
                        "conversation_id": self.conversation_id,
                        "content": content,
                        "content_type": content_type,
                        "from_bot":from_bot,
                        "wamid":wamid,
                        "message_id":message_id,
                        "created_at": created_at
                    }
                )

    async def chat_message_image(self, event):
        content_type = event["content_type"]
        wamid = event["wamid"]
        message_id = event["message_id"]
        from_bot = event["from_bot"]
        caption = event["caption"]

        if from_bot == "False":
            media_url = event["media_url"]
            await self.send(text_data=json.dumps({
                    "conversation_id": self.conversation_id,
                    "media_url":media_url,
                    "caption":caption,
                    "content_type": content_type,
                    "sender":f"{self.user}",
                    "wamid": wamid,
                    "message_id":message_id,
                    "is_successfully":"true"
                }))
        else:
            await self.send(text_data=json.dumps({
                    "message_id":message_id,
                    "wamid":wamid,
                    "is_successfully":"true"
                }))
            
    async def chat_message_video(self, event):
        content_type = event["content_type"]
        wamid = event["wamid"]
        message_id = event["message_id"]
        from_bot = event["from_bot"]
        caption = event["caption"]

        if from_bot == "False":
            media_url = event["media_url"]
            await self.send(text_data=json.dumps({
                    "conversation_id": self.conversation_id,
                    "media_url":media_url,
                    "caption":caption,
                    "content_type": content_type,
                    "sender":f"{self.user}",
                    "wamid": wamid,
                    "message_id":message_id,
                    "is_successfully":"true"
                }))
        else:
            await self.send(text_data=json.dumps({
                    "message_id":message_id,
                    "wamid":wamid,
                    "is_successfully":"true"
                }))
    # Receive message from room group
    async def chat_message(self, event):
        # conversation_id = event["conversation_id"]
        content = event["content"]
        content_type = event["content_type"]
        from_bot = event["from_bot"]
        wamid = event['wamid']


        match content_type:
        #handel voice
            case 'voice':
                await self.send(text_data=json.dumps({
                        # "conversation_id": self.conversation_id,
                        # "content": content,
                        # "content_type": content_type,
                        # "sender":self.user
                        "message_id":message_id,
                        "is_successfully":"true"
                    }))

            #handel document
            case 'document':
                type_content_receive = event["type_content_receive"]
                await self.send(text_data=json.dumps({
                        # "conversation_id": self.conversation_id,
                        # "content": content,
                        # "content_type": content_type,
                        # "type_content_receive":type_content_receive,
                        # "sender":self.user
                        "message_id":message_id,
                        "is_successfully":"true"
                    }))


            # handle video
            case 'video':
                await self.send(text_data=json.dumps({
                        # "conversation_id": self.conversation_id,
                        # "content": content,
                        # "content_type": content_type,
                        # "sender":self.user
                        "message_id":message_id,
                        "is_successfully":"true"
                    }))
        
            # handel message
            case 'text':
                message_id_ = event["message_id"]
                created_at = event["created_at"]
                if from_bot == "False":
                    await self.send(text_data=json.dumps({
                        "message_id": message_id_,
                        "content":content,
                        "content_type":content_type,
                        "conversation_id":self.conversation_id,
                        "wamid":wamid,
                        "created_at":created_at,
                        "is_successfully":"true"
                    }))
                else:
                    message_id = await self.create_chat_message(self.conversation_id, content_type, content, from_bot, wamid)
                    await self.send(text_data=json.dumps({
                            "message_id":message_id,
                            "wamid":wamid,
                            "is_successfully":"true"
                        }))
                    send_message(
                        message_content=content,
                        to= await self.get_phonenumber(self.conversation_id),
                        wa_id= await self.get_waid(self.conversation_id),
                        bearer_token= await self.get_token(self.conversation_id),
                        chat_id=self.conversation_id,
                        platform="whatsapp",
                        question='statment'
                    )
                
           
    @database_sync_to_async
    def create_chat_message(self, conversation_id, content_type, content, wamid, media_url):
        conversation = Conversation.objects.filter(conversation_id=conversation_id).first()
        chat_message = ChatMessage.objects.create(
            conversation_id = conversation,
            # user_id = CustomUser1.objects.filter(id=self.user.id).first(),
            content_type = content_type,
            content = content,
            # from_message = bot,
            wamid = wamid,
            media_url = media_url,
        )
        return chat_message.message_id
    
    @database_sync_to_async
    def create_chat_image(self, conversation_id, content_type, caption, wamid, media_url):
        conversation = Conversation.objects.filter(conversation_id=conversation_id).first()
        chat_message = ChatMessage.objects.create(
            conversation_id = conversation,
            # user_id = CustomUser1.objects.filter(id=self.user.id).first(),
            content_type = content_type,
            caption = caption,
            # from_message = bot,
            wamid = wamid,
            media_url = media_url,
        )
        return chat_message.message_id
    
    
    @database_sync_to_async
    def get_messages(self, conversation_id):
        conversation_id = Conversation.objects.filter(conversation_id=conversation_id).first()
        messages = conversation_id.chatmessage_set.all().order_by("created_at")
        serializer_messages = ChatMessageSerializer(messages, many=True)
        return serializer_messages.data

    @database_sync_to_async
    def get_phonenumber(self, conversation_id):
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        phonenumber = conversation.contact_id.phone_number
        return phonenumber
    
    @database_sync_to_async
    def get_waid(self, conversation_id):
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        print(conversation.channle_id)
        waid = conversation.channle_id.phone_number_id
        return waid

    @database_sync_to_async
    def get_token(self, conversation_id):
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        tocken = conversation.channle_id.tocken
        return tocken

    @database_sync_to_async
    def create_file(self, file_name):
        file = UploadImage.objects.create(image_file=file_name)
        return file.get_absolute_url
    
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