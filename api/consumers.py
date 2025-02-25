import json
from .models import *
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.files.base import ContentFile
from .serializers import *
import base64
from .utils import *

# from pydub import AudioSegment

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        # self.contact_phonenumber = self.scope["url_route"]["kwargs"]["contact_phonenumber"]
        self.channel_id= self.scope["url_route"]["kwargs"]["channel_id"]
        # self.user = self.scope['user']
        # print(self.user.id)
        # if self.user.is_authenticated:
        # self.room_group_name = "chat_%s" % f"{self.conversation_id}-{self.contact_phonenumber}"
        self.room_group_name = "chat_"
            # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        conversations = await self.get_conversations(self.channel_id)
        for conversation in conversations:
            await self.send(text_data=json.dumps({
                "type": "conversation",
                "conversation": conversation
            }))
            # messages = await self.get_messages(self.conversation_id)
            # for message in messages:
            #     await self.send(text_data=json.dumps(message))
        # else:
        # await self.close()


    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        conversation_id = text_data_json["conversation_id"]
        
        content_type = text_data_json["content_type"]
        from_bot = text_data_json['from_bot']
        wamid = text_data_json["wamid"]



        match content_type:
            # handel receive voice message
            case "audio":
                caption = text_data_json["caption"]
                if from_bot == "True":
                    content = text_data_json["content"]
                    media_name = text_data_json["media_name"]
                    decoded_audio = base64.b64decode(content)
                    # output_folder = 'media/chat_message'
                    output_folder = '/var/www/html/media/chat_message'
                    file_path = os.path.join(output_folder, media_name)
                    with open(file_path, "wb") as image_file:
                        image_file.write(decoded_audio)
                    conversation_id = await self.get_conversation(conversation_id)
                    message_id = await self.create_chat_image(conversation_id, content_type, caption, wamid, f"https://chatbot.icsl.me/media/chat_message/{media_name}")
                    # message_id = await self.create_chat_image(self.conversation_id, content_type, caption, wamid, f"http://127.0.0.1:8000/media/chat_message/{media_name}")
                    # Send image to room group
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message_audio",
                            "conversation_id": conversation_id,
                            "content": content,
                            "caption": caption,
                            "content_type": content_type,
                            "from_bot": from_bot,
                            "wamid": wamid,
                            "message_id": message_id,
                        }
                    )
                    send_message(
                        message_content= '',
                        to= await self.get_phonenumber(self.conversation_id),
                        wa_id= await self.get_waid(self.conversation_id),
                        bearer_token= await self.get_token(self.conversation_id),
                        chat_id=conversation_id,
                        platform="whatsapp",
                        # question={"label":caption},
                        type="audio",
                        source=f"https://chatbot.icsl.me/media/chat_message/{media_name}",
                    )
                else:
                    media_url = text_data_json["media_url"]
                    created_at = text_data_json["created_at"]
                    message_id = text_data_json["message_id"]
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message_audio",
                            "conversation_id": conversation_id,
                            "caption": caption,
                            "content_type": content_type,
                            "from_bot": from_bot,
                            "wamid": wamid,
                            "message_id": message_id,
                            "media_url" : media_url,
                            "created_at": created_at
                        }
                    )

            # handel receive image
            case 'image':
                caption = text_data_json["caption"]
                if from_bot == "True":
                    content = text_data_json["content"]
                    media_name = text_data_json["media_name"]
                    decoded_image = base64.b64decode(content)
                    # output_folder = 'media/chat_message'
                    output_folder = '/var/www/html/media/chat_message'
                    file_path = os.path.join(output_folder, media_name)
                    with open(file_path, "wb") as image_file:
                        image_file.write(decoded_image)
                    conversation_id = await self.get_conversation(conversation_id)
                    message_id = await self.create_chat_image(conversation_id, content_type, caption, wamid, f"https://chatbot.icsl.me/media/chat_message/{media_name}")
                    # message_id = await self.create_chat_image(self.conversation_id, content_type, caption, wamid, f"http://127.0.0.1:8000/media/chat_message/{media_name}")
                    # Send image to room group
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message_image",
                            "conversation_id": conversation_id,
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
                        to= await self.get_phonenumber(conversation_id),
                        wa_id= await self.get_waid(conversation_id),
                        bearer_token= await self.get_token(conversation_id),
                        chat_id=conversation_id,
                        platform="whatsapp",
                        question='',
                        type="image",
                        source=f"https://chatbot.icsl.me/media/chat_message/{media_name}",
                    )
                else:
                    media_url = text_data_json["media_url"]
                    created_at = text_data_json["created_at"]
                    message_id = text_data_json["message_id"]
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message_image",
                            "conversation_id": conversation_id,
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
                    decoded_video = base64.b64decode(content)
                    # output_folder = 'media/chat_message'
                    output_folder = '/var/www/html/media/chat_message'
                    file_path = os.path.join(output_folder, media_name)
                    with open(file_path, "wb") as image_file:
                        image_file.write(decoded_video)
                    conversation_id = await self.get_conversation(conversation_id)
                    message_id = await self.create_chat_image(conversation_id, content_type, caption, wamid, f"https://chatbot.icsl.me/media/chat_message/{media_name}")
                    # message_id = await self.create_chat_image(self.conversation_id, content_type, caption, wamid, f"http://127.0.0.1:8000/media/chat_message/{media_name}")
                    # Send image to room group
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message_video",
                            "conversation_id": conversation_id,
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
                        to= await self.get_phonenumber(conversation_id),
                        wa_id= await self.get_waid(conversation_id),
                        bearer_token= await self.get_token(conversation_id),
                        chat_id= conversation_id,
                        platform="whatsapp",
                        question={"label":caption},
                        type="video",
                        source=f"https://chatbot.icsl.me/media/chat_message/{media_name}",
                    )
                else:
                    media_url = text_data_json["media_url"]
                    created_at = text_data_json["created_at"]
                    message_id = text_data_json["message_id"]
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message_image",
                            "conversation_id": conversation_id,
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
                caption = text_data_json["caption"]
                mime_type = text_data_json["mime_type"]
                if from_bot == "True":
                    content = text_data_json["content"]
                    media_name = text_data_json["media_name"]
                    decoded_document = base64.b64decode(content)
                    # output_folder = 'media/chat_message'
                    output_folder = '/var/www/html/media/chat_message'
                    file_path = os.path.join(output_folder, media_name)
                    with open(file_path, "wb") as image_file:
                        image_file.write(decoded_document)
                    conversation_id = await self.get_conversation(conversation_id)
                    message_id = await self.create_chat_image(conversation_id, content_type, caption, wamid, f"https://chatbot.icsl.me/media/chat_message/{media_name}")
                    # message_id = await self.create_chat_image(self.conversation_id, content_type, caption, wamid, f"http://127.0.0.1:8000/media/chat_message/{media_name}")
                    # Send image to room group
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message_document",
                            "conversation_id": conversation_id,
                            "content": content,
                            "caption": caption,
                            "content_type": content_type,
                            "from_bot": from_bot,
                            "wamid": wamid,
                            "message_id": message_id,
                            "mime_type": mime_type
                        }
                    )
                    send_message(
                        message_content= caption,
                        to= await self.get_phonenumber(conversation_id),
                        wa_id= await self.get_waid(conversation_id),
                        bearer_token= await self.get_token(conversation_id),
                        chat_id= conversation_id,
                        platform="whatsapp",
                        type="document",
                        filename=media_name,
                        source=f"https://chatbot.icsl.me/media/chat_message/{media_name}",
                    )
                else:
                    media_url = text_data_json["media_url"]
                    created_at = text_data_json["created_at"]
                    message_id = text_data_json["message_id"]
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message_image",
                            "conversation_id": conversation_id,
                            "caption": caption,
                            "content_type": content_type,
                            "from_bot": from_bot,
                            "wamid": wamid,
                            "message_id": message_id,
                            "media_url" : media_url,
                            "created_at": created_at,
                            "mime_type": mime_type
                        }
                    )
            # Send message to room group
            case 'text':
                content = text_data_json["content"]
                message_id = text_data_json["message_id"]
                created_at = text_data_json['created_at']
                if from_bot == "False":
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message",
                            "conversation_id": conversation_id,
                            "content": content,
                            "content_type": content_type,
                            "from_bot":from_bot,
                            "wamid":wamid,
                            "message_id":message_id,
                            "created_at": created_at
                        }
                    )
                else:
                    message_id = await self.create_chat_message(conversation_id, content_type, content, from_bot, wamid)
                    send_message(
                        message_content=content,
                        to= await self.get_phonenumber(conversation_id),
                        wa_id= await self.get_waid(conversation_id),
                        bearer_token= await self.get_token(conversation_id),
                        chat_id= conversation_id,
                        platform="whatsapp",
                        question='statment'
                    )
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message",
                            "conversation_id": conversation_id,
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
        conversation_id = event["conversation_id"]
        

        if from_bot == "False":
            media_url = event["media_url"]
            created_at = event["created_at"]
            await self.send(text_data=json.dumps({
                    "type":"message",
                    "conversation_id": conversation_id,
                    "media_url":media_url,
                    "caption":caption,
                    "content_type": content_type,
                    #"sender":f"{self.user}",
                    "wamid": wamid,
                    "message_id":message_id,
                    "created_at":created_at,
                    "is_successfully":"true"
                }))
        else:
            await self.send(text_data=json.dumps({
                    "type": "message",
                    "message_id": message_id,
                    "wamid": wamid,
                    "conversation_id": conversation_id,
                    "is_successfully": "true"
                }))
            
    async def chat_message_video(self, event):
        content_type = event["content_type"]
        wamid = event["wamid"]
        message_id = event["message_id"]
        from_bot = event["from_bot"]
        caption = event["caption"]
        conversation_id = event["conversation_id"]
        
        if from_bot == "False":
            created_at = event["created_at"]
            media_url = event["media_url"]
            await self.send(text_data=json.dumps({
                    "type":"message",
                    "conversation_id": conversation_id,
                    "media_url":media_url,
                    "caption":caption,
                    "content_type": content_type,
                    #"sender":f"{self.user}",
                    "wamid": wamid,
                    "message_id":message_id,
                    "created_at":created_at,
                    "is_successfully":"true"
                }))
        else:
            await self.send(text_data=json.dumps({
                    "type": "message",
                    "message_id": message_id,
                    "wamid": wamid,
                    "conversation_id": conversation_id,
                    "is_successfully": "true"
                }))
            
    async def chat_message_audio(self, event):
        content_type = event["content_type"]
        wamid = event["wamid"]
        message_id = event["message_id"]
        from_bot = event["from_bot"]
        caption = event["caption"]
        conversation_id = event["conversation_id"]
        
        if from_bot == "False":
            created_at = event["created_at"]
            media_url = event["media_url"]
            await self.send(text_data=json.dumps({
                    "type":"message",
                    "conversation_id": conversation_id,
                    "media_url":media_url,
                    "caption":caption,
                    "content_type": content_type,
                    #"sender":f"{self.user}",
                    "wamid": wamid,
                    "message_id":message_id,
                    "created_at":created_at,
                    "is_successfully":"true"
                }))
        else:
            await self.send(text_data=json.dumps({
                    "type": "message",
                    "message_id": message_id,
                    "wamid": wamid,
                    "conversation_id": conversation_id,
                    "is_successfully": "true"
                }))      
                
    async def chat_message_document(self, event):
        content_type = event["content_type"]
        wamid = event["wamid"]
        message_id = event["message_id"]
        from_bot = event["from_bot"]
        caption = event["caption"]
        mime_type = event["mime_type"]
        conversation_id = event["conversation_id"]

        if from_bot == "False":
            created_at = event["created_at"]
            media_url = event["media_url"]
            await self.send(text_data=json.dumps({
                    "type":"message",
                    "conversation_id": conversation_id,
                    "media_url":media_url,
                    "caption":caption,
                    "content_type": content_type,
                    #"sender":f"{self.user}",
                    "wamid": wamid,
                    "message_id":message_id,
                    "created_at":created_at,
                    "mime_type": mime_type,
                    "is_successfully":"true"
                }))
        else:
            await self.send(text_data=json.dumps({
                    "type": "message",
                    "message_id": message_id,
                    "wamid": wamid,
                    "mime_type": mime_type,
                    "conversation_id": conversation_id,
                    "is_successfully": "true"
                }))
            
    # Receive message from room group
    async def chat_message(self, event):
        content = event["content"]
        content_type = event["content_type"]
        from_bot = event["from_bot"]
        wamid = event['wamid']
        conversation_id = event["conversation_id"]

        message_id_ = event["message_id"]
        created_at = event["created_at"]
        if from_bot == "False":
            await self.send(text_data=json.dumps({
                "type":"message",
                "message_id": message_id_,
                "content":content,
                "content_type":content_type,
                "conversation_id": conversation_id,
                "wamid":wamid,
                "created_at":created_at,
                "is_successfully":"true"
            }))
        else:
            await self.send(text_data=json.dumps({
                    "type": "message",
                    "message_id": message_id_,
                    "wamid": wamid,
                    "conversation_id": conversation_id,
                    "is_successfully": "true"
                }))

                
           
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

    @database_sync_to_async
    def get_conversation(self, conversation_id):
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        return conversation.conversation_id

    @database_sync_to_async
    def get_conversations(self, channel_id):
        channel = Channle.objects.get(channle_id = channel_id)
        conversation = channel.conversation_set.all().order_by('-created_at')
        serializer = ConversationSerializer(conversation, many=True)
        return serializer.data
