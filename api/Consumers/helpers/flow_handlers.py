"""
Flow handler functions for bot integration.
"""
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from django.core.files.storage import default_storage
from django.db.models import Q
from .message_helpers import MessageHelpers
from ..consumer_constants import ContentType
from api.Flow.models_flow import Flow, Chat, RestartKeyword
from api.utils import read_json, show_response
from api.utils import check_sql_condition, change_occurences
import langid
from .database_helpers import DatabaseHelpers


class FlowHandlers:
    """Helper class for flow operations."""
    
    @staticmethod
    async def get_flow_by_trigger(channel, content, source_id):
        """Get flow by trigger word or existing chat flow."""
        try:
            flow = await database_sync_to_async(channel.flows.get)(trigger__trigger=content)
            chats = await database_sync_to_async(list)(
                Chat.objects.filter(
                    Q(conversation_id=source_id) & 
                    Q(channel_id=channel.channle_id)
                )
            )
            for c in chats:
                c.flow = flow
                c.state = 'start'
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
    
    @staticmethod
    async def get_default_flow(channel):
        """Get default flow for a channel."""
        return await database_sync_to_async(channel.flows.get)(is_default=True)
    
    @staticmethod
    async def load_flow_json(flow):
        """Load flow JSON from storage."""
        file_path = await database_sync_to_async(default_storage.path)(flow.flow.name)
        return await sync_to_async(read_json)(file_path)
    
    @staticmethod
    async def get_question_by_state(questions, chat, reset_flow, reset_flow_chat):
        """Get question based on chat state."""
        if chat.state == 'start':
            if reset_flow:
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
        return question
    
    @staticmethod
    async def get_response_data(question, questions, chat):
        """Get response data for a question."""
        return await sync_to_async(show_response)(question, questions, chat.id)
    
    @staticmethod
    async def handle_detect_language(question, data, next_options):
        """Handle language detection."""
        lang = await sync_to_async(langid.classify)(data['content'])
        language = lang[0]
        detect = False
        next_question_id = None
        
        for options in next_options:
            for opt in options:
                if opt == language:
                    detect = True
                    next_question_id = options[1]
                    break
        
        if not detect:
            next_question_id = next_options[-1][1]
        
        return next_question_id
    
    @staticmethod
    async def handle_redirect_flow(next_question_id, source_id, channel, chat):
        """Handle flow redirection."""
        flow = await DatabaseHelpers.get_flow(next_question_id)
        file_path = await database_sync_to_async(default_storage.path)(flow.flow.name)
        chat_flow = await sync_to_async(read_json)(file_path)
        
        if chat_flow and source_id:
            chat = await DatabaseHelpers.update_chat_status_flow(chat, flow)
            questions = chat_flow['payload']['questions']
            await database_sync_to_async(chat.update_state)('start')
        
        return questions, chat, flow
    
    @staticmethod
    async def handle_if_else(chat, next_question_id):
        """Handle if-else condition."""
        await DatabaseHelpers.update_chat_status(chat, next_question_id)
    
    @staticmethod
    async def handle_condition(choices_with_next, chat):
        """Handle condition logic."""
        next_question_id = None
        default_state = ''
        
        for c in choices_with_next:
            condition = c[0][0]
            condition = change_occurences(condition, pattern=r'\{\{(\w+)\}\}', chat_id=chat.id, sql=True)
            
            if not condition == 'Default':
                if check_sql_condition(condition):
                    next_question_id = c[3]
                    break
            else:
                default_state = c[3]
        
        if not next_question_id in [c[3] for c in choices_with_next]:
            next_question_id = default_state
        
        return next_question_id
    
    @staticmethod
    async def handle_smart_question(choices_with_next, user_reply, chat, attribute_name, account):
        """Handle smart question matching."""
        next_question_id = None
        
        for option in choices_with_next:
            matching_type = option[3]
            if matching_type == 'CONTAIN':
                if any(string in user_reply for string in option[4]):
                    next_question_id = option[2]
                    break
            elif matching_type == 'EXACT':
                if any(string == user_reply for string in option[4]):
                    next_question_id = option[2]
                    break
        
        if next_question_id:
            attr, created = await DatabaseHelpers.create_attribute(attribute_name, account)
            await DatabaseHelpers.save_custome_attribute(attr, chat, user_reply)
            await DatabaseHelpers.update_chat_status(chat, next_question_id)
        
        return next_question_id
    
    @staticmethod
    async def reset_flow(channel, source_id, conversation_id, wamid, content, contact_name):
        """Reset flow if content matches a restart keyword."""
        restart_keywords = await DatabaseHelpers.get_restart_keywords(channel)
        
        matching_keyword = None
        for keyword in restart_keywords:
            if keyword.keyword == content:
                matching_keyword = keyword
                break
        
        if matching_keyword:
            default_flow = await DatabaseHelpers.get_default_flow(matching_keyword)
            ch = await DatabaseHelpers.update_chat_for_restart(source_id, channel, default_flow)
            
            if ch:
                message_id = await DatabaseHelpers.create_chat_message(
                    conversation_id=await DatabaseHelpers.get_conversation(conversation_id),
                    user=None,
                    content_type=ContentType.TEXT,
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
                
                await database_sync_to_async(ch.update_state)('start')
                ch.isSent = False
                await database_sync_to_async(ch.save)()
            
            return True, ch
        else:
            ch = await DatabaseHelpers.get_chat(source_id, channel)
            return False, ch
