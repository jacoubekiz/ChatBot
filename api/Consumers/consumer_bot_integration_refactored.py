"""
Refactored bot integration using helper modules.
"""
import json
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from api.Flow.models_flow import Chat
from api.Channel.models_channel import Channle
from api.Contact.models_contact import ChatMessage
from .consumer_constants import ContentType
from .helpers import (
    DatabaseHelpers,
    MessageHelpers,
    FlowHandlers,
    MessageTypeHandlers,
    APIHandlers
)


class BotIntegration:
    """Handles bot integration and flow processing."""
    
    def __init__(self, consumer):
        self.consumer = consumer
    
    async def handle_bot_integration(self, data: dict) -> None:
        """Handle bot integration and flow processing."""
        wamid = data.get("data", {}).get('wamid', '')
        content = data.get("data", {}).get('content', '')
        contact_name = data.get('contact_name', '')
        conversation_id = data.get("conversation_id")
        source_id = data.get("data", {}).get("source_id")
        platform = 'whatsapp'
        
        channel = await DatabaseHelpers.get_channel(data['channel_id'])
        flow = await FlowHandlers.get_flow_by_trigger(channel, content, source_id)
        reset_flow_, ch = await FlowHandlers.reset_flow(channel, source_id, conversation_id, wamid, content, contact_name)

        if not flow or reset_flow_:
            flow = await FlowHandlers.get_default_flow(channel)
        
        chat_flow = await FlowHandlers.load_flow_json(flow)
        
        if chat_flow and source_id:
            if reset_flow_:
                chat = ch
            else:
                chat = await DatabaseHelpers.get_chat(source_id, channel)
            
            questions = chat_flow['payload']['questions']
            
            if not bool(chat.state) or chat.state == 'end' or chat.state == '':
                await database_sync_to_async(chat.update_state)('start')
            
            while True:
                next_question_id = None
                question = await FlowHandlers.get_question_by_state(questions, chat, reset_flow_, ch)
                
                message, next_question_id, choices_with_next, choices, r_type, attribute_name = await FlowHandlers.get_response_data(question, questions, chat)
                
                if r_type == 'detect_language':
                    next_options = [(option['value'], option['next']['target']) for option in question['options']]
                    next_question_id = await FlowHandlers.handle_detect_language(question, data, next_options)

                if r_type == 'button' or r_type == 'list':
                    should_return = await MessageTypeHandlers.handle_button_or_list(
                        content, channel, question, chat, r_type, choices, platform, message, data,
                        choices_with_next, attribute_name, conversation_id, contact_name, self.consumer
                    )
                    if should_return:
                        return True
                    continue
                
                elif r_type == 'live_chat':
                    next_question_id = await MessageTypeHandlers.handle_live_chat(
                        message, chat, channel, question, platform, conversation_id, data, self.consumer
                    )
                
                elif r_type == 'redirect':
                    questions, chat, flow = await FlowHandlers.handle_redirect_flow(
                        next_question_id, source_id, channel, chat
                    )
                    continue

                elif r_type == 'if-else':
                    await FlowHandlers.handle_if_else(chat, next_question_id)
                    continue

                elif r_type == 'smart_question' and choices_with_next:
                    if not chat.isSent:
                        chat.isSent = True
                        await database_sync_to_async(chat.save)()
                        message_id, message_con, message_wamid = await MessageHelpers.send_text_message(
                            message, chat, channel, platform, question, conversation_id, contact_name, from_bot=True
                        )
                        payload, _ = await MessageHelpers.create_and_broadcast_bot_message(
                            conversation_id, message_con, message_wamid
                        )
                        await MessageHelpers.broadcast_message(self.consumer, payload)
                        return True
                    else:
                        try:
                            user_reply = data['content']
                        except:
                            try:
                                user_reply = data['entry'][0]['changes'][0]['value']['messages'][0]['text']['body']
                            except:
                                user_reply = data['entry'][0]['changes'][0]['value']['messages'][0]['reply_to']['button_title']
                        
                        account = await DatabaseHelpers.get_account(data['channel_id'])
                        next_question_id = await FlowHandlers.handle_smart_question(
                            choices_with_next, user_reply, chat, attribute_name, account
                        )
                        if next_question_id:
                            chat.isSent = False
                            await database_sync_to_async(chat.save)()

                elif r_type == 'api':
                    next_question_id = await MessageTypeHandlers.handle_api(question, chat, choices_with_next)

                elif r_type in ['name', 'phone', 'email', 'question', 'number']:
                    should_return = await MessageTypeHandlers.handle_name_phone_email_question(
                        question, chat, channel, content, r_type, next_question_id, platform, message, data,
                        attribute_name, conversation_id, contact_name, self.consumer
                    )
                    if should_return:
                        return True

                elif r_type == 'document':
                    await MessageTypeHandlers.handle_document(
                        channel, chat, question, message, platform, conversation_id, data, next_question_id, self.consumer
                    )

                elif r_type == 'image':
                    await MessageTypeHandlers.handle_image(
                        message, chat, channel, question, platform, conversation_id, data, next_question_id, self.consumer
                    )

                elif r_type in ['audio', 'sticker', 'video']:
                    await MessageTypeHandlers.handle_audio_video_sticker(
                        message, chat, channel, question, platform, r_type, conversation_id, data, next_question_id, self.consumer
                    )

                elif r_type in ['contact', 'location']:
                    await MessageTypeHandlers.handle_contact_location(
                        message, chat, channel, question, platform, r_type, conversation_id, self.consumer
                    )
                
                elif r_type in ['Condition', 'condition']:
                    next_question_id = await MessageTypeHandlers.handle_condition(question, chat, choices_with_next)
                
                elif r_type == 'detect_language':
                    pass
                else:
                    await MessageTypeHandlers.handle_default_message(
                        message, chat, channel, platform, question, conversation_id, self.consumer
                    )
                
                # Handle null next_question_id by sending default message
                await database_sync_to_async(chat.update_state)(next_question_id)
                if next_question_id is None or next_question_id == 'end':
                    # Send a default fallback message
                    default_message = "Sorry, I didn't understand that. Please try again."
                    message_id, message_con, message_wamid = await MessageHelpers.send_text_message(
                        default_message, chat, channel, platform, question, conversation_id, contact_name, from_bot=True
                    )
                    payload, _ = await MessageHelpers.create_and_broadcast_bot_message(
                        conversation_id, message_con, message_wamid
                    )
                    await MessageHelpers.broadcast_message(self.consumer, payload)
                    chat.isSent = False
                    await database_sync_to_async(chat.save)()
                    break
                
                # await database_sync_to_async(chat.update_state)(next_question_id)
                # if next_question_id == 'end':
                #     chat.isSent = False
                #     await database_sync_to_async(chat.save)()
                #     break

        if not next_question_id or next_question_id == 'end':
            return True
        else:
            return False
