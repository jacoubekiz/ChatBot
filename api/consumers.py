import json
import base64
import os
import urllib.parse as url_parser

import requests
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.files.storage import default_storage
from django.utils import timezone
import urllib.parse as up
import langid

from .models import *
from .serializers import *
from .utils import *



# =========================
# Constants
# =========================

class MessageType:
    MESSAGE = "message"
    CONVERSATION = "conversation"
    ERROR = "error"
    MESSAGE_STATUS = "chat_message_status"
    CHAT_MESSAGE = "chat_message"


class ContentType:
    BOT_INTEGRATION = "bot_integration"
    MESSAGE_STATUS = "message_status"
    TEMPLATE = "template"
    AUDIO = "audio"
    IMAGE = "image"
    TEXT = "text"
    DOCUMENT = "document"
    VIDEO = "video"

class ContentTypeBot:
    SMART_QUESTION = "smart_question"
    API = "api"
    NAME = "name"
    PHONE = "phone"
    EMAIL = "email"
    LIVE_CHAT = "live_chat"
    QUESTION = "question"
    NUMBER = "number"
    DOCUMENT = "document"
    IMAGE = "image"

class MediaType:
    AUDIO = "audio"
    IMAGE = "image"
    DOCUMENT = "document"
    VIDEO = "video"


class WhatsAppAPI:
    BASE_URL = "https://graph.facebook.com/v22.0"
    MEDIA_URL = "https://chatapi.icsl.me/media/chat_message/"


# =========================
# Utility Functions
# =========================

def create_websocket_payload(**kwargs) -> str:
    """Create a standardized WebSocket payload."""
    return json.dumps({
        "type": MessageType.MESSAGE,
        "is_successfully": "true",
        **kwargs
    })


def safe_nested_get(data: dict, *keys, default=None):
    """Safely get nested dictionary values."""
    try:
        for key in keys:
            data = data[key]
        return data
    except (KeyError, TypeError, IndexError):
        return default


# =========================
# Main Consumer
# =========================

