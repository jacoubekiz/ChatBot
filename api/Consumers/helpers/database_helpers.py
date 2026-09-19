"""
Database helper functions for bot integration.
"""
from channels.db import database_sync_to_async
from django.db.models import Q
from django.utils import timezone
from api.Flow.models_flow import Flow, Chat, Attribute, Custome_attribute, RestartKeyword
from api.Channel.models_channel import Channle
from api.Contact.models_contact import Conversation, ChatMessage
from api.APIs.models_api import API, Api_parameter, APILog
from api.utils import change_occurences


class DatabaseHelpers:
    """Helper class for database operations."""
    
    @staticmethod
    @database_sync_to_async
    def get_channel(channel_id: str):
        """Retrieve channel by ID."""
        return Channle.objects.get(channle_id=channel_id)

    @staticmethod
    @database_sync_to_async
    def get_conversation(conversation_id):
        """Get conversation by ID and update timestamp."""
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        conversation.updated_at = timezone.now()
        conversation.save()
        return conversation

    @staticmethod
    @database_sync_to_async
    def get_phone_number(conversation_id: str) -> str:
        """Get phone number for a conversation."""
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        return conversation.contact_id.phone_number

    @staticmethod
    @database_sync_to_async
    def get_conversation_state(conversation_id: str) -> str:
        """Get conversation state."""
        return Conversation.objects.get(conversation_id=conversation_id).state

    @staticmethod
    @database_sync_to_async
    def create_chat_message(conversation_id, user, content_type: str,
                           content: str, whatsapp_message_id: str, from_message="bot"):
        """Create a chat message record."""
        return ChatMessage.objects.create(
            conversation_id=conversation_id,
            user_id=user,
            content_type=content_type,
            content=content,
            wamid=whatsapp_message_id,
            from_message=from_message
        )

    @staticmethod
    @database_sync_to_async
    def create_chat_media_message(conversation_id: str, user, media_type: str,
                                 caption: str, whatsapp_message_id: str,
                                 file_path: str):
        """Create a media chat message record."""
        return ChatMessage.objects.create(
            conversation_id=conversation_id,
            user_id=user,
            content_type=media_type,
            caption=caption or "",
            wamid=whatsapp_message_id,
            media_url=file_path
        )

    @staticmethod
    @database_sync_to_async
    def update_chat_status(chat, next_question_id) -> None:
        """Update conversation status."""
        chat.update_state(next_question_id)
        chat.isSent = False
        chat.save()

    @staticmethod
    @database_sync_to_async
    def update_state_conversation(conversation_id: str) -> None:
        """Update conversation state to live_chat."""
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        conversation.state = "live_chat"
        conversation.save()

    @staticmethod
    @database_sync_to_async
    def get_account(channel_id):
        """Get account based on channel."""
        channel = Channle.objects.get(channle_id=channel_id)
        return channel.account_id

    @staticmethod
    @database_sync_to_async
    def create_attribute(attribute_name, account):
        """Create or get an attribute."""
        attr, created = Attribute.objects.get_or_create(key=attribute_name, account=account)
        return attr

    @staticmethod
    @database_sync_to_async
    def save_custome_attribute(attribute, chat, user_reply):
        """Save custom attribute value."""
        custome_attribute, created = Custome_attribute.objects.get_or_create(attribute=attribute, chat=chat)
        custome_attribute.value = user_reply
        custome_attribute.save()

    @staticmethod
    @database_sync_to_async
    def get_api_info(api_id):
        """Get API information by ID."""
        return API.objects.get(api_id=api_id)

    @staticmethod
    @database_sync_to_async
    def get_custome_attrs(api):
        """Get custom attributes for an API."""
        return Custome_attribute.objects.filter(api=api)

    @staticmethod
    @database_sync_to_async
    def save_api_response_in_custome_attribute(custome_attrs, response, chat):
        """Save API response in custom attributes."""
        if custome_attrs:
            for custome_attr in custome_attrs:
                DatabaseHelpers._save_value_for_custome_attr(custome_attr, response, chat)

    @staticmethod
    def _save_value_for_custome_attr(custome_attr, response, chat):
        """Save value for a specific custom attribute."""
        custome_attr.value = response.content[f'{custome_attr.variable}']
        custome_attr.chat = chat
        custome_attr.save()

    @staticmethod
    @database_sync_to_async
    def get_api_parameter_header(api):
        """Get API parameters and headers."""
        headers = Api_parameter.objects.filter(Q(api=api) & Q(type='header'))
        parameters = Api_parameter.objects.filter(Q(api=api) & Q(type='parameter'))
        return headers, parameters

    @staticmethod
    @database_sync_to_async
    def get_new_header(headers, api_parameter_headers, chat):
        """Update headers with chat variables."""
        for api_parameter_header in api_parameter_headers:
            value = f'{api_parameter_header.value}'
            headers[f'{api_parameter_header.key}'] = change_occurences(
                value, pattern=r'\{\{(\w+)\}\}', chat_id=chat.id, sql=True
            )
        return headers

    @staticmethod
    @database_sync_to_async
    def get_new_endpoint(endpoint, api_parameter_params, chat):
        """Update endpoint with parameters."""
        final_url = ''
        if api_parameter_params:
            for api_parameter_param_ in api_parameter_params:
                key = api_parameter_param_.key
                value_ = api_parameter_param_.value
                value = change_occurences(value_, pattern=r'\{\{(\w+)\}\}', chat_id=chat.id, sql=True)
                final_url += f'{key}={value}&'
            endpoint += f'?{final_url}'
        return endpoint

    @staticmethod
    @database_sync_to_async
    def get_flow(next_question_id):
        """Get flow by ID."""
        return Flow.objects.get(id=next_question_id)

    @staticmethod
    @database_sync_to_async
    def get_chat(source_id, channel):
        """Get or create chat."""
        chat, created = Chat.objects.get_or_create(conversation_id=source_id, channel_id=channel)
        return chat

    @staticmethod
    @database_sync_to_async
    def update_chat_for_restart(source_id, channel, flow):
        """Update chat for flow restart."""
        chat, created = Chat.objects.get_or_create(conversation_id=source_id, channel_id=channel)
        if chat:
            chat.flow = flow
            chat.state = 'start'
            chat.isSent = False
            chat.save()
            return chat
        return None

    @staticmethod
    @database_sync_to_async
    def get_default_flow(restart_keyword):
        """Get default flow for a channel."""
        return restart_keyword.channel_id.flows.filter(is_default=True).first()

    @staticmethod
    @database_sync_to_async
    def update_chat_status_flow(chat, flow) -> None:
        """Update chat with new flow."""
        chat.flow = flow
        chat.isSent = False
        chat.save()
        return chat

    @staticmethod
    @database_sync_to_async
    def create_api_log(api, response, status_request):
        """Create API log entry."""
        return APILog.objects.create(api=api, response=response, status_request=status_request)

    @staticmethod
    @database_sync_to_async
    def get_restart_keywords(channel):
        """Get restart keywords for a channel."""
        return list(RestartKeyword.objects.filter(channel_id=channel.channle_id))
