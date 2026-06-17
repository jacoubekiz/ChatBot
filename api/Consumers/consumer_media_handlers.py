import base64
from asgiref.sync import sync_to_async
from api.Contact.models_contact import Conversation, ChatMessage
from .consumer_constants import MediaType, ContentType, WhatsAppAPI
from api.utils import send_message, process_and_send_voice_note


class MediaHandlers:
    """Handles media messages in the chat consumer."""
    
    def __init__(self, consumer):
        self.consumer = consumer
    
    async def handle_voice_message(self, data: dict) -> None:
        """Handle audio message."""
        await self._handle_media_message(data, MediaType.VOICE)

    async def handle_audio_message(self, data: dict) -> None:
        """Handle audio message."""
        await self._handle_media_message(data, MediaType.AUDIO)

    async def handle_image_message(self, data: dict) -> None:
        """Handle image message."""
        await self._handle_media_message(data, MediaType.IMAGE)
    
    async def handle_document_message(self, data: dict) -> None:
        """Handle document message."""
        await self._handle_media_message(data, MediaType.DOCUMENT)
    
    async def handle_video_message(self, data: dict) -> None:
        """Handle video message."""
        await self._handle_media_message(data, MediaType.VIDEO)

    async def _handle_media_message(self, data: dict, media_type: str) -> None:
        """Generic handler for media messages."""
        if data["from_bot"] != "True":
            await self._broadcast_message(data)
            return

        file_path = await self._save_base64_file(data)
        try:
            if media_type == 'audio' or media_type == 'voice':
                result = await sync_to_async(process_and_send_voice_note)(
                    file_path, 
                    await self._get_whatsapp_account_id(data["conversation_id"]), 
                    await self._get_channel_token(data["conversation_id"]), 
                    await self._get_phone_number(data["conversation_id"]), 
                    bitrate_kbps=24)
                whatsapp_message_id = result
            else:
                result = await sync_to_async(send_message)(
                    message_content=data["caption"],
                    to=await self._get_phone_number(data["conversation_id"]),
                    wa_id=await self._get_whatsapp_account_id(data["conversation_id"]),
                    bearer_token=await self._get_channel_token(data["conversation_id"]),
                    type=media_type,
                    chat_id= data["conversation_id"],
                    source=f"https://chatapi.icsl.me/media/chat_message/{data["media_name"]}",
                    platform="whatsapp"
                )
                whatsapp_message_id = result['messages'][0]['id']

            message_id = await self._create_chat_media_message(
                conversation_id=await self._get_conversation(data["conversation_id"]),
                user=self.consumer.user,
                media_type=media_type,
                caption=data["caption"],
                whatsapp_message_id=whatsapp_message_id,
                file_path=f"{WhatsAppAPI.MEDIA_URL}{file_path}"if media_type == 'audio' or media_type == 'voice'else file_path
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
        if data["content_type"] == 'voice' or data["content_type"]=='audio':
            return f"{file_path}"
        else:
            return f"{WhatsAppAPI.MEDIA_URL}{file_path}"

    async def _broadcast_message(self, payload: dict) -> None:
        """Broadcast message to all channel members."""
        if payload["from_bot"] == "True":
            payload.update({"content_type":"message_status"})
        await self.consumer.channel_layer.group_send(
            self.consumer.room_group_name,
            {
                "type": "chat_message",
                "conversation_state":await self._get_conversation_state(payload["conversation_id"]),
                **payload
            }
        )

    async def _send_error_message(self, error_message: str) -> None:
        """Send error message to client."""
        import json
        await self.consumer.send(json.dumps({
            "type": "error",
            "message": error_message
        }))

    @sync_to_async
    def _get_phone_number(self, conversation_id: str) -> str:
        """Get phone number for a conversation."""
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        phonenumber = conversation.contact_id.phone_number
        return phonenumber

    @sync_to_async
    def _get_whatsapp_account_id(self, conversation_id: str) -> str:
        """Get WhatsApp account ID for a conversation."""
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        waid = conversation.channle_id.phone_number_id
        return waid

    @sync_to_async
    def _get_channel_token(self, conversation_id: str) -> str:
        """Get channel token for a conversation."""
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        tocken = conversation.channle_id.tocken
        return tocken
    
    @sync_to_async
    def _get_conversation(self, conversation_id):
        """Get conversation by ID."""
        from django.utils import timezone
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        conversation.updated_at = timezone.now()
        conversation.save()
        return conversation

    @sync_to_async
    def _get_conversation_state(self, conversation_id: str) -> str:
        return Conversation.objects.get(conversation_id=conversation_id).state

    @sync_to_async
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
