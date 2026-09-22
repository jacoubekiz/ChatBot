"""
Message type handler functions for bot integration.
"""
from asgiref.sync import sync_to_async
from api.utils import change_occurences, validate_phone_number, validate_email, send_message
from .database_helpers import DatabaseHelpers
from .message_helpers import MessageHelpers
import json
import requests
from .flow_handlers import FlowHandlers
from .api_handlers import APIHandlers


class MessageTypeHandlers:
    """Helper class for handling different message types."""
    
    @staticmethod
    async def handle_button_or_list(content, channel, question, chat, r_type, choices, platform, message, data, choices_with_next, attribute_name, conversation_id, contact_name, consumer):
        """Handle button or list message type."""
        message_con = await sync_to_async(change_occurences)(message, pattern=r'\{\{(\w+)\}\}', chat_id=chat.id, sql=True)
        
        if not chat.isSent:
            chat.isSent = True
            await DatabaseHelpers.update_chat_status(chat, chat.state)
            
            if r_type == 'list':
                message_id, message_con, message_wamid = await MessageHelpers.send_interactive_message(
                    message, chat, channel, platform, question, choices, 'list',
                    conversation_id, contact_name, header=question['header'], footer=question['footer']
                )
            else:
                message_id, message_con, message_wamid = await MessageHelpers.send_interactive_message(
                    message, chat, channel, platform, question, choices, 'button',
                    conversation_id, contact_name
                )
            
            payload, _ = await MessageHelpers.create_and_broadcast_bot_message(
                conversation_id, message_con, message_wamid
            )
            await MessageHelpers.broadcast_message(consumer, payload)
            return True
        else:
            user_reply = content
            payload, message_id = await MessageHelpers.create_and_broadcast_user_message(
                conversation_id, user_reply, contact_name, "sdflskjdflksjdf"
            )
            await MessageHelpers.broadcast_message(consumer, payload)
            
            if user_reply not in choices or user_reply == '':
                error_message = question['message']['error']
                message_wamid = await sync_to_async(send_message)(
                    message_content=await sync_to_async(change_occurences)(error_message, pattern=r'\{\{(\w+)\}\}', chat_id=chat.id, sql=True),
                    to=chat.conversation_id,
                    bearer_token=channel.tocken,
                    wa_id=channel.phone_number_id,
                    chat_id=chat.id,
                    platform=platform,
                    question=question
                )
                
                payload, _ = await MessageHelpers.create_and_broadcast_bot_message(
                    conversation_id, error_message, message_wamid
                )
                await MessageHelpers.broadcast_message(consumer, payload)
                return True
            else:
                account = await DatabaseHelpers.get_account(data['channel_id'])
                attr = await DatabaseHelpers.create_attribute(attribute_name, account)
                await DatabaseHelpers.save_custome_attribute(attr, chat, user_reply)
                next_question_id = [c[2] for c in choices_with_next if user_reply == c[0]][0]
                await DatabaseHelpers.update_chat_status(chat, next_question_id)
                return False
    
    @staticmethod
    async def handle_live_chat(message, chat, channel, question, platform, conversation_id, data, consumer):
        """Handle live chat message type."""
        message_id, message_con, message_wamid = await MessageHelpers.send_text_message(
            message, chat, channel, platform, question, conversation_id, None, from_bot=True
        )
        
        await DatabaseHelpers.update_state_conversation(conversation_id)
        
        payload, _ = await MessageHelpers.create_and_broadcast_bot_message(
            conversation_id, message_con, message_wamid
        )
        await MessageHelpers.broadcast_message(consumer, payload)
        return "end"
    
    @staticmethod
    async def handle_api(question, chat, choices_with_next):
        """Handle API message type."""
        
        api_id = question['name']
        api_ = await DatabaseHelpers.get_api_info(api_id)
        next_question_id = await APIHandlers.execute_api_call(api_, chat, choices_with_next)
        return next_question_id
    
    @staticmethod
    async def handle_name_phone_email_question(question, chat, channel, content, r_type, next_question_id, platform, message, data, attribute_name, conversation_id, contact_name, consumer):
        """Handle name, phone, email, question, or number message types."""
        message_id, message_con, message_wamid = await MessageHelpers.send_text_message(
            message, chat, channel, platform, question, conversation_id, contact_name, from_bot=True
        )
        
        payload, _ = await MessageHelpers.create_and_broadcast_bot_message(
            conversation_id, message_con, message_wamid
        )
        await MessageHelpers.broadcast_message(consumer, payload)
        
        if not chat.isSent:
            chat.isSent = True
            await DatabaseHelpers.update_chat_status(chat, chat.state)
            return True
        else:
            user_reply = content
            payload, message_id = await MessageHelpers.create_and_broadcast_user_message(
                conversation_id, user_reply, contact_name, "sdflskjdflksjdf"
            )
            await MessageHelpers.broadcast_message(consumer, payload)
            
            is_valid = True
            if r_type == 'name' and len(user_reply) > question['maxRange']:
                is_valid = False
            elif r_type == 'phone' and not validate_phone_number(user_reply):
                is_valid = False
            elif r_type == 'email' and not validate_email(user_reply):
                is_valid = False
            elif r_type == 'number' and not str(user_reply).isdigit():
                is_valid = False
            
            if not is_valid:
                # If next_question_id is 'end', skip error message and let flow end
                if next_question_id == 'end':
                    await DatabaseHelpers.update_chat_status(chat, next_question_id)
                    return False
                error_message = question['message']['error']
                message_id, message_con, message_wamid = await MessageHelpers.send_text_message(
                    error_message, chat, channel, platform, question, conversation_id, contact_name, from_bot=True
                )
                
                payload, _ = await MessageHelpers.create_and_broadcast_bot_message(
                    conversation_id, error_message, message_wamid
                )
                await MessageHelpers.broadcast_message(consumer, payload)
                return True
            else:
                account = await DatabaseHelpers.get_account(data['channel_id'])
                attr = await DatabaseHelpers.create_attribute(attribute_name, account)
                await DatabaseHelpers.save_custome_attribute(attr, chat, user_reply)
                await DatabaseHelpers.update_chat_status(chat, next_question_id)
                return False
    
    @staticmethod
    async def handle_document(channel, chat, question, message, platform, conversation_id, data, next_question_id, consumer):
        """Handle document message type."""
        message_id, message_con, message_wamid = await MessageHelpers.send_media_message(
            message, chat, channel, platform, question, 'document', 
            question['source'], conversation_id, question.get('beem_media_id'), message
        )
        
        payload, _ = await MessageHelpers.create_and_broadcast_bot_message(
            conversation_id, message_con, message_wamid, content_type="document", media_url=question['source']
        )
        await MessageHelpers.broadcast_message(consumer, payload)
        await DatabaseHelpers.update_chat_status(chat, next_question_id)
    
    @staticmethod
    async def handle_image(message, chat, channel, question, platform, conversation_id, data, next_question_id, consumer):
        """Handle image message type."""
        message_id, message_con, message_wamid = await MessageHelpers.send_media_message(
            message, chat, channel, platform, question, 'image',
            question['source'], conversation_id, question.get('beem_media_id')
        )
        
        payload, _ = await MessageHelpers.create_and_broadcast_bot_message(
            conversation_id, message_con, message_wamid, content_type="image", media_url=question['source']
        )
        await MessageHelpers.broadcast_message(consumer, payload)
        await DatabaseHelpers.update_chat_status(chat, next_question_id)
    
    @staticmethod
    async def handle_audio_video_sticker(message, chat, channel, question, platform, r_type, conversation_id, data, next_question_id, consumer):
        """Handle audio, video, or sticker message type."""
        message_id, message_con, message_wamid = await MessageHelpers.send_media_message(
            message, chat, channel, platform, question, r_type,
            question['source'], conversation_id
        )
        
        payload, _ = await MessageHelpers.create_and_broadcast_bot_message(
            conversation_id, message_con, message_wamid, content_type=r_type, media_url=question['source']
        )
        await MessageHelpers.broadcast_message(consumer, payload)
        await DatabaseHelpers.update_chat_status(chat, next_question_id)
    
    @staticmethod
    async def handle_contact_location(message, chat, channel, question, platform, r_type, conversation_id, consumer):
        """Handle contact or location message type."""
        message_id, message_con, message_wamid = await MessageHelpers.send_special_type_message(
            message, chat, channel, platform, question, r_type, conversation_id
        )
        
        payload, _ = await MessageHelpers.create_and_broadcast_bot_message(
            conversation_id, message_con, message_wamid
        )
        await MessageHelpers.broadcast_message(consumer, payload)
    
    @staticmethod
    async def handle_condition(question, chat, choices_with_next):
        """Handle condition message type."""
        return await FlowHandlers.handle_condition(choices_with_next, chat)
    
    @staticmethod
    async def handle_default_message(message, chat, channel, platform, question, conversation_id, consumer):
        """Handle default message type."""
        message_con = await sync_to_async(change_occurences)(message, pattern=r'\{\{(\w+)\}\}', chat_id=chat.id, sql=True)
        message_wamid = await sync_to_async(send_message)(
            message_content=message_con,
            to=chat.conversation_id,
            bearer_token=channel.tocken,
            wa_id=channel.phone_number_id,
            chat_id=chat.id,
            platform=platform,
            question=question,
        )
        
        message_id = await DatabaseHelpers.create_chat_message(
            conversation_id=await DatabaseHelpers.get_conversation(conversation_id),
            user=None,
            content_type="text",
            content=message_con,
            whatsapp_message_id=message_wamid['messages'][0]['id']
        )
        
        payload, _ = await MessageHelpers.create_and_broadcast_bot_message(
            conversation_id, message_con, message_wamid
        )
        await MessageHelpers.broadcast_message(consumer, payload)