# class DocumentConsumers(AsyncWebsocketConsumer):
#     async def connect(self):
#         self.room_name = self.scope['url_route']['kwargs']['room']
#         self.room_group_name = "chat_%s" % self.room_name
#         self.document_data = []

#         await self.channel_layer.group_add(self.room_group_name, self.channel_layer)

#         return self.accept()
    
#     async def disconnect(self, code):
#         return await super().disconnect(code)
    
#     async def receive(self, text_data=None, bytes_data=None):
#         text_data_json = json.loads(text_data)
#         chunk = text_data_json.get('chunk', '')
#         last_chunk = text_data_json.get('last_chunk', '')

#         self.document_data.append(chunk)

#         if last_chunk != '':
#             document_data = ''.join(self.document_data)

    
# # def split_base64_into_chunks(base64_string, chunk_size=5 * 1024 * 1024): 
# #     return [base64_string[i:i + chunk_size] for i in range(0, len(base64_string), chunk_size)]


class ListAllConversations(AsyncWebsocketConsumer):
    async def connect(self):
        self.channel_id = self.scope["url_route"]["kwargs"]["channel_id"]
        await self.accept()
        
        conversations = await self.get_conversation(self.channel_id)
        for conversation in conversations:
            await self.send(text_data=json.dumps(conversation))
        

    @database_sync_to_async
    def get_conversation(self, channel_id):
        channel = Channle.objects.get(channle_id = channel_id)
        conversation = channel.conversation_set.all()
        serializer = ConversationSerializer(conversation, many=True)
        return serializer.data
