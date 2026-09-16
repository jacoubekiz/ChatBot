"""
Message helper functions for bot integration.
"""
from asgiref.sync import sync_to_async
from api.utils import send_message, change_occurences
from .database_helpers import DatabaseHelpers


class MessageHelpers:
    """Helper class for message operations."""
    
    @staticmethod
    async def send_text_message(message, chat, channel, platform, question, conversation_id, contact_name, from_bot=True):
        """Send a text message."""
        message_con = await sync_to_async(change_occurences)(
            message, pattern=r'\{\{(\w+)\}\}', chat_id=chat.id, sql=True
        )
        message_wamid = await sync_to_async(send_message)(
            message_content=message_con,
            to=chat.conversation_id,
            bearer_token=channel.tocken,
            wa_id=channel.phone_number_id,
            chat_id=chat.id,
            platform=platform,
            question=question
        )
        
        message_id = await DatabaseHelpers.create_chat_message(
            conversation_id=await DatabaseHelpers.get_conversation(conversation_id),
            user=None,
            content_type="text",
            content=message_con,
            whatsapp_message_id=message_wamid['messages'][0]['id'],
            from_message=contact_name if not from_bot else "bot"
        )
        
        return message_id, message_con, message_wamid
    
    @staticmethod
    async def send_interactive_message(message, chat, channel, platform, question, choices, interaction_type, conversation_id, contact_name, header=None, footer=None):
        """Send an interactive message (list or button)."""
        message_con = await sync_to_async(change_occurences)(
            message, pattern=r'\{\{(\w+)\}\}', chat_id=chat.id, sql=True
        )
        
        kwargs = {
            'message_content': message_con,
            'choices': choices,
            'type': 'interactive',
            'interaction_type': interaction_type,
            'to': chat.conversation_id,
            'bearer_token': channel.tocken,
            'wa_id': channel.phone_number_id,
            'chat_id': chat.id,
            'platform': platform,
            'question': question
        }
        
        if header:
            kwargs['header'] = header
        if footer:
            kwargs['footer'] = footer
            
        message_wamid = await sync_to_async(send_message)(**kwargs)
        
        message_id = await DatabaseHelpers.create_chat_message(
            conversation_id=await DatabaseHelpers.get_conversation(conversation_id),
            user=None,
            content_type="text",
            content=message_con,
            whatsapp_message_id=message_wamid['messages'][0]['id'],
            from_message="bot"
        )
        
        return message_id, message_con, message_wamid
    
    @staticmethod
    async def send_media_message(message, chat, channel, platform, question, media_type, source, conversation_id, beem_media_id=None, caption=None):
        """Send a media message (image, video, audio, document)."""
        message_con = await sync_to_async(change_occurences)(
            message, pattern=r'\{\{(\w+)\}\}', chat_id=chat.id, sql=True
        )
        
        kwargs = {
            'message_content': message_con,
            'to': chat.conversation_id,
            'bearer_token': channel.tocken,
            'wa_id': channel.phone_number_id,
            'type': media_type,
            'source': source,
            'chat_id': chat.id,
            'platform': platform,
            'question': question
        }
        
        if beem_media_id:
            kwargs['beem_media_id'] = beem_media_id
            
        message_wamid = await sync_to_async(send_message)(**kwargs)
        
        message_id = await DatabaseHelpers.create_chat_media_message(
            conversation_id=await DatabaseHelpers.get_conversation(conversation_id),
            user=None,
            media_type=media_type,
            caption=caption or message_con or "",
            whatsapp_message_id=message_wamid['messages'][0]['id'],
            file_path=source
        )
        
        return message_id, message_con, message_wamid
    
    @staticmethod
    async def send_special_type_message(message, chat, channel, platform, question, r_type, conversation_id):
        """Send special type messages (contact, location)."""
        message_con = await sync_to_async(change_occurences)(
            message, pattern=r'\{\{(\w+)\}\}', chat_id=chat.id, sql=True
        )
        message_wamid = await sync_to_async(send_message)(
            message_content=message_con,
            to=chat.conversation_id,
            bearer_token=channel.tocken,
            wa_id=channel.phone_number_id,
            type=r_type,
            chat_id=chat.id,
            platform=platform,
            question=question
        )
        
        message_id = await DatabaseHelpers.create_chat_message(
            conversation_id=await DatabaseHelpers.get_conversation(conversation_id),
            user=None,
            content_type="text",
            content=message_con,
            whatsapp_message_id=message_wamid['messages'][0]['id']
        )
        
        return message_id, message_con, message_wamid
    
    @staticmethod
    async def broadcast_message(consumer, payload: dict) -> None:
        """Broadcast message to WebSocket."""
        await consumer.channel_layer.group_send(
            consumer.room_group_name,
            {
                "type": "chat_message",
                "conversation_state": await DatabaseHelpers.get_conversation_state(payload["conversation_id"]),
                **payload
            }
        )
    
    @staticmethod
    async def create_and_broadcast_user_message(conversation_id, content, contact_name, wamid):
        """Create and broadcast a user message."""
        message_id = await DatabaseHelpers.create_chat_message(
            conversation_id=await DatabaseHelpers.get_conversation(conversation_id),
            user=None,
            content_type="text",
            content=content,
            whatsapp_message_id=wamid,
            from_message=contact_name
        )
        
        payload = {
            "phoneNumber": await DatabaseHelpers.get_phone_number(conversation_id),
            "conversation_id": conversation_id,
            "content": content,
            "content_type": "text",
            "wamid": wamid,
            "created_at": f"{message_id.created_at}",
            "message_id": message_id.message_id,
            "from_bot": "False",
            "status_message": "sent"
        }
        
        return payload, message_id
    
    @staticmethod
    async def create_and_broadcast_bot_message(conversation_id, message_con, message_wamid, content_type="text", media_url=None):
        """Create and broadcast a bot message."""
        message_id = await DatabaseHelpers.create_chat_message(
            conversation_id=await DatabaseHelpers.get_conversation(conversation_id),
            user=None,
            content_type=content_type,
            content=message_con,
            whatsapp_message_id=message_wamid['messages'][0]['id'],
            from_message="bot"
        )
        
        payload = {
            "phoneNumber": await DatabaseHelpers.get_phone_number(conversation_id),
            "conversation_id": conversation_id,
            "content": message_con,
            "content_type": content_type,
            "wamid": message_wamid['messages'][0]['id'],
            "created_at": f"{message_id.created_at}",
            "message_id": message_id.message_id,
            "from_bot": "True",
            "status_message": "sent"
        }
        
        if media_url:
            payload["media_url"] = media_url
            
        return payload, message_id
