from channels.db import database_sync_to_async
from django.utils import timezone
from api.Auth.models_auth import CustomUser
from api.Channel.models_channel import Channle
from api.Contact.models_contact import Conversation, ChatMessage
from api.Contact.serializers_contact import ConversationSerializer


class DatabaseHelpers:
    """Database helper methods for the chat consumer."""
    
    def __init__(self, consumer):
        self.consumer = consumer
    
    @database_sync_to_async
    def get_channel(self, channel_id: str):
        """Retrieve channel by ID."""
        return Channle.objects.get(channle_id=channel_id)

    @database_sync_to_async
    def get_or_create_chat(self, source_id: str, channel, flow):
        """Get or create chat record."""
        from api.Flow.models_flow import Chat
        return Chat.objects.get_or_create(
            conversation_id=source_id,
            channel_id=channel,
            flow=flow
        )[0]

    @database_sync_to_async
    def update_state_conversation(self, conversation_id: str) -> None:
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        conversation.state = "live_chat"
        conversation.save()
    
    @database_sync_to_async
    def get_conversation_state(self, conversation_id: str) -> str:
        return Conversation.objects.get(conversation_id=conversation_id).state

    @database_sync_to_async
    def create_chat_message(self, conversation_id, user, content_type: str,
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
    def create_chat_media_message(self, conversation_id: str, user, media_type: str,
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
    def get_conversations(self):
        """Get all conversations for a channel."""
        user = CustomUser.objects.get(id=self.consumer.user.id)
        permissions = list(user.get_all_permissions())
        if 'api.visibility all conversations' in permissions:
            conversation = Conversation.objects.all()
            serializer = ConversationSerializer(conversation, many=True)
            return serializer.data
        else:
            conversation = Conversation.objects.filter(user=self.consumer.user)
            serializer = ConversationSerializer(conversation, many=True)
            return serializer.data

    @database_sync_to_async
    def get_last_message(self, conversation_id: str):
        """Get the last message in a conversation."""
        conversation = Conversation.objects.filter(conversation_id=conversation_id).first()
        message = conversation.chatmessage_set.exclude(from_message ='bot').order_by("-created_at").first()
        return message

    @database_sync_to_async
    def archive_conversation(self, conversation_id: str) -> None:
        """Archive a conversation."""
        pass

    @database_sync_to_async
    def update_chat_status(self, chat, next_question_id) -> None:
        """Update conversation status."""
        chat.update_state(next_question_id)
        chat.isSent = False
        chat.save()

    @database_sync_to_async
    def get_phone_number(self, conversation_id: str) -> str:
        """Get phone number for a conversation."""
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        phonenumber = conversation.contact_id.phone_number
        return phonenumber

    @database_sync_to_async
    def get_whatsapp_account_id(self, conversation_id: str) -> str:
        """Get WhatsApp account ID for a conversation."""
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        waid = conversation.channle_id.phone_number_id
        return waid

    @database_sync_to_async
    def get_channel_token(self, conversation_id: str) -> str:
        """Get channel token for a conversation."""
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        tocken = conversation.channle_id.tocken
        return tocken
    
    @database_sync_to_async
    def get_conversation(self, conversation_id):
        """Get conversation by ID."""
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        conversation.updated_at = timezone.now()
        conversation.save()
        return conversation
    
    @database_sync_to_async
    def get_account(self, channel_id):
        """Get account based on channel."""
        channel = Channle.objects.get(channle_id=channel_id)
        return channel.account_id
