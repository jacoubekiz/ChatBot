from email import message
import json
import requests
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from django.utils import timezone
from api.Contact.models_contact import Conversation, ChatMessage
from api.Channel.models_channel import Channle
from .consumer_constants import MessageType, ContentType, WhatsAppAPI
from api.utils import send_message
from django.shortcuts import get_object_or_404


class MessageHandlers:
    """Handles different types of messages in the chat consumer."""
    
    def __init__(self, consumer):
        self.consumer = consumer
    
    async def handle_text_message(self, data: dict) -> None:
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
                user=self.consumer.user,
                content_type=ContentType.TEXT,
                content=data["content"],
                whatsapp_message_id=whatsapp_message_id
            )

            await self._broadcast_message({
                **data,
                "wamid": whatsapp_message_id,
                "message_id": f'{message_id.message_id}',
                "contact_id": await self.get_contact_id(message_id.message_id),
                "status_message": "sent"
            })

        except Exception as error:
            # Store failed message in database with error details
            await self._create_failed_message(
                conversation_id=await self._get_conversation(data["conversation_id"]),
                user=self.consumer.user,
                content_type=ContentType.TEXT,
                content=data["content"],
                error_message=str(error)
            )
            await self._send_error_message(str(error))

    async def handle_message_status(self, data: dict) -> None:
        """Handle message status updates."""
        await self.consumer.channel_layer.group_send(self.consumer.room_group_name, {
            "type": MessageType.MESSAGE_STATUS,
            "conversation_id": data["conversation_id"],
            "message_id": data["message_id"],
            "status_message": data["status"],
            "content_type":"message_status"
        })

    async def handle_template_message(self, data: dict) -> None:
        """Handle WhatsApp template messages."""
        # try:
        channel = await self._get_channel(data['channel_id'])

        response = await sync_to_async(requests.post)(
            f"{WhatsAppAPI.BASE_URL}/{channel.phone_number_id}/messages",
            headers={
                "Authorization": f"Bearer {channel.tocken}",
                "Content-Type": "application/json"
            },
            data=json.dumps(data["template_info"])
        )

        response_data = await sync_to_async(response.json)()
        if 'messages' in response_data:
            whatsapp_message_id = response_data['messages'][0]['id']

            message_id = await self._create_chat_message(
                conversation_id=await self._get_conversation(data["conversation_id"]),
                user=self.consumer.user,
                content_type=data["content_type"],
                content=data["content"],
                whatsapp_message_id=whatsapp_message_id
            )

            await self._broadcast_message({
                **data,
                "wamid": whatsapp_message_id,
                "message_id": message_id.message_id,
                "contact_id": await self.get_contact_id(message_id.message_id),
                "status_message": "sent"
            })
        else:
            error_message = response_data.get('error', {}).get('message', 'Unknown error')
        # Store failed message in database with error details
            await self._create_failed_message(
                conversation_id=await self._get_conversation(data["conversation_id"]),
                user=self.consumer.user,
                content_type=data["content_type"],
                content=data["content"],
                error_message=error_message
            )
            await self._send_error_message(str(error_message))

    async def _broadcast_message(self, payload: dict) -> None:
        """Broadcast message to all channel members."""
        if payload["from_bot"] == "True":
            payload.update({"content_type":"message_status"})
        await self.consumer.channel_layer.group_send(
            self.consumer.room_group_name,
            {
                "type": MessageType.CHAT_MESSAGE,
                "conversation_state":await self._get_conversation_state(payload["conversation_id"]),
                **payload
            }
        )

    async def _send_error_message(self, error_message: str) -> None:
        """Send error message to client."""
        await self.consumer.send(json.dumps({
            "type": MessageType.ERROR,
            "message": error_message
        }))

    @database_sync_to_async
    def _get_channel(self, channel_id: str):
        """Retrieve channel by ID."""
        return Channle.objects.get(channle_id=channel_id)

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
    def _create_failed_message(self, conversation_id, user, content_type: str,
                                content: str, error_message: str, from_message = "bot") -> int:
        """Create a failed chat message record with error details."""
        return ChatMessage.objects.create(
            conversation_id=conversation_id,
            user_id=user,
            content_type=content_type,
            content=content,
            wamid="failed",
            from_message=from_message,
            error_message=error_message,
            status_message="failed"
        )

    @database_sync_to_async
    def get_contact_id(self, messgae_id):
        message_id = get_object_or_404(ChatMessage, message_id = messgae_id)
        return message_id.conversation_id.contact_id.contact_id