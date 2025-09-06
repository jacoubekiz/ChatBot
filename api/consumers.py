import json
from .models import *
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.files.base import ContentFile
from .serializers import *
import base64
from django.db.models import Q
from django.core.files.storage import default_storage
import langid
from .utils import *
from django.utils import timezone
import urllib.parse as up

# from pydub import AudioSegment

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.channel_id= self.scope["url_route"]["kwargs"]["channel_id"]
        self.room_group_name = "chat_"
            # Join room group
        self.user = self.scope['user']
        query_string = self.scope['query_string'].decode()
        params = dict(up.parse_qsl(query_string))
        self.from_message = params.get('from_bot')
        if self.user and self.user.is_authenticated:
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()
            conversations = await self.get_conversations(self.channel_id)
            for conversation in conversations:
                message = await self.get_last_message(conversation.get('conversation_id'))
                if message == None:
                    await self.return_conversation(conversation.get('conversation_id'))
                else:
                    s = timezone.now() - message.created_at
                    if s > timedelta(hours=24):
                        await self.return_conversation(conversation.get('conversation_id'))
            # for conversation in conversations:
            await self.send(text_data=json.dumps({
                "type": "conversation",
                "conversation": conversations
            }))
        elif self.from_message == 'False':
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()
            # conversations = await self.get_conversations(self.channel_id)
            # for conversation in conversations:
            #     message = await self.get_last_message(conversation.get('conversation_id'))
            #     if message == None:
            #         await self.return_conversation(conversation.get('conversation_id'))
            #     else:
            #         s = timezone.now() - message.created_at
            #         if s > timedelta(hours=24):
            #             await self.return_conversation(conversation.get('conversation_id'))
            # # for conversation in conversations:
            # await self.send(text_data=json.dumps({
            #     "type": "conversation",
            #     "conversation": conversations
            # }))
        else:
            await self.close()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        conversation_id = text_data_json["conversation_id"]
        content_type = text_data_json["content_type"]
        from_bot = text_data_json['from_bot']
        await self.change_status(conversation_id, from_bot)


        match content_type:
            case "message_status":
                message_id = text_data_json['message_id']
                status_message = text_data_json['status']

                await self.channel_layer.group_send(
                    self.room_group_name, {
                        "type": "chat_message_status",
                        "conversation_id": conversation_id,
                        "content_type": content_type,
                        "message_id":message_id,
                        "status_message": status_message
                    }
                )
            # handel receive template message
            case "template":
                front_id = text_data_json['front_id']
                content = text_data_json["content"]
                template_info = text_data_json['template_info']
                created_at = text_data_json['created_at']
                channel_id = await self.get_channel(self.channel_id)
                url = f"https://graph.facebook.com/v22.0/{channel_id.phone_number_id}/messages"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"{channel_id.tocken}"
                }
                template_data = json.dumps(template_info)   
                response = requests.post(url, headers=headers, data=template_data)
                data = json.loads(response.content.decode())
                template_wamid = data['messages'][0]['id']
                message_id = await self.create_chat_message(conversation_id, self.user, content_type, content, template_wamid)
                await self.channel_layer.group_send(
                    self.room_group_name, {
                        "type": "chat_message",
                        "conversation_id": conversation_id,
                        "content": content,
                        "content_type": content_type,
                        "from_bot":from_bot,
                        "wamid":template_wamid,
                        "front_id":front_id,
                        "message_id":message_id,
                        "created_at": created_at
                    }
                )

            # handel receive voice message
            case "audio":
                caption = text_data_json["caption"]
                if from_bot == "True":
                    media_name = text_data_json["media_name"]
                    front_id = text_data_json['front_id']
                    message_wamid = send_message(
                        message_content= '',
                        to= await self.get_phonenumber(conversation_id),
                        wa_id= await self.get_waid(conversation_id),
                        bearer_token= await self.get_token(conversation_id),
                        chat_id=conversation_id,
                        platform="whatsapp",
                        # question={"label":caption},
                        type="audio",
                        source=f"https://chatbot.icsl.me/media/chat_message/{media_name}",
                    )
                    content = text_data_json["content"]
                    decoded_audio = base64.b64decode(content)
                    # output_folder = 'media/chat_message'
                    output_folder = '/var/www/html/media/chat_message'
                    file_path = os.path.join(output_folder, media_name)
                    with open(file_path, "wb") as image_file:
                        image_file.write(decoded_audio)
                    conversation_id = await self.get_conversation(conversation_id)
                    message_id = await self.create_chat_image(conversation_id, self.user, content_type, caption, message_wamid, f"https://chatbot.icsl.me/media/chat_message/{media_name}")
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
                            "wamid": message_wamid,
                            "message_id": message_id,
                            "front_id": front_id
                        }
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
                            "wamid": 'message_wamid',
                            "message_id": message_id,
                            "media_url" : media_url,
                            "created_at": created_at
                        }
                    )

            # handel receive image
            case 'image':
                caption = text_data_json["caption"]
                media_name = text_data_json["media_name"]
                if from_bot == "True":
                    message_wamid = send_message(
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
                    content = text_data_json["content"]
                    front_id = text_data_json['front_id']
                    decoded_image = base64.b64decode(content)
                    # output_folder = 'media/chat_message'
                    output_folder = '/var/www/html/media/chat_message'
                    file_path = os.path.join(output_folder, media_name)
                    with open(file_path, "wb") as image_file:
                        image_file.write(decoded_image)
                    conversation_id = await self.get_conversation(conversation_id)
                    message_id = await self.create_chat_image(conversation_id, self.user, content_type, caption, message_wamid, f"https://chatbot.icsl.me/media/chat_message/{media_name}")
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
                            "wamid": message_wamid,
                            "message_id": message_id,
                            "front_id": front_id
                        }
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
                            "wamid": 'wamid',
                            "message_id": message_id,
                            "media_url" : media_url,
                            "created_at": created_at
                        }
                    )
            # handel receive video
            case 'video':
                caption = text_data_json["caption"]
                if from_bot == "True":
                    media_name = text_data_json["media_name"]
                    message_wamid = send_message(
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
                    front_id = text_data_json["front_id"]
                    content = text_data_json["content"]
                    decoded_video = base64.b64decode(content)
                    output_folder = '/var/www/html/media/chat_message'
                    file_path = os.path.join(output_folder, media_name)
                    with open(file_path, "wb") as image_file:
                        image_file.write(decoded_video)
                    conversation_id = await self.get_conversation(conversation_id)
                    message_id = await self.create_chat_image(conversation_id, self.user, content_type, caption, message_wamid, f"https://chatbot.icsl.me/media/chat_message/{media_name}")
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
                            "wamid": message_wamid,
                            "message_id": message_id,
                            "front_id": front_id
                        }
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
                            "wamid": 'wamid',
                            "message_id": message_id,
                            "media_url" : media_url,
                            "created_at": created_at
                        }
                    )
            # Send document to room group
            case 'document':
                caption = text_data_json["caption"]
                if from_bot == "True":
                    media_name = text_data_json["media_name"]
                    message_wamid = send_message(
                        message_content= caption,
                        to= await self.get_phonenumber(conversation_id),
                        wa_id= await self.get_waid(conversation_id),
                        bearer_token= await self.get_token(conversation_id),
                        chat_id= conversation_id,
                        platform="whatsapp",
                        type="document",
                        source=f"https://chatbot.icsl.me/media/chat_message/{media_name}",
                    )
                    content = text_data_json["content"]
                    front_id = text_data_json["front_id"]
                    decoded_document = base64.b64decode(content)
                    output_folder = '/var/www/html/media/chat_message'
                    file_path = os.path.join(output_folder, media_name)
                    with open(file_path, "wb") as image_file:
                        image_file.write(decoded_document)
                    conversation_id = await self.get_conversation(conversation_id)
                    message_id = await self.create_chat_image(conversation_id, self.user, content_type, caption, message_wamid, f"https://chatbot.icsl.me/media/chat_message/{media_name}")
                    # Send image to room group
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message_document",
                            "conversation_id": conversation_id,
                            "content": content,
                            "caption": caption,
                            "content_type": content_type,
                            "from_bot": from_bot,
                            "wamid": message_wamid,
                            "message_id": message_id,
                            "front_id": front_id
                        }
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
                            "wamid": 'wamid',
                            "message_id": message_id,
                            "media_url" : media_url,
                            "created_at": created_at,
                            # "mime_type": mime_type
                        }
                    )
            # Send message to room group
            case 'text':
                content = text_data_json["content"]
                created_at = text_data_json['created_at']
                if from_bot == "False":
                    message_id = text_data_json["message_id"]
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message",
                            "conversation_id": conversation_id,
                            "content": content,
                            "content_type": content_type,
                            "from_bot":from_bot,
                            "wamid":'wamid',
                            "message_id":message_id,
                            "created_at": created_at
                        }
                    )
                else:
                    # status = text_data_json['status']
                    message_wamid = send_message(
                        message_content=content,
                        to= await self.get_phonenumber(conversation_id),
                        wa_id= await self.get_waid(conversation_id),
                        bearer_token= await self.get_token(conversation_id),
                        chat_id= conversation_id,
                        platform="whatsapp",
                        question='statment'
                    )
                    front_id = text_data_json['front_id']
                    message_id = await self.create_chat_message(conversation_id, self.user, content_type, content, message_wamid)
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message",
                            "conversation_id": conversation_id,
                            "content": content,
                            "content_type": content_type,
                            "from_bot":from_bot,
                            "wamid":message_wamid,
                            "message_id":message_id,
                            "created_at": created_at,
                            "front_id": front_id
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
                    "wamid": wamid,
                    "message_id":message_id,
                    "created_at":created_at,
                    "is_successfully":"true"
                }))
        else:
            front_id = event["front_id"]
            await self.send(text_data=json.dumps({
                    "type": "message",
                    "content_type":"message_status",
                    "message_id": message_id,
                    "wamid": wamid,
                    "conversation_id": conversation_id,
                    "front_id": front_id,
                    "is_successfully": "true",
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
                    "wamid": wamid,
                    "message_id":message_id,
                    "created_at":created_at,
                    "is_successfully":"true"
                }))
        else:
            front_id = event["front_id"]
            await self.send(text_data=json.dumps({
                    "type": "message",
                    "content_type":"message_status",
                    "message_id": message_id,
                    "wamid": wamid,
                    "conversation_id": conversation_id,
                    "front_id": front_id,
                    "is_successfully": "true",
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
                    "wamid": wamid,
                    "message_id":message_id,
                    "created_at":created_at,
                    "is_successfully":"true"
                }))
        else:
            front_id = event['front_id']
            await self.send(text_data=json.dumps({
                    "type": "message",
                    "content_type":"message_status",
                    "message_id": message_id,
                    "wamid": wamid,
                    "conversation_id": conversation_id,
                    "front_id": front_id,
                    "is_successfully": "true",
                }))      
                
    async def chat_message_document(self, event):
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
                    "wamid": wamid,
                    "message_id":message_id,
                    "created_at":created_at,
                    "is_successfully":"true"
                }))
        else:
            front_id = event['front_id']
            await self.send(text_data=json.dumps({
                    "type": "message",
                    "content_type":"message_status",
                    "message_id": message_id,
                    "wamid": wamid,
                    "conversation_id": conversation_id,
                    "front_id": front_id,
                    "is_successfully": "true",
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
            front_id = event["front_id"]
            await self.send(text_data=json.dumps({
                    "type": "message",
                    "content_type":"message_status",
                    "message_id": message_id_,
                    "wamid": wamid,
                    "conversation_id": conversation_id,
                    "front_id": front_id,
                    "is_successfully": "true",
                }))

    async def chat_message_status(self, event):
        content_type = event["content_type"] 
        conversation_id = event["conversation_id"]
        message_id_ = event["message_id"]
        status_message = event["status_message"]

        await self.send(text_data=json.dumps({
                "message_id": message_id_,
                "conversation_id": conversation_id,
                "content_type": content_type,
                "status_message" : status_message
                }))

           
    @database_sync_to_async
    def get_last_message(self, conversation_id):
        conversation = Conversation.objects.filter(conversation_id=conversation_id).first()
        message = conversation.chatmessage_set.exclude(from_message ='bot').order_by("-created_at").first()
        return message
    
    @database_sync_to_async
    def create_chat_message(self, conversation_id, user, content_type, content, wamid):
        conversation = Conversation.objects.filter(conversation_id=conversation_id).first()
        chat_message = ChatMessage.objects.create(
            conversation_id = conversation,
            user_id = user,
            content_type = content_type,
            content = content,
            wamid = wamid,
            # from_message = from_bot
        )
        return chat_message.message_id
    
    @database_sync_to_async
    def create_chat_image(self, conversation_id, user, content_type, caption, wamid, media_url):
        conversation = Conversation.objects.filter(conversation_id=conversation_id).first()
        chat_message = ChatMessage.objects.create(
            conversation_id = conversation,
            user_id = user,
            content_type = content_type,
            caption = caption,
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
        conversation.updated_at = timezone.now()
        conversation.save()
        return conversation.conversation_id

    @database_sync_to_async
    def get_conversations(self, channel_id):
        user = CustomUser.objects.get(id=self.user.id)
        permissions = list(user.get_all_permissions())
        if 'api.visibility all conversations' in permissions:
            conversation = Conversation.objects.filter(channle_id=channel_id)
            # conversation = channel.conversation_set.all().order_by('-updated_at')
            serializer = ConversationSerializer(conversation, many=True)
            return serializer.data
        else:
            conversation = Conversation.objects.filter(channle_id=channel_id, user=self.user)
            # conversation = channel.conversation_set.all().order_by('-updated_at')
            serializer = ConversationSerializer(conversation, many=True)
            return serializer.data
    @database_sync_to_async
    def get_channel(self, channel_id):
        channel = Channle.objects.get(channle_id = channel_id)
        return channel
    
    @database_sync_to_async
    def get_message(self, message_id):
        message = ChatMessage.objects.get(message_id = message_id)
        message.status_message = 'delivered'
        message.save()
        return message
    
    @database_sync_to_async
    def return_conversation(self, con_id):
        conv = Conversation.objects.get(conversation_id=con_id)
        conv.status = 'lock'
        return conv.save()
    
    @database_sync_to_async
    def change_status(self, conversation_id, from_bot):
        if from_bot == 'False':
            print("yes its me")
            c =Conversation.objects.get(conversation_id=conversation_id)
            c.status = 'open'
            c.save()
        return True
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


class ChatBotConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.channel_id = self.scope["url_route"]["kwargs"]["channel_id"]
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.room_group_name = "djsdk"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        text_data_json = json.loads(text_data)
        data = text_data_json.get('data', '')

        
        

        try:
            conversation = data['conversation']
            source_id = conversation['contact_inbox']['source_id']
            platform = 'whatsapp'

        except:
            source_id = data.get('entry')[0]['changes'][0]['value']['messages'][0]['from']
            platform = 'beam'

        value = await self.chat_bot(data, source_id, platform)
        if value == True:   
            await self.channel_layer.group_send(
                self.room_group_name, {
                    "type": "bot_integration",
                    "Message": "bot_integration_succesfully",
                }
            )
        else:
            await self.channel_layer.group_send(
                self.room_group_name, {
                    "type": "bot_integration_error",
                    'Message' : 'Please make sure you have provided client info and source_id.'
                }
            )

    async def bot_integration_error(self, event):
        message = event["Message"]

        await self.send(text_data=json.dumps({
            "type":"message",
            "message": message,
            "is_successfully":"False"
        }))

    async def bot_integration(self, event):
        message = event["Message"]

        await self.send(text_data=json.dumps({
            "type":"message",
            "message": message,
            "is_successfully":"True"
        }))


    @database_sync_to_async
    def chat_bot(self, data, source_id, platform):
        try:
            channel = Channle.objects.get(Q(channle_id = self.channel_id))
        except:
            pass
        reset_flow = False
        restart_keyword = RestartKeyword.objects.filter(channel_id=channel.channle_id)
        for rest in restart_keyword:
            if rest.keyword == data['content']:
                reset_flow = True
                flows = rest.channel_id.flows.all()
                for flow in flows:
                    ch = Chat.objects.filter(Q(conversation_id = source_id) & Q(channel_id = channel.channle_id) & Q(flow=flow)).first()
                    if ch :
                        ch.update_state('start')
                        ch.isSent = False
                        ch.save()
                    continue
                break
        
        try:
            flow =  channel.flows.get(trigger__trigger=data['content'])
            chats = Chat.objects.filter(Q(conversation_id = source_id) & Q(channel_id = channel.channle_id) & ~Q(flow = flow))
            for c in chats:
                c.update_state('end')
                c.isSent = False
                c.save()
        except:
            ch = ch = Chat.objects.filter(Q(conversation_id = source_id) & Q(channel_id = channel.channle_id) & ~Q(state = 'end')).first()
            if ch:
                flow = ch.flow
            else:
                flow = None
            
        if not flow:
            flow = channel.flows.get(is_default = True)
        file_path = default_storage.path(flow.flow.name)
        chat_flow = read_json(file_path)
        if chat_flow and source_id:
            chat, isCreated = Chat.objects.get_or_create(conversation_id = source_id, channel_id = channel, flow=flow )
            questions = chat_flow['payload']['questions']
            print(questions)
            if not bool(chat.state) or chat.state == 'end' or chat.state == '':
                chat.update_state('start')
            while True:
                next_question_id = None
                if chat.state == 'start':
                    if reset_flow:
                        question = questions[0]
                        if question['type'] == 'detect_language':
                            
                            question = questions[int(questions.index(questions[0]) + 1)]

                    else:
                        question = questions[0]
                #         lang = langid.classify(request.data['content'])
                #         language = lang[0]
                #         # print(language)
                #         for ques in questions:
                #             try:
                #                 print(ques['type_language'])
                #                 ques_lang_type = ques['type_language']
                #             except:
                #                 ques_lang_type = ''
                #             if ques_lang_type  == language:
                #                     print('hello')
                #                     question = ques
                #                     break
                else:
                    for item in questions:
                        if item['id'] == chat.state:
                            question = item
                            break
                        
                message, next_question_id, choices_with_next, choices, r_type, attribute_name = show_response(question, questions)

                if r_type == 'detect_language':
                    lang = langid.classify(data['content'])
                    language = lang[0]
                    next_options = [(option['value'], option['next']['target']) for option in question['options']]
                    detect = False
                    for options in next_options:
                        for opt in options:
                            if opt == language:
                                detect = True
                                next_question_id = options[1]
                                break
                    if not detect:
                        next_question_id = next_options[-1][1]
                if r_type == 'button' or r_type == 'list':
                    
                    if not chat.isSent:
                        chat.isSent = True
                        chat.save()
                        
                        if r_type == 'list':
                            send_message(message_content=message,
                                        choices = choices,
                                        type='interactive', 
                                        interaction_type='list',
                                        footer=question['footer'],
                                        header=question['header'],
                                        to = chat.conversation_id,
                                        bearer_token=channel.tocken,
                                        wa_id=channel.phone_number_id,
                                        chat_id=chat.id,
                                        platform=platform,
                                        question=question)
                        
                        else:
                            send_message(message_content=message,
                                        choices = choices,
                                        type='interactive', 
                                        interaction_type='button',
                                        to=chat.conversation_id,
                                        bearer_token=channel.tocken,
                                        wa_id=channel.phone_number_id,
                                        chat_id=chat.id,
                                        platform=platform,
                                        question=question)
                            
                        return Response(
                            {"Message" : "BOT has interacted successfully."},
                            status=status.HTTP_200_OK
                        )
                        
                    else:
                        try:
                            user_reply = data['content'] #If this raises an error then it means that the response has come from Beam not Whatsapp
                        except:
                            user_reply = data['entry'][0]['changes'][0]['value']['messages'][0]['text']['body']
                            
                            # except:
                            #     user_reply = request.data['entry'][0]['changes'][0]['value']['messages'][0]['reply_to']['button_title']
                            
                        if user_reply not in choices or user_reply == '':
                            error_message = question['message']['error']
                            
                            send_message(message_content=error_message,
                                            to=chat.conversation_id,
                                            bearer_token=channel.tocken,
                                            wa_id=channel.phone_number_id,
                                            chat_id=chat.id,
                                            platform=platform,
                                            question=question)
                            
                            return Response(
                                {"Message" : "BOT has interacted successfully."},
                                status=status.HTTP_200_OK
                            )
                        
                        else:
                            next_question_id = [c[2] for c in choices_with_next if user_reply == c[0]][0]
                            chat.update_state(next_question_id)
                            chat.isSent = False
                            chat.save()
                
                elif r_type == 'smart_question' and choices_with_next:
                    if not chat.isSent:
                        chat.isSent = True
                        chat.save()
                        
                        send_message(message_content=message,
                                    to = chat.conversation_id,
                                    bearer_token=channel.tocken,
                                    wa_id=channel.phone_number_id,
                                    chat_id=chat.id,
                                    platform=platform,
                                    question=question)
                        return Response(
                            {"Message" : "BOT has interacted successfully."},
                            status=status.HTTP_200_OK
                        )
                    
                    else:
                        try:
                            user_reply = data['content'] #If this raises an error then it means that the response has come from Beam not Whatsapp                        
                        except:
                            
                            try: #If this raises an error then this means that it is a beam user reply not normal beam text message reply
                                user_reply = data['entry'][0]['changes'][0]['value']['messages'][0]['text']['body']
                            
                            except:
                                user_reply = data['entry'][0]['changes'][0]['value']['messages'][0]['reply_to']['button_title']
                                
                        
                        attr, created = Attribute.objects.get_or_create(key=attribute_name, chat_id=chat.id)
                        attr.value = user_reply
                        attr.save()
                        
                        for option in choices_with_next:
                            matchingType = option[3]
                            if matchingType == 'CONTAIN':
                    
                                if any(string in user_reply for string in option[4]):
                                    next_question_id = option[2]
                                    break
                    
                            elif matchingType == 'EXACT':
                                if any(string == user_reply for string in option[4]):
                                    next_question_id = option[2]
                                    break
                    
                        chat.update_state(next_question_id)
                        chat.isSent = False
                        chat.save()
                # for handel component calender
                    
                # elif question['type'] == 'calendar':
                #     headers = {
                #             'Content-Type': 'application/json',
                #         }
                #     day = Attribute.objects.filter(key='day', chat=chat.id).first()
                #     hour = Attribute.objects.filter(key='hour', chat=chat.id).first()
                #     if not day or day == None:
                #         if not chat.isSent:
                #             chat.isSent = True
                #             chat.save()
                #             url = f"https://chatbot.ics.me/get-first-ten-days/?date=&key={question['key']}"
                #             response = requests.get(url , headers=headers)
                #             result = response.json()
                #             choice = next(iter(result.values()))
                #             choice.append('next')
                #             NextTenDay.objects.create(chat=chat, day=choice[0], day_end=choice[-2])
                #             chat.update_state(question['id'])
                #             send_message(message_content=question['day-message'],
                #                     choices = choice,
                #                     type='interactive',
                #                     interaction_type='button',
                #                     to=chat.conversation_id,
                #                     bearer_token=client.token,
                #                     wa_id=client.wa_id,
                #                     chat_id=chat.id,
                #                     platform=platform,
                #                     question=question
                #                 )
                #             return Response({"Message" : "BOT has interacted successfully."},status=status.HTTP_200_OK)
                #         else:
                #             day = NextTenDay.objects.filter(chat=chat.id).first()
                #             url = f"https://chatbot.ics.me/get-first-ten-days/?date={day.day}&key={question['key']}"
                #             response = requests.get(url , headers=headers)
                #             result = response.json()
                #             choices = next(iter(result.values()))
                #             print(len(choices))
                #             # if len(choices) > 9:
                #             choices.append('next')
                #             # else:
                #             #     print('I am her')
                #             #     day.day = choices[-1]
                #             #     day.save()
                #             # print(choices)
                #             user_reply = request.data['content']
                #             if user_reply not in choices:
                #                 error_message = question['error-Message']
                #                 send_message(message_content=error_message,
                #                                 to=chat.conversation_id,
                #                                 bearer_token=client.token,
                #                                 wa_id=client.wa_id,
                #                                 chat_id=chat.id,
                #                                 platform=platform,
                #                                 question=question)
                #                 return Response(
                #                     {"Message" : "BOT has interacted successfully."},
                #                     status=status.HTTP_200_OK
                #                 )
                #             # print(user_reply)
                            
                #             if user_reply == "next" and chat.isSent:
                #                 # day = NextTenDay.objects.filter(chat=chat.id).first()
                #                 chat.isSent = True
                #                 chat.save()
                #                 url = f"https://chatbot.ics.me/get-first-ten-days/?date={day.day_end}&key={question['key']}"
                #                 response = requests.get(url , headers=headers)
                #                 result = response.json()
                #                 chat.update_state(question['id'])
                #                 ch = next(iter(result.values()))
                #                 if len(ch) >= 9:
                #                     ch.append('next')
                #                     day.day_end = ch[-2]
                #                 day.day = ch[0]
                #                 day.save()
                #                 send_message(message_content=question['day-message'],
                #                         choices = ch,
                #                         type='interactive',
                #                         interaction_type='button',
                #                         to=chat.conversation_id,
                #                         bearer_token=client.token,
                #                         wa_id=client.wa_id,
                #                         chat_id=chat.id,
                #                         platform=platform,
                #                         question=question
                #                     )
                #                 return Response({"Message" : "BOT has interacted successfully."},status=status.HTTP_200_OK)                            

                            
                #             attr, created = Attribute.objects.get_or_create(key='day', chat_id=chat.id)
                #             attr.value = user_reply
                #             attr.save()
                #             next_question_id = question['id']
                #             chat.isSent = False
                #             chat.save()
                #     elif not hour or hour == None:
                #         if not chat.isSent:
                #             chat.isSent = True
                #             chat.save()
                #             url = f"https://chatbot.ics.me/get-hours-free/?date={day.value}&key={question['key']}"
                #             response = requests.get(url , headers=headers)
                #             result = response.json()
                #             chat.update_state(question['id'])
                #             choices = next(iter(result.values()))
                #             try:
                #                 ch = choices[:9]
                #                 ch.append('next')
                #                 NextTime.objects.create(chat=chat, time=ch[-2])
                #             except:
                #                 ch=choices
                #             send_message(message_content=question['appointment-message'],
                #                     choices = ch,
                #                     type='interactive',
                #                     interaction_type='button',
                #                     to=chat.conversation_id,
                #                     bearer_token=client.token,
                #                     wa_id=client.wa_id,
                #                     chat_id=chat.id,
                #                     platform=platform,
                #                     question=question
                #                 )
                #             return Response({"Message" : "BOT has interacted successfully."},status=status.HTTP_200_OK)
                #         else:
                #             time_day = NextTime.objects.filter(chat=chat.id).first()
                #             url = f"https://chatbot.ics.me/get-hours-free/?date={day.value}&key={question['key']}"
                #             response = requests.get(url , headers=headers)
                #             result = response.json()
                #             choices = next(iter(result.values()))
                #             choices.append('next')
                #             user_reply = request.data['content']
                #             if user_reply not in choices:
                #                 error_message = question['error-Message']
                #                 send_message(message_content=error_message,
                #                                 to=chat.conversation_id,
                #                                 bearer_token=client.token,
                #                                 wa_id=client.wa_id,
                #                                 chat_id=chat.id,
                #                                 platform=platform,
                #                                 question=question)
                #                 return Response(
                #                     {"Message" : "BOT has interacted successfully."},
                #                     status=status.HTTP_200_OK
                #                 )
                #             if user_reply == "next" and chat.isSent:
                #                 chat.isSent = True
                #                 chat.save()
                #                 url = f"https://chatbot.ics.me/get-hours-free/?date={day.value}&key={question['key']}"
                #                 response = requests.get(url , headers=headers)
                #                 result = response.json()
                #                 chat.update_state(question['id'])
                #                 choices = next(iter(result.values()))
                #                 try:
                #                     print(str(time_day.time)[:-3])
                #                     index_time = choices.index(str(time_day.time)[:-3])
                #                     print(index_time)
                #                     ch = choices[index_time:index_time+9]
                #                     time_day.time = ch[-2]
                #                     time_day.save()
                #                 except:
                #                     ch = choices
                #                 send_message(message_content=question['appointment-message'],
                #                         choices = ch,
                #                         type='interactive',
                #                         interaction_type='button',
                #                         to=chat.conversation_id,
                #                         bearer_token=client.token,
                #                         wa_id=client.wa_id,
                #                         chat_id=chat.id,
                #                         platform=platform,
                #                         question=question
                #                     )
                #                 return Response({"Message" : "BOT has interacted successfully."},status=status.HTTP_200_OK) 
                #             user_reply = request.data['content']
                #             attr, created = Attribute.objects.get_or_create(key='hour', chat_id=chat.id)
                #             attr.value = user_reply
                #             attr.save()
                #             next_question_id = question['id']
                #             chat.isSent = False
                #             chat.save()
                #     else:
                #         calendar = Calendar.objects.get(key=question['key'])
                #         duration = calendar.duration
                #         user = calendar.user
                #         print(user.id)
                #         data = {
                #             "user":user.id,
                #             "day":day.value,
                #             "duration":f"{duration}",
                #             "hour":f"{hour.value}",
                #             "details":f"{question['parameters'][1]['value']}",
                #             "patientName":f"{question['parameters'][0]['value']}"
                #         } 
                #         url = "https://chatbot.ics.me/create-book-an-appointment/"
                #         response = requests.post(url , headers=headers, json=data)

                #         for option in choices_with_next:
                #             for state in option:
                #                 if str(response.status_code) == str(state):
                #                     next_question_id = option[1]
                #         day.delete()
                #         hour.delete()
                #         NextTenDay.objects.get(chat=chat).delete()
                #         NextTime.objects.get(chat=chat).delete()
                # for handle api in flow
                elif r_type == 'api':
                        url = question['url']
                        headers = {
                                'Content-Type': 'application/json',
                            }
                        
                        data = question['body']
                        for key, value in data.items():
                            if isinstance(value, (int, float)):
                                continue
                            data[key] = change_occurences(value, pattern=r'\{\{(\w+)\}\}', chat_id=chat.id, sql=True)

                        response = requests.post(url , headers=headers, json=data)
                        for option in choices_with_next:
                            for state in option:
                                if str(response.status_code) == str(state):
                                    next_question_id = option[2]
                
                elif r_type == 'name' or \
                    r_type == 'phone' or \
                    r_type == 'email' or \
                    r_type == 'question' or \
                    r_type == 'number' :

                    if not chat.isSent:
                        chat.isSent = True
                        chat.save()
                
                        send_message(message_content=message,
                                        to=chat.conversation_id,
                                        bearer_token=channel.tocken,
                                        wa_id=channel.phone_number_id,
                                        chat_id=chat.id,
                                        platform=platform,
                                        question=question)
                
                        return Response(
                            {"Message" : "BOT has interacted successfully."},
                            status=status.HTTP_200_OK
                        )
                
                    else:
                        user_reply = ''
                    
                        try:
                            user_reply = data['content'] #If this raises an error then it means that the response has come from Beam not Whatsapp
                    
                        except:
                            
                            try: #If this raises an error then this means that it is a beam user reply not normal beam text message reply
                                user_reply = data['entry'][0]['changes'][0]['value']['messages'][0]['text']['body']
                            
                            except:
                                user_reply = data['entry'][0]['changes'][0]['value']['messages'][0]['reply_to']['button_title']
                        
                        restart_keywords = [r.keyword for r in RestartKeyword.objects.filter(channel_id = channel.channle_id)]
                        
                        if user_reply in restart_keywords:
                            chat.isSent = False
                            chat.save()
                            chat.update_state('start')
                            
                        elif r_type == 'name' and len(user_reply) > question['maxRange']:
                            error_message = question['message']['error']
                            send_message(message_content=error_message,
                                            to=chat.conversation_id,
                                            bearer_token=channel.tocken,
                                            wa_id=channel.phone_number_id,
                                            chat_id=chat.id,
                                            platform=platform,
                                            question=question)
                            return Response(
                                {"Message" : "BOT has interacted successfully."},
                                status=status.HTTP_200_OK
                            )
                        
                        elif r_type == 'phone' and not validate_phone_number(user_reply):
                            error_message = question['message']['error']
                            send_message(message_content=error_message,
                                            to=chat.conversation_id,
                                            bearer_token=channel.tocken,
                                            wa_id=channel.phone_number_id,
                                            chat_id=chat.id,
                                            platform=platform,
                                            question=question)
                            return Response(
                                {"Message" : "BOT has interacted successfully."},
                                status=status.HTTP_200_OK
                            )
                        
                        elif r_type == 'email' and not validate_email(user_reply):
                            error_message = question['message']['error']
                            send_message(message_content=error_message,
                                            to=chat.conversation_id,
                                            bearer_token=channel.tocken,
                                            wa_id=channel.phone_number_id,
                                            chat_id=chat.id,
                                            platform=platform,
                                            question=question)
                            return Response(
                                {"Message" : "BOT has interacted successfully."},
                                status=status.HTTP_200_OK
                            )
                        
                        elif r_type == 'number' and not str(user_reply).isdigit():
                            error_message = question['message']['error']
                            send_message(message_content=error_message,
                                            to=chat.conversation_id,
                                            bearer_token=channel.tocken,
                                            wa_id=channel.phone_number_id,
                                            chat_id=chat.id,
                                            platform=platform,
                                            question=question)
                            return Response(
                                {"Message" : "BOT has interacted successfully."},
                                status=status.HTTP_200_OK
                            )
                        
                        else:
                            # add attribute name 
                            # attr, created = Attribute.objects.get_or_create(key=r_type, chat_id=chat.id)
                            attr, created = Attribute.objects.get_or_create(key=attribute_name, chat_id=chat.id)
                            attr.value = user_reply
                            chat.update_state(next_question_id)
                            chat.isSent = False
                            attr.save()
                            chat.save()
                
                elif r_type == 'document':
                    send_message(message_content=message,
                                    to=chat.conversation_id,
                                    bearer_token=channel.tocken,
                                    type='document',
                                    source=question['source'],
                                    beem_media_id=question.get('beem_media_id'),
                                    wa_id=channel.phone_number_id,
                                    chat_id=chat.id,
                                    platform=platform,
                                    question=question)
                
                elif r_type == 'image':
                    send_message(message_content=message,
                                    to=chat.conversation_id,
                                    bearer_token=channel.tocken,
                                    wa_id=channel.phone_number_id,
                                    type='image',
                                    source=question['source'],
                                    beem_media_id=question.get('beem_media_id'), 
                                    chat_id=chat.id,
                                    platform=platform,
                                    question=question)

                
                elif r_type == 'audio' or r_type == 'sticker' or r_type == 'video':

                    send_message(message_content=message,
                                    to=chat.conversation_id,
                                    bearer_token=channel.tocken,
                                    wa_id=channel.phone_number_id,
                                    type=r_type,
                                    source=question['source'], 
                                    chat_id=chat.id,
                                    platform=platform,
                                    question=question)

                
                elif r_type == 'contact' or r_type == 'location':
                    send_message(message_content=message,
                                    to=chat.conversation_id,
                                    bearer_token=channel.tocken,
                                    wa_id=channel.phone_number_id,
                                    type=r_type,
                                    chat_id=chat.id,
                                    platform=platform,
                                    question=question)

                
                
                elif r_type == 'Condition' and choices_with_next or r_type == 'condition' and choices_with_next:
                    
                    for c in choices_with_next:
                        condition = c[0][0]
                        default_state = ''
                        condition = change_occurences(condition, pattern=r'\{\{(\w+)\}\}', chat_id=chat.id, sql=True)
                    
                        if not condition == 'Default':
                    
                            if check_sql_condition(condition):
                                next_question_id = c[3]
                                break
                    
                        else:
                            default_state = c[3]
                    
                    if not next_question_id in [c[3] for c in choices_with_next]: #This means if the next question wasn't changed with any conditions then it'll take the default value
                        next_question_id = default_state
                elif r_type == 'detect_language':
                    pass    
                else:
                    # if chat.state == 'start':
                    #     print(detect(request.data['content']))
                    send_message(message_content=message,
                                    to=chat.conversation_id,
                                    bearer_token=channel.tocken,
                                    wa_id=channel.phone_number_id,
                                    chat_id=chat.id,
                                    platform=platform,
                                    question=question,
                                    )
                
                chat.update_state(next_question_id)
                if not next_question_id or next_question_id == 'end':
                    return True
        else:
            return False