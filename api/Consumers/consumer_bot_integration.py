import json
import langid
import requests
from functools import lru_cache
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from django.core.files.storage import default_storage
from django.db.models import Q, Prefetch
from api.Flow.models_flow import Flow, Chat, Attribute, Custome_attribute, RestartKeyword
from api.Channel.models_channel import Channle
from api.Contact.models_contact import Conversation, ChatMessage
from api.APIs.models_api import API, Api_parameter, APILog
from .consumer_constants import ContentType
from api.utils import (
    send_message, 
    change_occurences,
    show_response, 
    read_json, 
    check_sql_condition, 
    validate_phone_number, 
    validate_email
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
        channel = await self._get_channel(data['channel_id'])

        flow = await self._get_flow_by_trigger(channel, content, source_id)
        reset_flow_, ch = await self.reset_flow(channel, source_id, conversation_id, wamid, content, contact_name)

        if not flow or reset_flow_ == True:
            flow = await database_sync_to_async(channel.flows.get)(is_default=True)
        
        file_path = await database_sync_to_async(default_storage.path)(flow.flow.name)
        chat_flow = await sync_to_async(read_json)(file_path)
        
        if chat_flow and source_id:
            if reset_flow_ == True:
                chat = ch
            else:
                chat = await self._get_chat(source_id, channel)
            
            questions = chat_flow['payload']['questions']
            
            if not bool(chat.state) or chat.state == 'end' or chat.state == '':
                await database_sync_to_async(chat.update_state)('start')
            
            while True:
                next_question_id = None
                if chat.state == 'start':
                    if reset_flow_ == True:
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
                
                message, next_question_id, choices_with_next, choices, r_type, attribute_name = await sync_to_async(show_response)(question, questions, chat.id)
                
                if r_type == 'detect_language':
                    lang = await sync_to_async(langid.classify)(data['content'])
                    language = lang[0]
                    next_options = [(option['value'], option['next']['target']) for option in question['options']]
                    detect = False
                    for options in next_options:
                        for opt in options:
                            if opt == language:
                                detect = True
                                next_question_id = options[1]
                                break
                    if not detect:
                        next_question_id = next_options[-1][1]

                if r_type == 'button' or r_type == 'list':
                    state_ = await self._retype_content_list_or_button(content, channel, question, chat, r_type, choices, platform, message, data, choices_with_next, attribute_name, conversation_id, contact_name)
                    if state_:
                        return True
                    continue
                
                elif r_type == 'live_chat':
                    next_message = await self._retype_live_chat(message, chat, channel, question, platform, conversation_id, data) 
                    next_question_id = next_message
                
                elif r_type == 'redirect':
                    ret_from , chat_, flow= await self._retype_redirect_flow(next_question_id, source_id, channel, chat)
                    questions=ret_from
                    chat = chat_
                    continue

                elif r_type == 'if-else':
                    await self._retype_ifElse(chat, next_question_id)
                    continue

                elif r_type == 'smart_question' and choices_with_next:
                    if not chat.isSent:
                        chat.isSent = True
                        await database_sync_to_async(chat.save)()
                        message_wamid = await sync_to_async(send_message)(
                            message_content=await sync_to_async(change_occurences)(message, pattern=r'\{\{(\w+)\}\}', chat_id=chat.id, sql=True),
                            to = chat.conversation_id,
                            bearer_token=channel.tocken,
                            wa_id=channel.phone_number_id,
                            chat_id=chat.id,
                            platform=platform,
                            question=question)
                        return True
                    else:
                        try:
                            user_reply = data['content']
                        except:
                            try:
                                user_reply = data['entry'][0]['changes'][0]['value']['messages'][0]['text']['body']
                            except:
                                user_reply = data['entry'][0]['changes'][0]['value']['messages'][0]['reply_to']['button_title']
                        
                        account = await self._get_account(data['channel_id'])
                        attr, created = Attribute.objects.get_or_create(key=attribute_name, chat_id=chat.id, account=account)
                        attr.value = user_reply
                        await database_sync_to_async(attr.save)()
                        
                        for option in choices_with_next:
                            matchingType = option[3]
                            if matchingType == 'CONTAIN':
                                if any(string in user_reply for string in option[4]):
                                    next_question_id = option[2]
                                    break
                            elif matchingType == 'EXACT':
                                if any(string == user_reply for string in option[4]):
                                    next_question_id = option[2]
                                    break
                        
                        await database_sync_to_async(chat.update_state)(next_question_id)
                        chat.isSent = False
                        await database_sync_to_async(chat.save)()

                elif r_type == 'api':
                    next_question_id = await self._retype_api(question, chat, choices_with_next)

                elif r_type == 'name' or r_type == 'phone' or r_type == 'email' or r_type == 'question' or r_type == 'number':
                    state = await self._retype_name_phone_email_question(question, chat, channel, content, r_type, next_question_id, platform, message, data, attribute_name, conversation_id, contact_name)
                    if state:
                        return True

                elif r_type == 'document':
                    await self._retype_document(channel, chat, question, message, platform, conversation_id, data, next_question_id)

                elif r_type == 'image':
                    await self._retype_image(message, chat, channel, question, platform, conversation_id, data, next_question_id)

                elif r_type == 'audio' or r_type == 'sticker' or r_type == 'video':
                    await self._retype_audio_vedio_steker(message, chat, channel, question, platform, r_type, conversation_id, data, next_question_id)

                elif r_type == 'contact' or r_type == 'location':
                    message_wamid = await sync_to_async(send_message)(
                        message_content=await sync_to_async(change_occurences)(message, pattern=r'\{\{(\w+)\}\}', chat_id=chat.id, sql=True),
                        to=chat.conversation_id,
                        bearer_token=channel.tocken,
                        wa_id=channel.phone_number_id,
                        type=r_type,
                        chat_id=chat.id,
                        platform=platform,
                        question=question)
                
                elif r_type == 'Condition' and choices_with_next or r_type == 'condition' and choices_with_next:
                    for c in choices_with_next:
                        condition = c[0][0]
                        default_state = ''
                        condition = change_occurences(condition, pattern=r'\{\{(\w+)\}\}', chat_id=chat.id, sql=True)
                        
                        if not condition == 'Default':
                            if check_sql_condition(condition):
                                next_question_id = c[3]
                                break
                        else:
                            default_state = c[3]
                    
                    if not next_question_id in [c[3] for c in choices_with_next]:
                        next_question_id = default_state
                
                elif r_type == 'detect_language':
                    pass
                else:
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
                    message_id = await self._create_chat_message(
                        conversation_id=await self._get_conversation(conversation_id),
                        user= None,
                        content_type="text",
                        content=message_con,
                        whatsapp_message_id=message_wamid['messages'][0]['id']
                    )
                    await self._broadcast_message_flow({
                        "phoneNumber":await self._get_phone_number(conversation_id),
                        "conversation_id": conversation_id,
                        "content":message_con,
                        "content_type":"text",
                        "wamid": "wamid",
                        "created_at": f"{message_id.created_at}",
                        "message_id": message_id.message_id,
                        "from_bot":"True",
                        "status_message": "sent"
                    })
                
                await database_sync_to_async(chat.update_state)(next_question_id)
                if next_question_id == 'end':
                    chat.isSent = False
                    await database_sync_to_async(chat.save)()
                    break

        if not next_question_id or next_question_id == 'end':
            return True
        else:
            return False

    async def reset_flow(self, channel, source_id, conversation_id, wamid, content, contact_name):
        reset_flow = False
        restart_keyword = await database_sync_to_async(list)(RestartKeyword.objects.filter(channel_id=channel.channle_id))
        for rest in restart_keyword:
            if rest.keyword == content:
                reset_flow = True
                ch = await self._update_chat_for_restart(source_id, channel, await self._get_default_flow(rest))
                if ch:
                    message_id = await self._create_chat_message(
                        conversation_id=await self._get_conversation(conversation_id),
                        user=None,
                        content_type=ContentType.TEXT,
                        content=content,
                        whatsapp_message_id=wamid,
                        from_message=contact_name
                    )
                    await self._broadcast_message_flow({
                        "phoneNumber":await self._get_phone_number(conversation_id),
                        "conversation_id": conversation_id,
                        "content":content,
                        "content_type":"text",
                        "wamid": wamid,
                        "created_at": f"{message_id.created_at}",
                        "wamid":wamid,
                        "message_id": message_id.message_id,
                        "from_bot":"False",
                        "status_message": "sent"
                    })
                    await database_sync_to_async(ch.update_state)('start')
                    ch.isSent = False
                    await database_sync_to_async(ch.save)()    
            else:
                ch = await self._get_chat(source_id, channel)
        return reset_flow, ch

    async def _get_flow_by_trigger(self, channel, content, source_id):
        try:
            flow = await database_sync_to_async(channel.flows.get)(trigger__trigger=content)
            chats = await database_sync_to_async(list)(Chat.objects.filter(
                Q(conversation_id=source_id) & 
                Q(channel_id=channel.channle_id)
            ))
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

    async def _retype_content_list_or_button(self, content, channel, question, chat, r_type, choices, platform, message, data, choices_with_next, attribute_name, conversation_id, contact_name):
        message_con = await sync_to_async(change_occurences)(message, pattern=r'\{\{(\w+)\}\}', chat_id=chat.id, sql=True)
        if not chat.isSent:
            chat.isSent = True
            await database_sync_to_async(chat.save)()

            if r_type == 'list':
                message_wamid = await sync_to_async(send_message)(
                    message_content=message_con,
                    choices=choices,
                    type='interactive', 
                    interaction_type='list',
                    footer=question['footer'],
                    header=question['header'],
                    to=chat.conversation_id,
                    bearer_token=channel.tocken,
                    wa_id=channel.phone_number_id,
                    chat_id=chat.id,
                    platform=platform,
                    question=question
                )
            else:
                message_wamid = await sync_to_async(send_message)(
                    message_content=message_con,
                    choices=choices,
                    type='interactive', 
                    interaction_type='button',
                    to=chat.conversation_id,
                    bearer_token=channel.tocken,
                    wa_id=channel.phone_number_id,
                    chat_id=chat.id,
                    platform=platform,
                    question=question
                )
                message_id = await self._create_chat_message(
                    conversation_id=await self._get_conversation(conversation_id),
                    user=None,
                    content_type="text",
                    content=message_con,
                    whatsapp_message_id=message_wamid['messages'][0]['id'],
                )
                await self._broadcast_message_flow({
                    "conversation_id": conversation_id,
                    "phoneNumber":await self._get_phone_number(conversation_id),
                    "content": message_con,
                    "created_at": f"{message_id.created_at}",
                    "content_type": "text",
                    "wamid": message_wamid['messages'][0]['id'],
                    "message_id": message_id.message_id,
                    "from_bot":"True",
                    "status_message": "sent"
            })
            return True
        else:
            user_reply = content
            message_id = await self._create_chat_message(
                conversation_id=await self._get_conversation(data["conversation_id"]),
                user=None,
                content_type="text",
                content=user_reply,
                whatsapp_message_id="sdflskjdflksjdf",
                from_message=contact_name,
            )
            await self._broadcast_message_flow({
                "phoneNumber":await self._get_phone_number(conversation_id),
                "conversation_id": conversation_id,
                "content":content,
                "content_type":"text",
                "wamid": "wamid",
                "created_at": f"{message_id.created_at}",
                "message_id": message_id.message_id,
                "from_bot":"False",
                "status_message": "sent"
            })
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
                message_id = await self._create_chat_message(
                    conversation_id=await self._get_conversation(data["conversation_id"]),
                    user=None,
                    content_type="text",
                    content=error_message,
                    whatsapp_message_id="sdflskjdflksjdf",
                    from_message=contact_name
                )
                await self._broadcast_message_flow({
                    "phoneNumber":await self._get_phone_number(conversation_id),
                    "conversation_id": conversation_id,
                    "content":error_message,
                    "content_type":"text",
                    "wamid": "wamid",
                    "created_at": f"{message_id.created_at}",
                    "message_id": message_id.message_id,
                    "from_bot":"True",
                    "status_message": "sent"
                })
                return True
            else:
                account = await self._get_account(data['channel_id'])
                attr = await self._create_attribute(attribute_name, account)
                await self._save_custome_attribute(attr, chat, user_reply)
                next_question_id = [c[2] for c in choices_with_next if user_reply == c[0]][0]
                await self._update_chat_status(chat, next_question_id)

    async def _retype_api(self, question, chat, choices_with_next):
        api_id = question['name']
        api_ = await self._get_api_info(api_id)
        api_parameter_headers, api_parameter_params = await self._get_api_parameter_header(api_)
        headers = {
            'Content-Type': 'application/json',
        }
        headers_ = await self._get_new_header(headers, api_parameter_headers, chat)
        data = json.loads(api_.body) if api_.body else {}
        endpoint = api_.endpoint
        endpoint_ = await self._get_new_endpoint(endpoint, api_parameter_params, chat)
        try:
            for key, value in data.items():
                if isinstance(value, (int, float)):
                    continue
                data[key] = await sync_to_async(change_occurences)(value, pattern=r'\{\{(\w+)\}\}', chat_id=chat.id, sql=True)
        except:
            data = {}
        response = requests.post(endpoint_ , headers=headers_, json=data)
        api_log = await self._create_api_log(
            api=api_,
            response = json.loads(response.content) if response.content else {},
            status_request = response.status_code
        )
        custome_attrs = await self._get_custome_attrs(api_)
        await self._save_api_response_in_custome_attribute(custome_attrs, response, chat)
        for option in choices_with_next:
            for state in option:
                if str(response.status_code) == str(state):
                    next_question_id = option[2]
                    await self._update_chat_status(chat, next_question_id)
                    return next_question_id

    async def _retype_name_phone_email_question(self, question, chat, channel, content, r_type, next_question_id, platform, message, data, attribute_name, conversation_id, contact_name):
        message_con = await sync_to_async(change_occurences)(message, pattern=r'\{\{(\w+)\}\}', chat_id=chat.id, sql=True)
        if not chat.isSent:
            chat.isSent = True
            await database_sync_to_async(chat.save)()
            message_wamid = await sync_to_async(send_message)(
                message_content= message_con,
                to=chat.conversation_id,
                bearer_token=channel.tocken,
                wa_id=channel.phone_number_id,
                chat_id=chat.id,
                platform=platform,
                question=question)
            message_id = await self._create_chat_message(
                conversation_id=await self._get_conversation(conversation_id),
                user=None,
                content_type="text",
                content=message_con,
                whatsapp_message_id=message_wamid['messages'][0]['id']
            )
            await self._broadcast_message_flow({
                "conversation_id": conversation_id,
                "phoneNumber":await self._get_phone_number(conversation_id),
                "content": message_con,
                "created_at": f"{message_id.created_at}",
                "content_type": "text",
                "wamid": message_wamid['messages'][0]['id'],
                "message_id": message_id.message_id,
                "from_bot":"True",
                "status_message": "sent"
            })
            return True
        else:
            user_reply = content
            message_id = await self._create_chat_message(
                conversation_id=await self._get_conversation(data["conversation_id"]),
                user=None,
                content_type="text",
                content=user_reply,
                whatsapp_message_id="sdflskjdflksjdf",
                from_message=contact_name
            )
            await self._broadcast_message_flow({
                "phoneNumber":await self._get_phone_number(conversation_id),
                "conversation_id": conversation_id,
                "content":user_reply,
                "content_type":"text",
                "wamid": "wamid",
                "created_at": f"{message_id.created_at}",
                "message_id": message_id.message_id,
                "from_bot":"False",
                "status_message": "sent"
            })
            if r_type == 'name' and len(user_reply) > question['maxRange'] or\
            r_type == 'phone' and not validate_phone_number(user_reply) or\
            r_type == 'email' and not validate_email(user_reply) or\
            r_type == 'number' and not str(user_reply).isdigit():
                error_message = question['message']['error']
                message_wamid = await sync_to_async(send_message)(
                    message_content=await sync_to_async(change_occurences)(error_message, pattern=r'\{\{(\w+)\}\}', chat_id=chat.id, sql=True),
                    to=chat.conversation_id,
                    bearer_token=channel.tocken,
                    wa_id=channel.phone_number_id,
                    chat_id=chat.id,
                    platform=platform,
                    question=question)
                message_id = await self._create_chat_message(
                    conversation_id=await self._get_conversation(data["conversation_id"]),
                    user=None,
                    content_type="text",
                    content=error_message,
                    whatsapp_message_id=message_wamid['messages'][0]['id'],
                )
                await self._broadcast_message_flow({
                    "conversation_id": conversation_id,
                    "phoneNumber":await self._get_phone_number(conversation_id),
                    "content": error_message,
                    "created_at": f"{message_id.created_at}",
                    "content_type": "text",
                    "wamid": message_wamid['messages'][0]['id'],
                    "message_id": message_id.message_id,
                    "from_bot":"True",
                    "status_message": "sent"
                })
                return True
            else:
                account = await self._get_account(data['channel_id'])
                attr = await self._create_attribute(attribute_name, account)
                await self._save_custome_attribute(attr, chat, user_reply)
                await self._update_chat_status(chat, next_question_id)

    async def _retype_document(self, channel, chat, question, message, platform, conversation_id, data, next_question_id):
        message_con = await sync_to_async(change_occurences)(message, pattern=r'\{\{(\w+)\}\}', chat_id=chat.id, sql=True)
        message_wamid = await sync_to_async(send_message)(
            message_content=message_con,
            to=chat.conversation_id,
            bearer_token=channel.tocken,
            type='document',
            source=question['source'],
            beem_media_id=question.get('beem_media_id'),
            wa_id=channel.phone_number_id,
            chat_id=chat.id,
            platform=platform,
            question=question)
        message_id = await self._create_chat_media_message(
            conversation_id= await self._get_conversation(conversation_id),
            user=None,
            media_type="document",
            caption=message_con or "",
            whatsapp_message_id=message_wamid['messages'][0]['id'],
            file_path= question['source'],
        )
        await self._broadcast_message_flow({
            "conversation_id": conversation_id,
            "phoneNumber":await self._get_phone_number(conversation_id),
            "content": message_con,
            "created_at": f"{message_id.created_at}",
            "content_type": "document",
            "wamid": message_wamid['messages'][0]['id'],
            "message_id": message_id.message_id,
            "from_bot":"True",
            "status_message": "sent"
        })
        await self._update_chat_status(chat, next_question_id)

    async def _retype_image(self, message, chat, channel, question, platform, conversation_id, data, next_question_id):
        message_con = await sync_to_async(change_occurences)(message, pattern=r'\{\{(\w+)\}\}', chat_id=chat.id, sql=True)
        message_wamid = await sync_to_async(send_message)(
            message_content=message_con,
            to=chat.conversation_id,
            bearer_token=channel.tocken,
            wa_id=channel.phone_number_id,
            type='image',
            source=question['source'],
            beem_media_id=question.get('beem_media_id'), 
            chat_id=chat.id,
            platform=platform,
            question=question
        )
        message_id = await database_sync_to_async(ChatMessage.objects.create)(
            conversation_id= await self._get_conversation(conversation_id),
            user=None,
            media_type="image",
            caption=message_con or "",
            wamid=message_wamid['messages'][0]['id'],
            media_url= question['source'],
        )
        await self._broadcast_message_flow({
            "conversation_id": conversation_id,
            "content": message_con,
            "phoneNumber":await self._get_phone_number(conversation_id),
            "created_at": f"{message_id.created_at}",
            "content_type": "image",
            "wamid": message_wamid['messages'][0]['id'],
            "message_id": message_id.message_id,
            "from_bot":"True",
            "status_message": "sent"
        })
        await self._update_chat_status(chat, next_question_id)

    async def _retype_audio_vedio_steker(self, message, chat, channel, question, platform, r_type, conversation_id, data, next_question_id):
        message_con = await sync_to_async(change_occurences)(message, pattern=r'\{\{(\w+)\}\}', chat_id=chat.id, sql=True)
        message_wamid = await sync_to_async(send_message)(
            message_content=message_con,
            to=chat.conversation_id,
            bearer_token=channel.tocken,
            wa_id=channel.phone_number_id,
            type=r_type,
            source=question['source'], 
            chat_id=chat.id,
            platform=platform,
            question=question)
        message_id = await self._create_chat_media_message(
            conversation_id= await self._get_conversation(conversation_id),
            user=None,
            media_type=r_type,
            caption=message_con or "",
            whatsapp_message_id=message_wamid['messages'][0]['id'],
            file_path= question['source'],
        )
        await self._broadcast_message_flow({
            "conversation_id": conversation_id,
            "phoneNumber":await self._get_phone_number(conversation_id),
            "content": message_con,
            "created_at": f"{message_id.created_at}",
            "content_type": "audio",
            "wamid": message_wamid['messages'][0]['id'],
            "message_id": message_id.message_id,
            "from_bot":"True",
            "status_message": "sent"
        })
        await self._update_chat_status(chat, next_question_id)

    async def _retype_live_chat(self, message, chat, channel, question, platform, conversation_id, data):
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
        message_id = await self._create_chat_message(
            conversation_id=await self._get_conversation(conversation_id),
            user= None,
            content_type="text",
            content=message_con,
            whatsapp_message_id=message_wamid['messages'][0]['id']
        )
        await self._update_state_conversation(conversation_id)
        await self._broadcast_message_flow({
            "conversation_id": conversation_id,
            "phoneNumber":await self._get_phone_number(conversation_id),
            "content": message_con,
            "created_at": f"{message_id.created_at}",
            "content_type": "text",
            "wamid": message_wamid['messages'][0]['id'],
            "message_id": message_id.message_id,
            "from_bot":"True",
            "status_message": "sent"
        })
        return "end"

    async def _retype_redirect_flow(self, next_question_id, source_id, channel, chat):
        flow = await self._get_flow(next_question_id)
        file_path = await database_sync_to_async(default_storage.path)(flow.flow.name)
        chat_flow = await sync_to_async(read_json)(file_path)
        if chat_flow and source_id:
            chat = await self._update_chat_status_flow(chat, flow)
            questions = chat_flow['payload']['questions']
            await database_sync_to_async(chat.update_state)('start')
        return questions, chat, flow
    
    async def _retype_ifElse(self, chat, next_question_id):
        await self._update_chat_status(chat, next_question_id)

    async def _broadcast_message_flow(self, payload: dict) -> None:
        await self.consumer.channel_layer.group_send(
            self.consumer.room_group_name,    
            {
                "type": "chat_message",
                "conversation_state":await self._get_conversation_state(payload["conversation_id"]),
                **payload
            }
        )

    @database_sync_to_async
    def _get_channel(self, channel_id: str):
        """Retrieve channel by ID."""
        return Channle.objects.get(channle_id=channel_id)

    @database_sync_to_async
    def _get_conversation(self, conversation_id):
        """Get conversation by ID."""
        from django.utils import timezone
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        conversation.updated_at = timezone.now()
        conversation.save()
        return conversation

    @database_sync_to_async
    def _get_phone_number(self, conversation_id: str) -> str:
        """Get phone number for a conversation."""
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        phonenumber = conversation.contact_id.phone_number
        return phonenumber

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

    @database_sync_to_async
    def _update_chat_status(self, chat, next_question_id) -> None:
        """Update conversation status."""
        chat.update_state(next_question_id)
        chat.isSent = False
        chat.save()

    @database_sync_to_async
    def _update_state_conversation(self, conversation_id: str) -> None:
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        conversation.state = "live_chat"
        conversation.save()

    @database_sync_to_async
    def _get_account(self, channel_id):
        """Get account based on channel."""
        channel = Channle.objects.get(channle_id=channel_id)
        return channel.account_id

    @database_sync_to_async
    def _create_attribute(self, attribute_name, account):
        """Create or update an attribute."""
        attr, created = Attribute.objects.get_or_create(key=attribute_name, account = account)
        return attr

    @database_sync_to_async
    def _save_custome_attribute(self, attribute, chat, user_reply):
        custome_attribute, created = Custome_attribute.objects.get_or_create(attribute=attribute, chat=chat)
        custome_attribute.value = user_reply
        custome_attribute.save()

    @database_sync_to_async
    def _get_api_info(self, api_id):
        """Get API information by name."""
        return API.objects.get(api_id=api_id)

    @database_sync_to_async
    def _get_custome_attrs(self, api):
        return Custome_attribute.objects.filter(api=api)

    @database_sync_to_async
    def _save_api_response_in_custome_attribute(self, custome_attrs, response, chat):
        if custome_attrs:
            for custome_attr in custome_attrs:
                self._save_value_for_custome_attr(custome_attr, response, chat)

    @database_sync_to_async
    def _save_value_for_custome_attr(self, custome_attr, response, chat):
        custome_attr.value = response.content[f'{custome_attr.variable}']
        custome_attr.chat = chat
        custome_attr.save()

    @database_sync_to_async
    def _get_api_parameter_header(self, api):
        headers =Api_parameter.objects.filter(Q(api=api) & Q(type='header'))
        parameters = Api_parameter.objects.filter(Q(api=api) & Q(type='parameter'))
        return headers, parameters

    @database_sync_to_async
    def _get_new_header(self, headers, api_parameter_headers, chat):
        for api_parameter_header in api_parameter_headers:
            value = f'{api_parameter_header.value}'
            headers[f'{api_parameter_header.key}'] = change_occurences(value, pattern=r'\{\{(\w+)\}\}', chat_id=chat.id, sql=True)
        return headers

    @database_sync_to_async
    def _get_new_endpoint(self, endpoint, api_parameter_params, chat):
        final_url = ''
        if api_parameter_params:
            for api_parameter_param_ in api_parameter_params:
                key = api_parameter_param_.key
                value_ = api_parameter_param_.value
                value = change_occurences(value_, pattern=r'\{\{(\w+)\}\}', chat_id=chat.id, sql=True)
                final_url += f'{key}={value}&'
            endpoint += f'?{final_url}'
        else:
            endpoint = endpoint
        return endpoint

    @database_sync_to_async
    def _get_flow(self, next_question_id):
        return Flow.objects.get(id=next_question_id)

    @database_sync_to_async
    def _get_chat(self, source_id, channel):
        chat, created = Chat.objects.get_or_create(conversation_id=source_id, channel_id=channel)
        return chat

    @database_sync_to_async
    def _update_chat_for_restart(self, source_id, channel, flow):
        chat, created = Chat.objects.get_or_create(conversation_id=source_id, channel_id=channel)
        if chat:
            chat.flow = flow
            chat.state = 'start'
            chat.isSent = False
            chat.save()
            return chat
        return None

    @database_sync_to_async
    def _get_default_flow(self, rest):
        return rest.channel_id.flows.filter(is_default=True).first()

    @database_sync_to_async
    def _update_chat_status_flow(self, chat, flow) -> None:
        """Update conversation status."""
        chat.flow = flow
        chat.isSent = False
        chat.save()
        return chat

    @database_sync_to_async
    def _create_api_log(self, api, response, status_request):
        return APILog.objects.create(api=api, response=response, status_request=status_request)
