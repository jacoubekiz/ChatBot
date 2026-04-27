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

        await self._update_conversation_status(conversation_id, from_bot)

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
                "message_id": message_id,
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
            "status_message": data["status"]
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
                "message_id": message_id,
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
            print(f"Media message sent with WhatsApp message ID: {whatsapp_message_id}")

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
                "message_id": message_id,
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

    async def _handle_bot_integration(self, data: dict) -> None:
        """Handle bot integration and flow processing."""
        source_id = (
            safe_nested_get(data, 'data', 'conversation', 'contact_inbox', 'source_id') or
            safe_nested_get(data, 'data', 'entry', 0, 'changes', 0, 'value', 'messages', 0, 'from')
        )

        channel = await self._get_channel(self.channel_id)
        flow = await self._resolve_flow(channel, data)

        if not flow:
            return

        chat = await self._get_or_create_chat(source_id, channel, flow)
        await self._process_bot_flow(chat, flow, data)

    async def _process_bot_flow(self, chat, flow, data: dict) -> None:
        """Process bot flow questions sequentially."""
        file_path = await database_sync_to_async(default_storage.path)(flow.flow.name)
        flow_json = await sync_to_async(read_json)(file_path)

        questions = flow_json['payload']['questions']

        while True:
            current_question = self._get_current_question(chat, questions)

            message, next_question_id, *_ = await sync_to_async(show_response)(
                current_question,
                questions
            )

            await self._send_bot_message(chat, message)
            await database_sync_to_async(chat.update_state)(next_question_id)

            if not next_question_id or next_question_id == "end":
                break

    def _get_current_question(self, chat, questions: list) -> dict:
        """Get the current question based on chat state."""
        if not chat.state or chat.state == "start":
            return questions[0]

        for question in questions:
            if question['id'] == chat.state:
                return question
        return questions[0]

    async def _send_bot_message(self, chat, message: str) -> None:
        """Send a message from the bot."""
        result = await sync_to_async(send_message)(
            message_content=message,
            to=chat.conversation_id,
            bearer_token=chat.channel_id.tocken,
            wa_id=chat.channel_id.phone_number_id,
            platform="whatsapp"
        )

        conversation = await database_sync_to_async(Conversation.objects.get)(
            conversation_id=chat.conversation_id
        )

        await database_sync_to_async(ChatMessage.objects.create)(
            conversation_id=conversation,
            content=message,
            from_message="bot",
            wamid=result['messages'][0]['id']
        )

    # =========================
    # Broadcasting & Error Handling
    # =========================

    async def _broadcast_message(self, payload: dict) -> None:
        """Broadcast message to all channel members."""
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": MessageType.CHAT_MESSAGE, **payload}
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
    def _create_chat_message(self, conversation_id, user, content_type: str,
                             content: str, whatsapp_message_id: str) -> int:
        """Create a chat message record and return its ID."""
        return ChatMessage.objects.create(
            conversation_id=conversation_id,
            user_id=user,
            content_type=content_type,
            content=content,
            wamid=whatsapp_message_id
        ).message_id

    @database_sync_to_async
    def _create_chat_media_message(self, conversation_id: str, user, media_type: str,
                                   caption: str, whatsapp_message_id: str,
                                   file_path: str) -> int:
        """Create a media chat message record."""
        return ChatMessage.objects.create(
            conversation_id=conversation_id,
            user_id=self.user,
            content_type=media_type,
            caption=caption or "",
            wamid=whatsapp_message_id,
            media_url=file_path
        ).message_id

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
    def _update_conversation_status(self, conversation_id: str, from_bot: str) -> None:
        """Update conversation status."""
        # This method needs to be implemented based on your models
        pass

    @database_sync_to_async
    def _resolve_flow(self, channel, data: dict):
        """Resolve which flow to use."""
        # This method needs to be implemented based on your models
        pass

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