class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for handling chat messages, media, and bot interactions.
    """

    # =========================
    # Connection Lifecycle
    # =========================

    async def connect(self) -> None:
        """Handle new WebSocket connection."""
        self.channel_id = self.scope["url_route"]["kwargs"]["channel_id"]
        self.room_group_name = f"chat_{self.channel_id}"
        self.user = self.scope['user']

        # Parse query parameters
        query_string = self.scope['query_string'].decode()
        query_params = dict(url_parser.parse_qsl(query_string))
        self.is_from_bot = query_params.get('from_bot')

        if self.user and self.user.is_authenticated:
            await self._handle_authenticated_connection()
        elif self.is_from_bot == 'False':
            await self._handle_unauthenticated_bot_connection()
        else:
            await self.close()

    async def disconnect(self, close_code: int) -> None:
        """Handle WebSocket disconnection."""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def _handle_authenticated_connection(self) -> None:
        """Handle connection for authenticated users."""
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        conversations = await self._get_conversations(self.channel_id)

        # Archive stale conversations
        for conversation in conversations:
            last_message = await self._get_last_message(conversation.get('conversation_id'))
            if not last_message or (timezone.now() - last_message.created_at).seconds > 86400:
                await self._archive_conversation(conversation.get('conversation_id'))

        await self.send(json.dumps({
            "type": MessageType.CONVERSATION,
            "conversation": conversations
        }))

    async def _handle_unauthenticated_bot_connection(self) -> None:
        """Handle connection for unauthenticated bot requests."""
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()


    # =========================
    # Channel Layer Event Handlers (CRITICAL FIX)
    # =========================
    
    async def chat_message(self, event: dict) -> None:
        """
        Handler for chat_message events from the channel layer.
        This is called when group_send is used with type="chat_message".
        """
        # Remove the 'type' field to avoid recursion
        event.pop('type', None)
        # Send the message to the WebSocket
        await self.send(json.dumps(event))
    
    async def chat_message_status(self, event: dict) -> None:
        """
        Handler for chat_message_status events from the channel layer.
        """
        event.pop('type', None)
        await self.send(json.dumps(event))


    # =========================
    # Message Reception & Routing
    # =========================

    async def receive(self, text_data: str) -> None:
        """Receive and route incoming WebSocket messages."""
        data = json.loads(text_data)

        content_type = data.get("content_type")
        conversation_id = data.get("conversation_id")
        from_bot = data.get("from_bot")

        # await self._update_conversation_status(conversation_id, from_bot)

        handler_mapping = {
            ContentType.BOT_INTEGRATION: self._handle_bot_integration,
            ContentType.MESSAGE_STATUS: self._handle_message_status,
            ContentType.TEMPLATE: self._handle_template_message,
            ContentType.AUDIO: self._handle_audio_message,
            ContentType.IMAGE: self._handle_image_message,
            ContentType.TEXT: self._handle_text_message,
            ContentType.DOCUMENT: self._handle_document_message,
            ContentType.VIDEO: self._handle_video_message
        }

        handler = handler_mapping.get(content_type)

        if handler:
            await handler(data)
        else:
            await self._send_error_message(f"Unsupported content type: {content_type}")

    # =========================
    # Message Handlers
    # =========================
    async def _handle_text_message(self, data: dict) -> None:
        """Handle text messages."""
        if data["from_bot"] != "True":
            await self._broadcast_message(data)
            return

        try:
            result = await sync_to_async(send_message)(
                message_content=data["content"],
                to=await self._get_phone_number(data["conversation_id"]),
                wa_id=await self._get_whatsapp_account_id(data["conversation_id"]),
                bearer_token=await self._get_channel_token(data["conversation_id"]),
                type=ContentType.TEXT,
                platform="whatsapp"
            )
            
            whatsapp_message_id = result['messages'][0]['id']

            message_id = await self._create_chat_message(
                conversation_id=await self._get_conversation(data["conversation_id"]),
                user=self.user,
                content_type=ContentType.TEXT,
                content=data["content"],
                whatsapp_message_id=whatsapp_message_id
            )

            await self._broadcast_message({
                **data,
                "wamid": whatsapp_message_id,
                "message_id": message_id.message_id,
                "status_message": "sent"
            })

        except Exception as error:
            await self._send_error_message(str(error))

    async def _handle_message_status(self, data: dict) -> None:
        """Handle message status updates."""
        await self.channel_layer.group_send(self.room_group_name, {
            "type": MessageType.MESSAGE_STATUS,
            "conversation_id": data["conversation_id"],
            "message_id": data["message_id"],
            "status_message": data["status"],
            "content_type":"message_status"
        })

    async def _handle_template_message(self, data: dict) -> None:
        """Handle WhatsApp template messages."""
        try:
            channel = await self._get_channel(self.channel_id)

            response = requests.post(
                f"{WhatsAppAPI.BASE_URL}/{channel.phone_number_id}/messages",
                headers={
                    "Authorization": f"Bearer {channel.tocken}",
                    "Content-Type": "application/json"
                },
                data=json.dumps(data["template_info"])
            )

            response_data = response.json()
            whatsapp_message_id = response_data['messages'][0]['id']

            message_id = await self._create_chat_message(
                conversation_id=await self._get_conversation(data["conversation_id"]),
                user=self.user,
                content_type=data["content_type"],
                content=data["content"],
                whatsapp_message_id=whatsapp_message_id
            )

            await self._broadcast_message({
                **data,
                "wamid": whatsapp_message_id,
                "message_id": message_id.message_id,
                "status_message": "sent"
            })

        except Exception as error:
            await self._send_error_message(str(error))

    # =========================
    # Media Handlers
    # =========================

    async def _handle_audio_message(self, data: dict) -> None:
        """Handle audio message."""
        await self._handle_media_message(data, MediaType.AUDIO)

    async def _handle_image_message(self, data: dict) -> None:
        """Handle image message."""
        await self._handle_media_message(data, MediaType.IMAGE)
    
    async def _handle_document_message(self, data: dict) -> None:
        """Handle document message."""
        await self._handle_media_message(data, MediaType.DOCUMENT)
    
    async def _handle_video_message(self, data: dict) -> None:
        """Handle video message."""
        await self._handle_media_message(data, MediaType.VIDEO)

    async def _handle_media_message(self, data: dict, media_type: str) -> None:
        """Generic handler for media messages."""
        if data["from_bot"] != "True":
            await self._broadcast_message(data)
            return

        file_path = await self._save_base64_file(data)

        try:
            result = await sync_to_async(send_message)(
                message_content=data["caption"],
                to=await self._get_phone_number(data["conversation_id"]),
                wa_id=await self._get_whatsapp_account_id(data["conversation_id"]),
                bearer_token=await self._get_channel_token(data["conversation_id"]),
                type=media_type,
                source=file_path,
                chat_id= data["conversation_id"],
                question={"label":data["caption"]},
                platform="whatsapp"
            )
            
            whatsapp_message_id = result['messages'][0]['id']

            message_id = await self._create_chat_media_message(
                conversation_id=await self._get_conversation(data["conversation_id"]),
                user=self.user,
                media_type=media_type,
                caption=data["caption"],
                whatsapp_message_id=whatsapp_message_id,
                file_path=file_path
            )

            await self._broadcast_message({
                **data,
                "wamid": whatsapp_message_id,
                "message_id": f'{message_id.message_id}',
                "status_message": "sent"
            })

        except Exception as error:
            await self._send_error_message(str(error))

    async def _save_base64_file(self, data: dict) -> str:
        """Save base64 encoded file and return its URL."""
        file_name = data["media_name"]
        file_content = base64.b64decode(data["content"])

        file_path = f"media/chat_message/{file_name}"

        with open(file_path, "wb") as file_handle:
            file_handle.write(file_content)

        return f"{WhatsAppAPI.MEDIA_URL}{file_name}"

    # =========================
    # Bot Integration
    # =========================

    async def reset_flow(self, channel, source_id, conversation_id, wamid, content, contact_name):
        reset_flow = False
        restart_keyword = await database_sync_to_async(list)(RestartKeyword.objects.filter(channel_id=channel.channle_id))
        for rest in restart_keyword:
            if rest.keyword == content:
                reset_flow = True
                print(f"{source_id}-------{channel}------{await self._get_default_flow(rest)}")
                ch = await self._update_chat_for_restart(source_id, channel, await self._get_default_flow(rest))
                if ch:
                    message_id = await self._create_chat_message(
                        conversation_id=await self._get_conversation(conversation_id),
                        user=None,
                        content_type=ContentType.TEXT,
                        content=content,
                        whatsapp_message_id=wamid,
                        from_message=contact_name
                    )

                    # Send the message to the channel layer
                    await self._broadcast_message_flow(
                        {
                            "phoneNumber":await self._get_phone_number(conversation_id),
                            "conversation_id": conversation_id,
                            "content":content,
                            "content_type":"text",
                            "wamid": wamid,
                            "created_at": f"{message_id.created_at}",
                            "wamid":wamid,
                            "message_id": message_id.message_id,
                            "from_bot":"False",
                            "status_message": "sent"
                        }
                    )
                    await database_sync_to_async(ch.update_state)('start')
                    ch.isSent = False
                    await database_sync_to_async(ch.save)()    
            else:
                ch = await self._get_chat(source_id, channel)        # break
        return reset_flow== True, ch

    async def _get_flow_by_trigger(self, channel, content, source_id):
        try:
            flow = await database_sync_to_async(channel.flows.get)(trigger__trigger=content)
            chats = await database_sync_to_async(list)(Chat.objects.filter(
                Q(conversation_id=source_id) & 
                Q(channel_id=channel.channle_id) & 
                ~Q(flow=flow)
            ))
            for c in chats:
                await database_sync_to_async(c.update_state)('end')
                c.isSent = False
                await database_sync_to_async(c.save)()
        except:
            ch = await database_sync_to_async(
                lambda: Chat.objects.filter(
                    Q(conversation_id=source_id) & 
                    Q(channel_id=channel.channle_id) & 
                    ~Q(state='end')
                ).first()
            )()
            if ch:
                flow = await database_sync_to_async(lambda: ch.flow)()
            else:
                flow = None
        return flow
    
    async def _retype_content_list_or_button(self, content, channel, question, chat, r_type, choices, platform, message, data, choices_with_next, attribute_name, conversation_id, contact_name):
        if not chat.isSent:
            chat.isSent = True
            await database_sync_to_async(chat.save)()

            if r_type == 'list':
                message_wamid = await sync_to_async(send_message)(
                    message_content=message,
                    choices=choices,
                    type='interactive', 
                    interaction_type='list',
                    footer=question['footer'],
                    header=question['header'],
                    to=chat.conversation_id,
                    bearer_token=channel.tocken,
                    wa_id=channel.phone_number_id,
                    chat_id=chat.id,
                    platform=platform,
                    question=question
                )
            else:
                message_wamid = await sync_to_async(send_message)(
                    message_content=message,
                    choices=choices,
                    type='interactive', 
                    interaction_type='button',
                    to=chat.conversation_id,
                    bearer_token=channel.tocken,
                    wa_id=channel.phone_number_id,
                    chat_id=chat.id,
                    platform=platform,
                    question=question
                )
                message_id = await self._create_chat_message(
                    conversation_id=await self._get_conversation(conversation_id),
                    user=None,
                    content_type="text",
                    content=message,
                    whatsapp_message_id=message_wamid['messages'][0]['id'],
                )
                await self._broadcast_message_flow({
                    "conversation_id": conversation_id,
                    "phoneNumber":await self._get_phone_number(conversation_id),
                    "content": message,
                    "created_at": f"{message_id.created_at}",
                    "content_type": "text",
                    "wamid": message_wamid['messages'][0]['id'],
                    "message_id": message_id.message_id,
                    "from_bot":"True",
                    "status_message": "sent"
            })
            return True
            
        else:
            user_reply = content
            if user_reply not in choices or user_reply == '':
                error_message = question['message']['error']
                
                message_wamid = await sync_to_async(send_message)(
                    message_content=error_message,
                    to=chat.conversation_id,
                    bearer_token=channel.tocken,
                    wa_id=channel.phone_number_id,
                    chat_id=chat.id,
                    platform=platform,
                    question=question
                )

                message_id = await self._create_chat_message(
                    conversation_id=await self._get_conversation(data["conversation_id"]),
                    user=None,
                    content_type="text",
                    content=message,
                    whatsapp_message_id="sdflskjdflksjdf",
                    from_message=contact_name

                )
                await self._broadcast_message_flow(
                    {
                        "phoneNumber":await self._get_phone_number(conversation_id),
                        "conversation_id": conversation_id,
                        "content":message,
                        "content_type":"text",
                        "wamid": "wamid",
                        "created_at": f"{message_id.created_at}",
                        "message_id": message_id.message_id,
                        "from_bot":"True",
                        "status_message": "sent"
                    }
                )
                return True
                
            else:
                message_id = await self._create_chat_message(
                    conversation_id=await self._get_conversation(data["conversation_id"]),
                    user=None,
                    content_type="text",
                    content=user_reply,
                    whatsapp_message_id="sdflskjdflksjdf",
                    from_message=contact_name
                )
            
                # Send message through WebSocket
                await self._broadcast_message_flow(
                    {
                        "phoneNumber":await self._get_phone_number(conversation_id),
                        "conversation_id": conversation_id,
                        "content":content,
                        "content_type":"text",
                        "wamid": "wamid",
                        "created_at": f"{message_id.created_at}",
                        "message_id": message_id.message_id,
                        "from_bot":"False",
                        "status_message": "sent"
                    }
                )
                account = await self._get_account(self.channel_id)
                await self._create_attribute(attribute_name, user_reply, chat, account)
                next_question_id = [c[2] for c in choices_with_next if user_reply == c[0]][0]
                await self._update_chat_status(chat, next_question_id)

    # handle api type question
    async def _retype_api(self, question, chat, choices_with_next):
        api_name = question['name']
        api_ = await self._get_api_info(api_name)
        headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {await api_.tocken}'
        }

        data = api_.body
        endpoint = api_.endpoint
        try:
            for key, value in data.items():
                if isinstance(value, (int, float)):
                    continue
            data[key] = change_occurences(value, pattern=r'\{\{(\w+)\}\}', chat_id=chat.id, sql=True)
        except:
            data = {}
        response = requests.post(endpoint , headers=headers, json=data)
        for option in choices_with_next:
            for state in option:
                if str(response.status_code) == str(state):
                    next_question_id = option[2]
                    await database_sync_to_async(chat.update_state)(next_question_id)
                    chat.isSent = False
                    await database_sync_to_async(chat.save)()

    # handle name and phone and email type question
    async def _retype_name_phone_email_question(self, question, chat,channel, content,r_type, next_question_id, platform, message, data, attribute_name, conversation_id, contact_name):
        if not chat.isSent:
            chat.isSent = True
            await database_sync_to_async(chat.save)()
            message_wamid = send_message(message_content=message,
                            to=chat.conversation_id,
                            bearer_token=channel.tocken,
                            wa_id=channel.phone_number_id,
                            chat_id=chat.id,
                            platform=platform,
                            question=question)
            message_id = await self._create_chat_message(
                conversation_id=await self._get_conversation(conversation_id),
                user=None,
                content_type="text",
                content=message,
                whatsapp_message_id=message_wamid['messages'][0]['id']
                )
            await self._broadcast_message_flow({
                "conversation_id": conversation_id,
                "phoneNumber":await self._get_phone_number(conversation_id),
                "content": message,
                "created_at": f"{message_id.created_at}",
                "content_type": "text",
                "wamid": message_wamid['messages'][0]['id'],
                "message_id": message_id.message_id,
                "from_bot":"True",
                "status_message": "sent"
            })
            return True
        else:
            user_reply = content

            if r_type == 'name' and len(user_reply) > question['maxRange'] or\
            r_type == 'phone' and not validate_phone_number(user_reply) or\
            r_type == 'email' and not validate_email(user_reply) or\
            r_type == 'number' and not str(user_reply).isdigit():
                error_message = question['message']['error']
                message_wamid = send_message(message_content=error_message,
                            to=chat.conversation_id,
                            bearer_token=channel.tocken,
                            wa_id=channel.phone_number_id,
                            chat_id=chat.id,
                            platform=platform,
                            question=question)
                message_id = await self._create_chat_message(
                    conversation_id=await self._get_conversation(data["conversation_id"]),
                    user=None,
                    content_type="text",
                    content=error_message,
                    whatsapp_message_id=message_wamid['messages'][0]['id'],
                )
                await self._broadcast_message_flow({
                    "conversation_id": conversation_id,
                    "phoneNumber":await self._get_phone_number(conversation_id),
                    "content": user_reply,
                    "created_at": f"{message_id.created_at}",
                    "content_type": "text",
                    "wamid": message_wamid['messages'][0]['id'],
                    "message_id": message_id.message_id,
                    "from_bot":"True",
                    "status_message": "sent"
                })
                return True
            else:
                message_id = await self._create_chat_message(
                    conversation_id=await self._get_conversation(data["conversation_id"]),
                    user=None,
                    content_type="text",
                    content=user_reply,
                    whatsapp_message_id="sdflskjdflksjdf",
                    from_message=contact_name
                )
                await self._broadcast_message_flow(
                    {
                        "phoneNumber":await self._get_phone_number(conversation_id),
                        "conversation_id": conversation_id,
                        "content":user_reply,
                        "content_type":"text",
                        "wamid": "wamid",
                        "created_at": f"{message_id.created_at}",
                        "message_id": message_id.message_id,
                        "from_bot":"False",
                        "status_message": "sent"
                    }
                )
                account = await self._get_account(self.channel_id)
                await self._create_attribute(attribute_name, user_reply, chat, account)
                await self._update_chat_status(chat, next_question_id)


    async def _retype_document(self, channel, chat, question, message, platform, conversation_id, data, next_question_id):
        message_wamid = send_message(message_content=message,
                        to=chat.conversation_id,
                        bearer_token=channel.tocken,
                        type='document',
                        source=question['source'],
                        beem_media_id=question.get('beem_media_id'),
                        wa_id=channel.phone_number_id,
                        chat_id=chat.id,
                        platform=platform,
                        question=question)
        message_id = await self._create_chat_media_message(
            conversation_id= await self._get_conversation(conversation_id),
            user=None,
            media_type="document",
            caption=message or "",
            whatsapp_message_id=message_wamid['messages'][0]['id'],
            file_path= question['source'],
        )
        await self._broadcast_message_flow({
            "conversation_id": conversation_id,
            "phoneNumber":await self._get_phone_number(conversation_id),
            "content": message,
            "created_at": f"{message_id.created_at}",
            "content_type": "document",
            "wamid": message_wamid['messages'][0]['id'],
            "message_id": message_id.message_id,
            "from_bot":"True",
            "status_message": "sent"
        })
        await self._update_chat_status(chat, next_question_id)

    async def _retype_image(self, message, chat, channel, question, platform, conversation_id, data, next_question_id):
        message_wamid = send_message(message_content=message,
            to=chat.conversation_id,
            bearer_token=channel.tocken,
            wa_id=channel.phone_number_id,
            type='image',
            source=question['source'],
            beem_media_id=question.get('beem_media_id'), 
            chat_id=chat.id,
            platform=platform,
            question=question
        )
        message_id = await database_sync_to_async(ChatMessage.objects.create)(
            conversation_id= await self._get_conversation(conversation_id),
            user=None,
            media_type="image",
            caption=message or "",
            whatsapp_message_id=message_wamid['messages'][0]['id'],
            file_path= question['source'],
        )
        await self._broadcast_message_flow({
             "conversation_id": conversation_id,
            "content": message,
            "phoneNumber":await self._get_phone_number(conversation_id),
            "created_at": f"{message_id.created_at}",
            "content_type": "image",
            "wamid": message_wamid['messages'][0]['id'],
            "message_id": message_id.message_id,
            "from_bot":"True",
            "status_message": "sent"
            })
        await self._update_chat_status(chat, next_question_id)
        

    async def _retype_audio_vedio_steker(self, message, chat, channel, question, platform, r_type, conversation_id, data, next_question_id):
        message_wamid = send_message(message_content=message,
                to=chat.conversation_id,
                bearer_token=channel.tocken,
                wa_id=channel.phone_number_id,
                type=r_type,
                source=question['source'], 
                chat_id=chat.id,
                platform=platform,
                question=question)
        message_id = await self._create_chat_media_message(
            conversation_id= await self._get_conversation(conversation_id),
            user=None,
            media_type=r_type,
            caption=message or "",
            whatsapp_message_id=message_wamid['messages'][0]['id'],
            file_path= question['source'],
        )
        await self._broadcast_message_flow({
            "conversation_id": conversation_id,
            "phoneNumber":await self._get_phone_number(conversation_id),
            "content": message,
            "created_at": f"{message_id.created_at}",
            "content_type": "audio",
            "wamid": message_wamid['messages'][0]['id'],
            "message_id": message_id.message_id,
            "from_bot":"True",
            "status_message": "sent"
        })
        await self._update_chat_status(chat, next_question_id)

    async def _retype_live_chat(self, message, chat, channel, question, platform, conversation_id, data):
        message_wamid = send_message(message_content=message,
                to=chat.conversation_id,
                bearer_token=channel.tocken,
                wa_id=channel.phone_number_id,
                chat_id=chat.id,
                platform=platform,
                question=question,
                )
        message_id = await self._create_chat_message(
            conversation_id=await self._get_conversation(conversation_id),
            user= None,
            content_type="text",
            content=message,
            whatsapp_message_id=message_wamid['messages'][0]['id']
        )
        await self._update_state_conversation(conversation_id)
        await self._broadcast_message_flow({
            "conversation_id": conversation_id,
            "phoneNumber":await self._get_phone_number(conversation_id),
            "content": message,
            "created_at": f"{message_id.created_at}",
            "content_type": "text",
            "wamid": message_wamid['messages'][0]['id'],
            "message_id": message_id.message_id,
            "from_bot":"True",
            "status_message": "sent"
            }
        )
        return "end"

    async def _retype_redirect_flow(self, next_question_id, source_id, channel, chat):
        flow = await self._get_flow(next_question_id)
        file_path = await database_sync_to_async(default_storage.path)(flow.flow.name)
        chat_flow = await sync_to_async(read_json)(file_path)
        # await self._delete_chat(chat)
        if chat_flow and source_id:
            chat = await self._update_chat_status_flow(chat, flow)
            questions = chat_flow['payload']['questions']
            # if not bool(chat.state) or chat.state == 'end' or chat.state == '':
            await database_sync_to_async(chat.update_state)('start')

        return questions, chat, flow
    
    async def _handle_bot_integration(self, data: dict) -> None:
        """Handle bot integration and flow processing."""

        wamid = data.get("data", {}).get('wamid', '')
        content = data.get("data", {}).get('content', '')
        contact_name = data.get('contact_name', '')
        conversation_id = data.get("conversation_id")
        source_id = data.get("data", {}).get("source_id")
        platform = 'whatsapp'
        channel = await self._get_channel(self.channel_id)

        flow = await self._get_flow_by_trigger(channel, content, source_id)
        reset_flow_, ch = await self.reset_flow(channel, source_id, conversation_id, wamid, content, contact_name)
                
        if not flow:
            flow = await database_sync_to_async(channel.flows.get)(is_default=True)
        
        file_path = await database_sync_to_async(default_storage.path)(flow.flow.name)
        chat_flow = await sync_to_async(read_json)(file_path)
        
    
        if chat_flow and source_id:
            if reset_flow_ == True:
                chat = ch
            else:
                chat = await self._get_chat(source_id, channel)
            
            questions = chat_flow['payload']['questions']
            
            if not bool(chat.state) or chat.state == 'end' or chat.state == '':
                await database_sync_to_async(chat.update_state)('start')
            while True:
                next_question_id = None
                if chat.state == 'start':
                    if reset_flow_ == True:
                        question = questions[0]
                        if question['type'] == 'detect_language':
                            question = questions[int(questions.index(questions[0]) + 1)]
                    else:
                        question = questions[0]
                        
                else:
                    for item in questions:
                        if item['id'] == chat.state:
                            question = item
                            break
                message, next_question_id, choices_with_next, choices, r_type, attribute_name = await sync_to_async(show_response)(question, questions)
                # if next_question_id == "end":
                #     break
                
                if r_type == 'detect_language':
                    lang = await sync_to_async(langid.classify)(data['content'])
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
                    
                    state_ = await self._retype_content_list_or_button(content, channel, question, chat, r_type, choices, platform, message, data, choices_with_next, attribute_name, conversation_id, contact_name)
                    if state_:
                        return True
                    continue
                # ... continue with other r_type cases following the same pattern ...
                elif r_type == 'live_chat':
                    next_message = await self._retype_live_chat(message, chat, channel, question, platform, conversation_id, data) 
                    next_question_id = next_message
                
                elif r_type == 'redirect':
                    ret_from , chat_, flow= await self._retype_redirect_flow(next_question_id, source_id, channel, chat)
                    questions=ret_from
                    chat = chat_
                    # await self._update_chat_status_flow(chat, questions[0]['id'], flow)
                    continue


                elif r_type == 'smart_question' and choices_with_next:
                    if not chat.isSent:
                        chat.isSent = True
                        await database_sync_to_async(chat.save)()
                        message_wamid = send_message(message_content=message,
                                    to = chat.conversation_id,
                                    bearer_token=channel.tocken,
                                    wa_id=channel.phone_number_id,
                                    chat_id=chat.id,
                                    platform=platform,
                                    question=question)
                        return True
                    else:
                        try:
                            user_reply = data['content'] #If this raises an error then it means that the response has come from Beam not Whatsapp                        
                        except:
                            
                            try: #If this raises an error then this means that it is a beam user reply not normal beam text message reply
                                user_reply = data['entry'][0]['changes'][0]['value']['messages'][0]['text']['body']
                            
                            except:
                                user_reply = data['entry'][0]['changes'][0]['value']['messages'][0]['reply_to']['button_title']
                                
                        account = await self.get_account(self.channel_id)
                        attr, created = Attribute.objects.get_or_create(key=attribute_name, chat_id=chat.id, account=account)
                        attr.value = user_reply
                        await database_sync_to_async(attr.save)()
                        
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
                    
                        await database_sync_to_async(chat.update_state)(next_question_id)
                        chat.isSent = False
                        await database_sync_to_async(chat.save)()

                elif r_type == 'api':
                    await self._retype_api()

                elif r_type == 'name' or \
                    r_type == 'phone' or \
                    r_type == 'email' or \
                    r_type == 'question' or \
                    r_type == 'number' :

                    state = await self._retype_name_phone_email_question(question, chat, channel, content, r_type, next_question_id, platform, message, data, attribute_name, conversation_id, contact_name)
                    if state:
                        return True

                elif r_type == 'document':
                    await self._retype_document(channel, chat, question, message, platform, conversation_id, data, next_question_id)

                elif r_type == 'image':
                    await self._retype_image(message, chat, channel, question, platform, conversation_id, data, next_question_id)

                elif r_type == 'audio' or r_type == 'sticker' or r_type == 'video':
                    await self._retype_audio_vedio_steker(message, chat, channel, question, platform, r_type, conversation_id, data, next_question_id)

                elif r_type == 'contact' or r_type == 'location':
                    message_wamid = send_message(message_content=message,
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
                    message_wamid = send_message(message_content=message,
                                    to=chat.conversation_id,
                                    bearer_token=channel.tocken,
                                    wa_id=channel.phone_number_id,
                                    chat_id=chat.id,
                                    platform=platform,
                                    question=question,
                                    )
                    message_id = await self._create_chat_message(
                        conversation_id=await self._get_conversation(conversation_id),
                        user= None,
                        content_type="text",
                        content=message,
                        whatsapp_message_id=message_wamid['messages'][0]['id']
                    )
                    await self._broadcast_message_flow(
                        {
                            "phoneNumber":await self._get_phone_number(conversation_id),
                            "conversation_id": conversation_id,
                            "content":message,
                            "content_type":"text",
                            "wamid": "wamid",
                            "created_at": f"{message_id.created_at}",
                            "message_id": message_id.message_id,
                            "from_bot":"True",
                            "status_message": "sent"
                        }
                    )
                await database_sync_to_async(chat.update_state)(next_question_id)
                if next_question_id == 'end':
                    chat.isSent = False
                    await database_sync_to_async(chat.save)()
                    break

        if not next_question_id or next_question_id == 'end':
            return True
        else:
                return False

    # =========================
    # Broadcasting & Error Handling
    # =========================

    async def _broadcast_message(self, payload: dict) -> None:
        """Broadcast message to all channel members."""
        if payload["from_bot"] == "True":
            payload.update({"content_type":"message_status"})
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": MessageType.CHAT_MESSAGE,
                "conversation_state":await self._get_conversation_state(payload["conversation_id"]),
                **payload
            }
        )
    async def _broadcast_message_flow(self, payload: dict) -> None:
        await self.channel_layer.group_send(
            self.room_group_name,    
            {
                "type": MessageType.CHAT_MESSAGE,
                "conversation_state":await self._get_conversation_state(payload["conversation_id"]),
                **payload
            }
        )
                
    async def _send_error_message(self, error_message: str) -> None:
        """Send error message to client."""
        await self.send(json.dumps({
            "type": MessageType.ERROR,
            "message": error_message
        }))

    # =========================
    # Database Helpers
    # =========================

    @database_sync_to_async
    def _get_channel(self, channel_id: str):
        """Retrieve channel by ID."""
        return Channle.objects.get(channle_id=channel_id)

    @database_sync_to_async
    def _get_or_create_chat(self, source_id: str, channel, flow):
        """Get or create chat record."""
        return Chat.objects.get_or_create(
            conversation_id=source_id,
            channel_id=channel,
            flow=flow
        )[0]

    @database_sync_to_async
    def _update_state_conversation(self, conversation_id: str) -> None:
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        conversation.state = "live_chat"
        conversation.save()
    
    @database_sync_to_async
    def _get_conversation_state(self, conversation_id: str) ->str:
        return Conversation.objects.get(conversation_id=conversation_id).state

    @database_sync_to_async
    def _create_chat_message(self, conversation_id, user, content_type: str,
                             content: str, whatsapp_message_id: str, from_message = "bot") -> int:
        """Create a chat message record and return its ID."""
        return ChatMessage.objects.create(
            conversation_id=conversation_id,
            user_id=user,
            content_type=content_type,
            content=content,
            wamid=whatsapp_message_id,
            from_message=from_message
        )

    @database_sync_to_async
    def _create_chat_media_message(self, conversation_id: str, user, media_type: str,
                                   caption: str, whatsapp_message_id: str,
                                   file_path: str) -> int:
        """Create a media chat message record."""
        return ChatMessage.objects.create(
            conversation_id=conversation_id,
            user_id=user,
            content_type=media_type,
            caption=caption or "",
            wamid=whatsapp_message_id,
            media_url=file_path
        )

    @database_sync_to_async
    def _get_conversations(self, channel_id: str):
        """Get all conversations for a channel."""
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
        pass

    @database_sync_to_async
    def _get_last_message(self, conversation_id: str):
        """Get the last message in a conversation."""
        conversation = Conversation.objects.filter(conversation_id=conversation_id).first()
        message = conversation.chatmessage_set.exclude(from_message ='bot').order_by("-created_at").first()
        return message

    @database_sync_to_async
    def _archive_conversation(self, conversation_id: str) -> None:
        """Archive a conversation."""
        # This method needs to be implemented based on your models
        pass

    @database_sync_to_async
    def _update_chat_status(self, chat, next_question_id) -> None:
        """Update conversation status."""
        chat.update_state(next_question_id)
        chat.isSent = False
        chat.save()

    @database_sync_to_async
    def _get_phone_number(self, conversation_id: str) -> str:
        """Get phone number for a conversation."""
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        phonenumber = conversation.contact_id.phone_number
        return phonenumber

    @database_sync_to_async
    def _get_whatsapp_account_id(self, conversation_id: str) -> str:
        """Get WhatsApp account ID for a conversation."""
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        waid = conversation.channle_id.phone_number_id
        return waid

    @database_sync_to_async
    def _get_channel_token(self, conversation_id: str) -> str:
        """Get channel token for a conversation."""
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        tocken = conversation.channle_id.tocken
        return tocken
    
    @database_sync_to_async
    def _get_conversation(self, conversation_id):
        """Get conversation by ID."""
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        conversation.updated_at = timezone.now()
        conversation.save()
        return conversation
    
    @database_sync_to_async
    def _get_account(self, channel_id):
        """Get account based on channel."""
        channel = Channle.objects.get(channle_id=channel_id)
        return channel.account_id
    
    @database_sync_to_async
    def _create_attribute(self, attribute_name, user_reply, chat, account):
        """Create or update an attribute."""
        attr, created = Attribute.objects.get_or_create(key=attribute_name, chat_id=chat.id, account = account)
        attr.value = user_reply
        attr.save()

    @database_sync_to_async
    def _get_api_info(self, api_name):
        """Get API information by name."""
        return API.objects.get(name=api_name)
    
    @database_sync_to_async
    def _get_flow(self, next_question_id):
        return Flow.objects.get(id=next_question_id)
    
    @database_sync_to_async
    def _get_chat(self, source_id, channel):
        chat, created = Chat.objects.get_or_create(conversation_id=source_id, channel_id=channel)
        return chat

    @database_sync_to_async
    def _update_chat_for_restart(self, source_id, channel, flow):
        chat, created = Chat.objects.get_or_create(conversation_id=source_id, channel_id=channel)
        if chat:
            chat.flow = flow
            chat.state = ''
            chat.isSent = False
            chat.save()
            return chat
        return None

    @database_sync_to_async
    def _delete_chat(self, chat):
        chat.delete()

    @database_sync_to_async
    def _get_default_flow(self, rest):
        return rest.channel_id.flows.filter(is_default=True).first()
    
    @database_sync_to_async
    def _update_chat_status_flow(self, chat, flow) -> None:
        """Update conversation status."""
        chat.flow = flow
        chat.isSent = False
        chat.save()
        return chat