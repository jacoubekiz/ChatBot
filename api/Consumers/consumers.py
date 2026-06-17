import json
import urllib.parse as url_parser
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

from .consumer_constants import MessageType, ContentType
from .consumer_utils import create_websocket_payload, safe_nested_get
from .consumer_message_handlers import MessageHandlers
from .consumer_bot_integration import BotIntegration
from .consumer_media_handlers import MediaHandlers
from .consumer_database_helpers import DatabaseHelpers

class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for handling chat messages, media, and bot interactions.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_handlers = MessageHandlers(self)
        self.bot_integration = BotIntegration(self)
        self.media_handlers = MediaHandlers(self)
        self.db_helpers = DatabaseHelpers(self)

    # =========================
    # Connection Lifecycle
    # =========================

    async def connect(self) -> None:
        """Handle new WebSocket connection."""
        self.room_group_name = f"chat_"
        self.user = self.scope['user']

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

        conversations = await self.db_helpers.get_conversations()

        for conversation in conversations:
            last_message = await self.db_helpers.get_last_message(conversation.get('conversation_id'))
            if not last_message or (timezone.now() - last_message.created_at).seconds > 86400:
                await self.db_helpers.archive_conversation(conversation.get('conversation_id'))

        await self.send(json.dumps({
            "type": MessageType.CONVERSATION,
            "conversation": conversations
        }))

    async def _handle_unauthenticated_bot_connection(self) -> None:
        """Handle connection for unauthenticated bot requests."""
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    # =========================
    # Channel Layer Event Handlers
    # =========================
    
    async def chat_message(self, event: dict) -> None:
        """Handler for chat_message events from the channel layer."""
        event.pop('type', None)
        await self.send(json.dumps(event))
    
    async def chat_message_status(self, event: dict) -> None:
        """Handler for chat_message_status events from the channel layer."""
        event.pop('type', None)
        await self.send(json.dumps(event))

    # =========================
    # Message Reception & Routing
    # =========================

    async def receive(self, text_data: str) -> None:
        """Receive and route incoming WebSocket messages."""
        data = json.loads(text_data)
        content_type = data.get("content_type")

        handler_mapping = {
            ContentType.BOT_INTEGRATION: self.bot_integration.handle_bot_integration,
            ContentType.MESSAGE_STATUS: self.message_handlers.handle_message_status,
            ContentType.TEMPLATE: self.message_handlers.handle_template_message,
            ContentType.AUDIO: self.media_handlers.handle_audio_message,
            ContentType.IMAGE: self.media_handlers.handle_image_message,
            ContentType.TEXT: self.message_handlers.handle_text_message,
            ContentType.DOCUMENT: self.media_handlers.handle_document_message,
            ContentType.VIDEO: self.media_handlers.handle_video_message,
            ContentType.VOICE: self.media_handlers.handle_voice_message,
        }

        handler = handler_mapping.get(content_type)
        if handler:
            await handler(data)
        else:
            await self._send_error_message(f"Unsupported content type: {content_type}")

    async def _send_error_message(self, error_message: str) -> None:
        """Send error message to client."""
        await self.send(json.dumps({
            "type": MessageType.ERROR,
            "message": error_message
        }))
