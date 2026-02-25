import json
from .models import *
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.files.base import ContentFile
from .serializers import *
import base64
from django.db.models import Q
from django.core.files.storage import default_storage
import langid
from .utils import *
from django.utils import timezone
import urllib.parse as up

# from pydub import AudioSegment

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.channel_id= self.scope["url_route"]["kwargs"]["channel_id"]
        self.room_group_name = "chat_"
            # Join room group
        self.user = self.scope['user']
        query_string = self.scope['query_string'].decode()
        params = dict(up.parse_qsl(query_string))
        self.from_message = params.get('from_bot')
        if self.user and self.user.is_authenticated:
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()
            conversations = await self.get_conversations(self.channel_id)
            for conversation in conversations:
                message = await self.get_last_message(conversation.get('conversation_id'))
                if message == None:
                    await self.return_conversation(conversation.get('conversation_id'))
                else:
                    s = timezone.now() - message.created_at
                    if s > timedelta(hours=24):
                        await self.return_conversation(conversation.get('conversation_id'))
            # for conversation in conversations:
            await self.send(text_data=json.dumps({
                "type": "conversation",
                "conversation": conversations
            }))
        elif self.from_message == 'False':
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        conversation_id = text_data_json["conversation_id"]
        content_type = text_data_json["content_type"]
        from_bot = text_data_json['from_bot']
            
        await self.change_status(conversation_id, from_bot)

    
        match content_type:
            case "bot_integration":
                    data = text_data_json.get('data', '')
                    wamid = text_data_json.get('wamid', '')
                    contact_name = text_data_json.get('contact_name', '')

                    try:
                        conversation = data['conversation']
                        source_id = conversation['contact_inbox']['source_id']
                        platform = 'whatsapp'
                    except:
                        source_id = data.get('entry')[0]['changes'][0]['value']['messages'][0]['from']
                        platform = 'beam'
                    
                    try:
                        channel = await database_sync_to_async(Channle.objects.get)(Q(channle_id=self.channel_id))
                    except:
                        return
                    
                    reset_flow = False
                    restart_keyword = await database_sync_to_async(list)(RestartKeyword.objects.filter(channel_id=channel.channle_id))
                    for rest in restart_keyword:
                        if rest.keyword == data['content']:
                            reset_flow = True
                            flows = flows = await database_sync_to_async(lambda: list(rest.channel_id.flows.all()))()
                            for flow in flows:
                                ch = await database_sync_to_async(
                                    lambda: Chat.objects.filter(
                                        Q(conversation_id=source_id) & 
                                        Q(channel_id=channel.channle_id) & 
                                        Q(flow=flow)
                                    ).first()
                                )()
                                if ch:
                                    chat_message = await database_sync_to_async(ChatMessage.objects.create)(
                                        conversation_id=await database_sync_to_async(Conversation.objects.get)(conversation_id=conversation_id),
                                        content_type='text',
                                        content=data['content'],
                                        from_message=contact_name,
                                        wamid=wamid
                                    )
                                
                                    # Send message through WebSocket
                                    await self.channel_layer.group_send(
                                        self.room_group_name, {
                                            "type": "chat_message",
                                            "content": data['content'],
                                            "content_type": 'text',
                                            "wamid": wamid,
                                            "conversation_id": conversation_id,
                                            "from_bot": "False",
                                            "message_id": chat_message.message_id,
                                            "created_at": f"{chat_message.created_at}",
                                            "from_flow":"True",
                                            "front_id": "auto_generated"
                                        }
                                    )
                                    await database_sync_to_async(ch.update_state)('start')
                                    ch.isSent = False
                                    await database_sync_to_async(ch.save)()
                                continue
                            
                            break
                    
                    try:
                        flow = await database_sync_to_async(channel.flows.get)(trigger__trigger=data['content'])
                        chats = await database_sync_to_async(list)(Chat.objects.filter(
                            Q(conversation_id=source_id) & 
                            Q(channel_id=channel.channle_id) & 
                            ~Q(flow=flow)
                        ))
                        for c in chats:
                            await database_sync_to_async(c.update_state)('end')
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
                    
                    if not flow:
                        flow = await database_sync_to_async(channel.flows.get)(is_default=True)
                    
                    file_path = await database_sync_to_async(default_storage.path)(flow.flow.name)
                    chat_flow = await sync_to_async(read_json)(file_path)
                    
                    if chat_flow and source_id:
                        chat, isCreated = await database_sync_to_async(
                            lambda: Chat.objects.get_or_create(
                                conversation_id=source_id, 
                                channel_id=channel, 
                                flow=flow
                            )
                        )()
                        
                        questions = chat_flow['payload']['questions']
                        
                        if not bool(chat.state) or chat.state == 'end' or chat.state == '':
                            await database_sync_to_async(chat.update_state)('start')
                        
                        while True:
                            next_question_id = None
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
                            
                            message, next_question_id, choices_with_next, choices, r_type, attribute_name = await sync_to_async(show_response)(question, questions)

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
                                if not chat.isSent:
                                    
                                    chat.isSent = True
                                    await database_sync_to_async(chat.save)()

                                    if r_type == 'list':
                                        message_wamid = await sync_to_async(send_message)(
                                            message_content=message,
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
                                            message_content=message,
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
                                    
                                        chat_message = await database_sync_to_async(ChatMessage.objects.create)(
                                            conversation_id=await database_sync_to_async(Conversation.objects.get)(conversation_id=conversation_id),
                                            content_type='text',
                                            content=message,
                                            from_message='bot',
                                            wamid=message_wamid['messages'][0]['id']
                                        )
                                    
                                    # Send message through WebSocket
                                        await self.channel_layer.group_send(
                                            self.room_group_name, {
                                                "type": "chat_message",
                                                "content": message,
                                                "content_type": 'text',
                                                "wamid": message,
                                                "conversation_id": conversation_id,
                                                "from_bot": "True",
                                                "message_id": chat_message.message_id,
                                                "created_at": f"{chat_message.created_at}",
                                                "from_flow":"True",
                                                "front_id": "auto_generated"
                                            }
                                        )
                                    return True
                                    
                                else:
                                    try:
                                        user_reply = data['content']
                                    except:
                                        user_reply = data['entry'][0]['changes'][0]['value']['messages'][0]['text']['body']
                                    
                                    if user_reply not in choices or user_reply == '':
                                        error_message = question['message']['error']
                                        
                                        message_wamid = await sync_to_async(send_message)(
                                            message_content=error_message,
                                            to=chat.conversation_id,
                                            bearer_token=channel.tocken,
                                            wa_id=channel.phone_number_id,
                                            chat_id=chat.id,
                                            platform=platform,
                                            question=question
                                        )
                                        
                                        chat_message = await database_sync_to_async(ChatMessage.objects.create)(
                                            conversation_id=await database_sync_to_async(Conversation.objects.get)(conversation_id=conversation_id),
                                            content_type='text',
                                            content=error_message,
                                            from_message='bot',
                                            wamid=message_wamid['messages'][0]['id']
                                        )
                                        
                                        # Send error message through WebSocket
                                        await self.channel_layer.group_send(
                                            self.room_group_name, {
                                                "type": "chat_message",
                                                "content": user_reply,
                                                "content_type": 'text',
                                                "wamid": wamid,
                                                "conversation_id": conversation_id,
                                                "from_bot": "False",
                                                "message_id": chat_message.message_id,
                                                "created_at": f"{chat_message.created_at}",
                                                "from_flow":"True",
                                                "front_id": "auto_generated"
                                            }
                                        )
                                        return True
                                        
                                    else:
                                        chat_message = await database_sync_to_async(ChatMessage.objects.create)(
                                            conversation_id=await database_sync_to_async(Conversation.objects.get)(conversation_id=conversation_id),
                                            content_type='text',
                                            content=user_reply,
                                            from_message=contact_name,
                                            wamid=wamid
                                        )
                                    
                                    # Send message through WebSocket
                                        await self.channel_layer.group_send(
                                            self.room_group_name, {
                                                "type": "chat_message",
                                                "content": user_reply,
                                                "content_type": 'text',
                                                "wamid": wamid,
                                                "conversation_id": conversation_id,
                                                "from_bot": "False",
                                                "message_id": chat_message.message_id,
                                                "created_at": f"{chat_message.created_at}",
                                                "from_flow":"True",
                                                "front_id": "auto_generated"
                                            }
                                        )
                                        attr, created = await database_sync_to_async(Attribute.objects.get_or_create)(key=attribute_name, chat_id=chat.id)
                                        attr.value = user_reply
                                        await database_sync_to_async(attr.save)()
                                        next_question_id = [c[2] for c in choices_with_next if user_reply == c[0]][0]
                                        await database_sync_to_async(chat.update_state)(next_question_id)
                                        chat.isSent = False
                                        await database_sync_to_async(chat.save)()
                            # ... continue with other r_type cases following the same pattern ...
                            
                            elif r_type == 'smart_question' and choices_with_next:
                                if not chat.isSent:
                                    chat.isSent = True
                                    await database_sync_to_async(chat.save)()
                                    message_wamid = send_message(message_content=message,
                                                to = chat.conversation_id,
                                                bearer_token=channel.tocken,
                                                wa_id=channel.phone_number_id,
                                                chat_id=chat.id,
                                                platform=platform,
                                                question=question)
                                    return True
                                else:
                                    try:
                                        user_reply = data['content'] #If this raises an error then it means that the response has come from Beam not Whatsapp                        
                                    except:
                                        
                                        try: #If this raises an error then this means that it is a beam user reply not normal beam text message reply
                                            user_reply = data['entry'][0]['changes'][0]['value']['messages'][0]['text']['body']
                                        
                                        except:
                                            user_reply = data['entry'][0]['changes'][0]['value']['messages'][0]['reply_to']['button_title']
                                            
                                    
                                    attr, created = Attribute.objects.get_or_create(key=attribute_name, chat_id=chat.id)
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
                                api_name = question['name']
                                api = API.objects.get(api_name=api_name)
                                headers = {
                                        'Content-Type': 'application/json',
                                }

                                data = api.body
                                for key, value in data.items():
                                    if isinstance(value, (int, float)):
                                        continue
                                data[key] = change_occurences(value, pattern=r'\{\{(\w+)\}\}', chat_id=chat.id, sql=True)

                                response = requests.post(api.endpoint , headers=headers, json=data)
                                for option in choices_with_next:
                                    for state in option:
                                        if str(response.status_code) == str(state):
                                            next_question_id = option[2]
                                            await database_sync_to_async(chat.update_state)(next_question_id)
                                            chat.isSent = False
                                            await database_sync_to_async(chat.save)()
                            elif r_type == 'name' or \
                                r_type == 'phone' or \
                                r_type == 'email' or \
                                r_type == 'question' or \
                                r_type == 'number' :
                                if not chat.isSent:
                                    chat.isSent = True
                                    await database_sync_to_async(chat.save)()
                            
                                    message_wamid = send_message(message_content=message,
                                                    to=chat.conversation_id,
                                                    bearer_token=channel.tocken,
                                                    wa_id=channel.phone_number_id,
                                                    chat_id=chat.id,
                                                    platform=platform,
                                                    question=question)
                                    chat_message = await database_sync_to_async(ChatMessage.objects.create)(
                                            conversation_id=await database_sync_to_async(Conversation.objects.get)(conversation_id=conversation_id),
                                            content_type='text',
                                            content=message,
                                            from_message='bot',
                                            wamid=message_wamid['messages'][0]['id']
                                        )
                                    await self.channel_layer.group_send(
                                        self.room_group_name, {
                                            "type": "chat_message",
                                            "content": message,
                                            "content_type": r_type,
                                            "wamid": message_wamid['messages'][0]['id'],
                                            "conversation_id": conversation_id,
                                            "from_bot": "True",
                                            "message_id": chat_message.message_id,
                                            "created_at": f"{chat_message.created_at}",
                                            "from_flow":"True",
                                            "front_id": "auto_generated"
                                        }
                                    )
                                    return True
                                else:
                                    user_reply = ''
                                
                                    try:
                                        user_reply = data['content'] #If this raises an error then it means that the response has come from Beam not Whatsapp
                                
                                    except:
                                        
                                        try: #If this raises an error then this means that it is a beam user reply not normal beam text message reply
                                            user_reply = data['entry'][0]['changes'][0]['value']['messages'][0]['text']['body']
                                        
                                        except:
                                            user_reply = data['entry'][0]['changes'][0]['value']['messages'][0]['reply_to']['button_title']
                                    
                                    restart_keywords = await database_sync_to_async(
                                        lambda: [r.keyword for r in RestartKeyword.objects.filter(channel_id=channel.channle_id)]
                                    )()                                    
                                    if user_reply in restart_keywords:
                                        chat.isSent = False
                                        await database_sync_to_async(chat.save)()
                                        await database_sync_to_async(chat.update_state)('start')

                                    elif r_type == 'name' and len(user_reply) > question['maxRange']:
                                        error_message = question['message']['error']
                                        message_wamid = send_message(message_content=error_message,
                                                        to=chat.conversation_id,
                                                        bearer_token=channel.tocken,
                                                        wa_id=channel.phone_number_id,
                                                        chat_id=chat.id,
                                                        platform=platform,
                                                        question=question)
                                        chat_message = await database_sync_to_async(ChatMessage.objects.create)(
                                            conversation_id=await database_sync_to_async(Conversation.objects.get)(conversation_id=conversation_id),
                                            content_type='text',
                                            content=message,
                                            from_message='bot',
                                            wamid=message_wamid['messages'][0]['id']
                                        )
                                        await self.channel_layer.group_send(
                                            self.room_group_name, {
                                                "type": "chat_message",
                                                "content": message,
                                                "content_type": r_type,
                                                "wamid": message_wamid['messages'][0]['id'],
                                                "conversation_id": conversation_id,
                                                "from_bot": "True",
                                                "message_id": chat_message.message_id,
                                                "created_at": f"{chat_message.created_at}",
                                                "from_flow":"True",
                                                "front_id": "auto_generated"
                                            }
                                        )
                                        return True
                                    elif r_type == 'phone' and not validate_phone_number(user_reply):
                                        error_message = question['message']['error']
                                        message_wamid = send_message(message_content=error_message,
                                                        to=chat.conversation_id,
                                                        bearer_token=channel.tocken,
                                                        wa_id=channel.phone_number_id,
                                                        chat_id=chat.id,
                                                        platform=platform,
                                                        question=question)
                                        chat_message = await database_sync_to_async(ChatMessage.objects.create)(
                                            conversation_id=await database_sync_to_async(Conversation.objects.get)(conversation_id=conversation_id),
                                            content_type='text',
                                            content=message,
                                            from_message='bot',
                                            wamid=message_wamid['messages'][0]['id']
                                        )
                                        await self.channel_layer.group_send(
                                            self.room_group_name, {
                                                "type": "chat_message",
                                                "content": message,
                                                "content_type": r_type,
                                                "wamid": message_wamid['messages'][0]['id'],
                                                "conversation_id": conversation_id,
                                                "from_bot": "True",
                                                "message_id": chat_message.message_id,
                                                "created_at": f"{chat_message.created_at}",
                                                "from_flow":"True",
                                                "front_id": "auto_generated"
                                            }
                                        )
                                        return True
                                    elif r_type == 'email' and not validate_email(user_reply):
                                        error_message = question['message']['error']
                                        message_wamid = send_message(message_content=error_message,
                                                        to=chat.conversation_id,
                                                        bearer_token=channel.tocken,
                                                        wa_id=channel.phone_number_id,
                                                        chat_id=chat.id,
                                                        platform=platform,
                                                        question=question)
                                        chat_message = await database_sync_to_async(ChatMessage.objects.create)(
                                            conversation_id=await database_sync_to_async(Conversation.objects.get)(conversation_id=conversation_id),
                                            content_type='text',
                                            content=message,
                                            from_message='bot',
                                            wamid=message_wamid['messages'][0]['id']
                                        )

                                        await self.channel_layer.group_send(
                                            self.room_group_name, {
                                                "type": "chat_message",
                                                "content": message,
                                                "content_type": r_type,
                                                "wamid": message_wamid['messages'][0]['id'],
                                                "conversation_id": conversation_id,
                                                "from_bot": "True",
                                                "message_id": chat_message.message_id,
                                                "created_at": f"{chat_message.created_at}",
                                                "from_flow":"True",
                                                "front_id": "auto_generated"
                                            }
                                        )
                                        return True
                                    elif r_type == 'number' and not str(user_reply).isdigit():
                                        error_message = question['message']['error']
                                        message_wamid = send_message(message_content=error_message,
                                                        to=chat.conversation_id,
                                                        bearer_token=channel.tocken,
                                                        wa_id=channel.phone_number_id,
                                                        chat_id=chat.id,
                                                        platform=platform,
                                                        question=question)
                                        chat_message = await database_sync_to_async(ChatMessage.objects.create)(
                                            conversation_id=await database_sync_to_async(Conversation.objects.get)(conversation_id=conversation_id),
                                            content_type='text',
                                            content=message,
                                            from_message='bot',
                                            wamid=message_wamid['messages'][0]['id']
                                        )
                                        await self.channel_layer.group_send(
                                            self.room_group_name, {
                                                "type": "chat_message",
                                                "content": message,
                                                "content_type": r_type,
                                                "wamid": message_wamid['messages'][0]['id'],
                                                "conversation_id": conversation_id,
                                                "from_bot": "True",
                                                "message_id": chat_message.message_id,
                                                "created_at": f"{chat_message.created_at}",
                                                "from_flow":"True",
                                                "front_id": "auto_generated"
                                            }
                                        )
                                        return True
                                    
                                    else:
                                        chat_message = await database_sync_to_async(ChatMessage.objects.create)(
                                                conversation_id=await database_sync_to_async(Conversation.objects.get)(conversation_id=conversation_id),
                                                content_type='text',
                                                content=user_reply,
                                                from_message=contact_name,
                                                wamid=wamid
                                            )
                                        await self.channel_layer.group_send(
                                            self.room_group_name, {
                                                "type": "chat_message",
                                                "content": user_reply,
                                                "content_type": r_type,
                                                "wamid": wamid,
                                                "conversation_id": conversation_id,
                                                "from_bot": "False",
                                                "message_id": chat_message.message_id,
                                                "created_at": f"{chat_message.created_at}",
                                                "from_flow":"True",
                                                "front_id": "auto_generated"
                                            }
                                        )
                                        attr, created = await database_sync_to_async(Attribute.objects.get_or_create)(key=attribute_name, chat_id=chat.id)
                                        attr.value = user_reply
                                        await database_sync_to_async(chat.update_state)(next_question_id)
                                        chat.isSent = False
                                        await database_sync_to_async(attr.save)()
                                        await database_sync_to_async(chat.save)()
                            elif r_type == 'document':
                                message_wamid = send_message(message_content=message,
                                                to=chat.conversation_id,
                                                bearer_token=channel.tocken,
                                                type='document',
                                                source=question['source'],
                                                beem_media_id=question.get('beem_media_id'),
                                                wa_id=channel.phone_number_id,
                                                chat_id=chat.id,
                                                platform=platform,
                                                question=question)
                                chat_message = await database_sync_to_async(ChatMessage.objects.create)(
                                    conversation_id=await database_sync_to_async(Conversation.objects.get)(conversation_id=conversation_id),
                                    content_type=r_type,
                                    media_url = question['source'],
                                    caption=message,
                                    from_message='bot',
                                    wamid=message_wamid['messages'][0]['id']
                                )
                                
                                await self.channel_layer.group_send(
                                    self.room_group_name, {
                                        "type": "chat_message_document",
                                        "conversation_id": conversation_id,
                                        "content": '',
                                        "caption": message,
                                        "content_type": r_type,
                                        "from_bot": "True",
                                        "wamid": message_wamid['messages'][0]['id'],
                                        "message_id": chat_message.message_id,
                                        "created_at": f"{chat_message.created_at}",
                                        "media_url":chat_message.media_url,
                                        "from_flow":"True",
                                        "front_id": "auto_generated"
                                    }
                                )
                            elif r_type == 'image':
                                message_wamid = send_message(message_content=message,
                                                to=chat.conversation_id,
                                                bearer_token=channel.tocken,
                                                wa_id=channel.phone_number_id,
                                                type='image',
                                                source=question['source'],
                                                beem_media_id=question.get('beem_media_id'), 
                                                chat_id=chat.id,
                                                platform=platform,
                                                question=question)

                                chat_message = await database_sync_to_async(ChatMessage.objects.create)(
                                    conversation_id=await database_sync_to_async(Conversation.objects.get)(conversation_id=conversation_id),
                                    content_type=r_type,
                                    media_url = question['source'],
                                    caption=message,
                                    from_message='bot',
                                    wamid=message_wamid['messages'][0]['id']
                                )
                                
                                await self.channel_layer.group_send(
                                    self.room_group_name, {
                                        "type": "chat_message_document",
                                        "conversation_id": conversation_id,
                                        "content": '',
                                        "caption": message,
                                        "content_type": r_type,
                                        "from_bot": "True",
                                        "wamid": message_wamid['messages'][0]['id'],
                                        "message_id": chat_message.message_id,
                                        "created_at": f"{chat_message.created_at}",
                                        "media_url":chat_message.media_url,
                                        "from_flow":"True",
                                        "front_id": "auto_generated"
                                    }
                                )
                            elif r_type == 'audio' or r_type == 'sticker' or r_type == 'video':

                                message_wamid = send_message(message_content=message,
                                                to=chat.conversation_id,
                                                bearer_token=channel.tocken,
                                                wa_id=channel.phone_number_id,
                                                type=r_type,
                                                source=question['source'], 
                                                chat_id=chat.id,
                                                platform=platform,
                                                question=question)
                                chat_message = await database_sync_to_async(ChatMessage.objects.create)(
                                    conversation_id=await database_sync_to_async(Conversation.objects.get)(conversation_id=conversation_id),
                                    content_type=r_type,
                                    media_url = question['source'],
                                    caption=message,
                                    from_message='bot',
                                    wamid=message_wamid['messages'][0]['id']
                                )
                                
                                await self.channel_layer.group_send(
                                    self.room_group_name, {
                                        "type": "chat_message_document",
                                        "conversation_id": conversation_id,
                                        "content": '',
                                        "caption": message,
                                        "content_type": r_type,
                                        "from_bot": "True",
                                        "wamid": message_wamid['messages'][0]['id'],
                                        "message_id": chat_message.message_id,
                                        "created_at": f"{chat_message.created_at}",
                                        "media_url":chat_message.media_url,
                                        "from_flow":"True",
                                        "front_id": "auto_generated"
                                    }
                                )

                
                            elif r_type == 'contact' or r_type == 'location':
                                message_wamid = send_message(message_content=message,
                                                to=chat.conversation_id,
                                                bearer_token=channel.tocken,
                                                wa_id=channel.phone_number_id,
                                                type=r_type,
                                                chat_id=chat.id,
                                                platform=platform,
                                                question=question)
                            # print(next_question_id)
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
                                
                                if not next_question_id in [c[3] for c in choices_with_next]: #This means if the next question wasn't changed with any conditions then it'll take the default value
                                    next_question_id = default_state
                            elif r_type == 'detect_language':
                                pass    
                            else:
                                message_wamid = send_message(message_content=message,
                                                to=chat.conversation_id,
                                                bearer_token=channel.tocken,
                                                wa_id=channel.phone_number_id,
                                                chat_id=chat.id,
                                                platform=platform,
                                                question=question,
                                                )
                                chat_message = await database_sync_to_async(ChatMessage.objects.create)(
                                    conversation_id=await database_sync_to_async(Conversation.objects.get)(conversation_id=conversation_id),
                                    content_type='text',
                                    content=message,
                                    from_message='bot',
                                    wamid=message_wamid['messages'][0]['id']
                                )
                                await self.channel_layer.group_send(
                                    self.room_group_name, {
                                        "type": "chat_message",
                                        "content": message,
                                        "content_type": r_type,
                                        "wamid": message_wamid['messages'][0]['id'],
                                        "conversation_id": conversation_id,
                                        "from_bot": "True",
                                        "message_id": chat_message.message_id,
                                        "created_at": f"{chat_message.created_at}",
                                        "from_flow":"True",
                                        "front_id": "auto_generated"
                                    }
                                )
                            await database_sync_to_async(chat.update_state)(next_question_id)
                            if not next_question_id or next_question_id == 'end':
                                return True
                    else:
                        return False

            case "message_status":
                message_id = text_data_json['message_id']
                status_message = text_data_json['status']

                await self.channel_layer.group_send(
                    self.room_group_name, {
                        "type": "chat_message_status",
                        "conversation_id": conversation_id,
                        "content_type": content_type,
                        "message_id":message_id,
                        "status_message": status_message
                    }
                )
            # handel receive template message
            case "template":
                await self.update_state_conversation(conversation_id)
                front_id = text_data_json['front_id']
                content = text_data_json["content"]
                template_info = text_data_json['template_info']
                created_at = text_data_json['created_at']
                channel_id = await self.get_channel(self.channel_id)
                url = f"https://graph.facebook.com/v22.0/{channel_id.phone_number_id}/messages"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {channel_id.tocken}"
                }
                template_data = json.dumps(template_info)   
                response = requests.post(url, headers=headers, data=template_data)
                data = json.loads(response.content.decode())
                try:
                    template_wamid = data['messages'][0]['id']
                    message_id = await self.create_chat_message(conversation_id, self.user, content_type, content, template_wamid)
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message",
                            "conversation_id": conversation_id,
                            "content": content,
                            "content_type": content_type,
                            "from_bot":from_bot,
                            "wamid":template_wamid,
                            "front_id":front_id,
                            "message_id":message_id,
                            "from_flow":"False",
                            "created_at": created_at
                        }
                    )
                except:
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "error_message",
                            "error": f"Template message not sent{response.content.decode()}"
                        }
                    )

            # handel receive voice message
            case "audio":
                await self.update_state_conversation(conversation_id)
                caption = text_data_json["caption"]
                if from_bot == "True":
                    media_name = text_data_json["media_name"]
                    front_id = text_data_json['front_id']
                    phonenumber_id =await self.get_waid(conversation_id)
                    phonenumber = await self.get_phonenumber(conversation_id)
                    token = await self.get_token(conversation_id)
                    content = text_data_json["content"]
                    decoded_audio = base64.b64decode(content)
                    # output_folder = 'media/chat_message/'
                    output_folder = f'/var/www/html/media/chat_message/'
                    file_path = os.path.join(output_folder, media_name)
                    with open(file_path, "wb") as image_file:
                        image_file.write(decoded_audio)
                    message_wamid =  process_and_send_voice_note(file_path, phonenumber_id, token[7:], phonenumber, bitrate_kbps=24)
                    conversation_id = await self.get_conversation(conversation_id)
                    message_id = await self.create_chat_image(conversation_id, self.user, content_type, caption, message_wamid, f"https://chatbot.icsl.me/media/chat_message/{media_name}")
                    # message_id = await self.create_chat_image(self.conversation_id, content_type, caption, wamid, f"http://127.0.0.1:8000/media/chat_message/{media_name}")
                    # Send image to room group
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message_audio",
                            "conversation_id": conversation_id,
                            "content": content,
                            "caption": caption,
                            "content_type": content_type,
                            "from_bot": from_bot,
                            "wamid": message_wamid,
                            "message_id": message_id,
                            "from_flow":"False",
                            "front_id": front_id
                        }
                    )
                else:
                    media_url = text_data_json["media_url"]
                    created_at = text_data_json["created_at"]
                    message_id = text_data_json["message_id"]
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message_audio",
                            "conversation_id": conversation_id,
                            "caption": caption,
                            "content_type": content_type,
                            "from_bot": from_bot,
                            "wamid": 'message_wamid',
                            "message_id": message_id,
                            "media_url" : media_url,
                            "from_flow":"True",
                            "created_at": created_at
                        }
                    )

            # handel receive image
            case 'image':
                await self.update_state_conversation(conversation_id)
                caption = text_data_json["caption"]
                if from_bot == "True":
                    media_name = text_data_json["media_name"]
                    message_wamid = send_message(
                        message_content= caption,
                        to= await self.get_phonenumber(conversation_id),
                        wa_id= await self.get_waid(conversation_id),
                        bearer_token= await self.get_token(conversation_id),
                        chat_id=conversation_id,
                        platform="whatsapp",
                        question='',
                        type="image",
                        source=f"https://chatbot.icsl.me/media/chat_message/{media_name}",
                    )
                    content = text_data_json["content"]
                    front_id = text_data_json['front_id']
                    decoded_image = base64.b64decode(content)
                    # output_folder = 'media/chat_message'
                    output_folder = '/var/www/html/media/chat_message'
                    file_path = os.path.join(output_folder, media_name)
                    with open(file_path, "wb") as image_file:
                        image_file.write(decoded_image)
                    conversation_id = await self.get_conversation(conversation_id)
                    message_id = await self.create_chat_image(conversation_id, self.user, content_type, caption, message_wamid['messages'][0]['id'], f"https://chatbot.icsl.me/media/chat_message/{media_name}")
                    # message_id = await self.create_chat_image(self.conversation_id, content_type, caption, wamid, f"http://127.0.0.1:8000/media/chat_message/{media_name}")
                    # Send image to room group
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message_image",
                            "conversation_id": conversation_id,
                            "content": content,
                            "caption": caption,
                            "content_type": content_type,
                            "from_bot": from_bot,
                            "wamid": message_wamid['messages'][0]['id'],
                            "message_id": message_id,
                            "from_flow":"False",
                            "front_id": front_id
                        }
                    )
                else:
                    media_url = text_data_json["media_url"]
                    created_at = text_data_json["created_at"]
                    message_id = text_data_json["message_id"]
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message_image",
                            "conversation_id": conversation_id,
                            "caption": caption,
                            "content_type": content_type,
                            "from_bot": from_bot,
                            "wamid": 'wamid',
                            "message_id": message_id,
                            "media_url" : media_url,
                            "from_flow":"True",
                            "created_at": created_at
                        }
                    )
            # handel receive video
            case 'video':
                await self.update_state_conversation(conversation_id)
                caption = text_data_json["caption"]
                if from_bot == "True":
                    media_name = text_data_json["media_name"]
                    message_wamid = send_message(
                        message_content= caption,
                        to= await self.get_phonenumber(conversation_id),
                        wa_id= await self.get_waid(conversation_id),
                        bearer_token= await self.get_token(conversation_id),
                        chat_id= conversation_id,
                        platform="whatsapp",
                        question={"label":caption},
                        type="video",
                        source=f"https://chatbot.icsl.me/media/chat_message/{media_name}",
                    )
                    front_id = text_data_json["front_id"]
                    content = text_data_json["content"]
                    decoded_video = base64.b64decode(content)
                    output_folder = '/var/www/html/media/chat_message'
                    file_path = os.path.join(output_folder, media_name)
                    with open(file_path, "wb") as image_file:
                        image_file.write(decoded_video)
                    conversation_id = await self.get_conversation(conversation_id)
                    message_id = await self.create_chat_image(conversation_id, self.user, content_type, caption, message_wamid['messages'][0]['id'], f"https://chatbot.icsl.me/media/chat_message/{media_name}")
                    # message_id = await self.create_chat_image(self.conversation_id, content_type, caption, wamid, f"http://127.0.0.1:8000/media/chat_message/{media_name}")
                    # Send image to room group
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message_video",
                            "conversation_id": conversation_id,
                            "content": content,
                            "caption": caption,
                            "content_type": content_type,
                            "from_bot": from_bot,
                            "wamid": message_wamid['messages'][0]['id'],
                            "message_id": message_id,
                            "from_flow":"False",
                            "front_id": front_id
                        }
                    )
                else:
                    media_url = text_data_json["media_url"]
                    created_at = text_data_json["created_at"]
                    message_id = text_data_json["message_id"]
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message_image",
                            "conversation_id": conversation_id,
                            "caption": caption,
                            "content_type": content_type,
                            "from_bot": from_bot,
                            "wamid": 'wamid',
                            "message_id": message_id,
                            "media_url" : media_url,
                            "from_flow":"True",
                            "created_at": created_at
                        }
                    )
            # Send document to room group
            case 'document':
                await self.update_state_conversation(conversation_id)
                caption = text_data_json["caption"]
                if from_bot == "True":
                    media_name = text_data_json["media_name"]
                    message_wamid = send_message(
                        message_content= caption,
                        to= await self.get_phonenumber(conversation_id),
                        wa_id= await self.get_waid(conversation_id),
                        bearer_token= await self.get_token(conversation_id),
                        chat_id= conversation_id,
                        platform="whatsapp",
                        type="document",
                        source=f"https://chatbot.icsl.me/media/chat_message/{media_name}",
                    )
                    content = text_data_json["content"]
                    front_id = text_data_json["front_id"]
                    decoded_document = base64.b64decode(content)
                    output_folder = '/var/www/html/media/chat_message'
                    file_path = os.path.join(output_folder, media_name)
                    with open(file_path, "wb") as image_file:
                        image_file.write(decoded_document)
                    conversation_id = await self.get_conversation(conversation_id)
                    message_id = await self.create_chat_image(conversation_id, self.user, content_type, caption, message_wamid['messages'][0]['id'], f"https://chatbot.icsl.me/media/chat_message/{media_name}")
                    # Send image to room group
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message_document",
                            "conversation_id": conversation_id,
                            "content": content,
                            "caption": caption,
                            "content_type": content_type,
                            "from_bot": from_bot,
                            "wamid": message_wamid['messages'][0]['id'],
                            "message_id": message_id,
                            "from_flow":"False",
                            "front_id": front_id
                        }
                    )
                else:
                    media_url = text_data_json["media_url"]
                    created_at = text_data_json["created_at"]
                    message_id = text_data_json["message_id"]
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message_image",
                            "conversation_id": conversation_id,
                            "caption": caption,
                            "content_type": content_type,
                            "from_bot": from_bot,
                            "wamid": 'wamid',
                            "message_id": message_id,
                            "media_url" : media_url,
                            "from_flow":"True",
                            "created_at": created_at
                        }
                    )
            # Send message to room group
            case 'text':
                await self.update_state_conversation(conversation_id)
                content = text_data_json["content"]
                created_at = text_data_json['created_at']
                if from_bot == "False":
                    message_id = text_data_json["message_id"]
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message",
                            "conversation_id": conversation_id,
                            "content": content,
                            "content_type": content_type,
                            "from_bot":from_bot,
                            "wamid":'wamid',
                            "message_id":message_id,
                            "from_flow":"True",
                            "created_at": created_at
                        }
                    )
                else:
                    # status = text_data_json['status']
                    message_wamid = send_message(
                        message_content=content,
                        to= await self.get_phonenumber(conversation_id),
                        wa_id= await self.get_waid(conversation_id),
                        bearer_token= await self.get_token(conversation_id),
                        chat_id= conversation_id,
                        platform="whatsapp",
                        question='statment'
                    )
                    front_id = text_data_json['front_id']
                    message_id = await self.create_chat_message(conversation_id, self.user, content_type, content, message_wamid['messages'][0]['id'])
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "chat_message",
                            "conversation_id": conversation_id,
                            "content": content,
                            "content_type": content_type,
                            "from_bot":from_bot,
                            "wamid":message_wamid['messages'][0]['id'],
                            "message_id":message_id,
                            "created_at": created_at,
                            "from_flow":"False",
                            "front_id": front_id
                        }
                    )

    async def chat_message_image(self, event):
        from_flow = event["from_flow"]
        if from_flow == "True":
            content_type = event["content_type"]
            created_at = event["created_at"]
            media_url = event["media_url"]
        else:
            content_type = "message_status"
            created_at = ""
            media_url = ""
        wamid = event["wamid"]
        message_id = event["message_id"]
        from_bot = event["from_bot"]
        caption = event["caption"]
        conversation_id = event["conversation_id"]
        

        if from_bot == "False":
            media_url = event["media_url"]
            created_at = event["created_at"]
            await self.send(text_data=json.dumps({
                    "type":"message",
                    "conversation_id": conversation_id,
                    "media_url":media_url,
                    "caption":caption,
                    "content_type": content_type,
                    "wamid": wamid,
                    "message_id":message_id,
                    "created_at":created_at,
                    "from_bot":"False",
                    "is_successfully":"true"
                }))
        else:
            front_id = event["front_id"]
            await self.send(text_data=json.dumps({
                    "type": "message",
                    "content_type":content_type,
                    "message_id": message_id,
                    "wamid": wamid,
                    "conversation_id": conversation_id,
                    "front_id": front_id,
                    "created_at":created_at,
                    "media_url": media_url,
                    "from_bot":"True",
                    "is_successfully": "true",
                }))
            
    async def chat_message_video(self, event):
        from_flow = event["from_flow"]
        if from_flow == "True":
            content_type = event["content_type"]
            created_at = event["created_at"]
            media_url = event['media_url']
        else:
            content_type = "message_status"
            created_at = ""
            media_url = ""
        wamid = event["wamid"]
        message_id = event["message_id"]
        from_bot = event["from_bot"]
        caption = event["caption"]
        conversation_id = event["conversation_id"]       
        if from_bot == "False":
            created_at = event["created_at"]
            media_url = event["media_url"]
            await self.send(text_data=json.dumps({
                    "type":"message",
                    "conversation_id": conversation_id,
                    "media_url":media_url,
                    "caption":caption,
                    "content_type": content_type,
                    "wamid": wamid,
                    "message_id":message_id,
                    "created_at":created_at,
                    "from_bot":"False",
                    "is_successfully":"true"
                }))
        else:
            front_id = event["front_id"]
            await self.send(text_data=json.dumps({
                    "type": "message",
                    "content_type":content_type,
                    "message_id": message_id,
                    "wamid": wamid,
                    "conversation_id": conversation_id,
                    "front_id": front_id,
                    "created_at":created_at,
                    "media_url": media_url,
                    "from_bot":"True",
                    "is_successfully": "true",
                }))
            
    async def chat_message_audio(self, event):
        from_flow = event["from_flow"]
        if from_flow == "True":
            content_type = event["content_type"]
            created_at = event["created_at"]
            media_url = event["media_url"]
        else:
            content_type = "message_status"
            created_at = ""
            media_url = ""
        wamid = event["wamid"]
        message_id = event["message_id"]
        from_bot = event["from_bot"]
        caption = event["caption"]
        conversation_id = event["conversation_id"]
        
        if from_bot == "False":
            created_at = event["created_at"]
            media_url = event["media_url"]
            await self.send(text_data=json.dumps({
                    "type":"message",
                    "conversation_id": conversation_id,
                    "media_url":media_url,
                    "caption":caption,
                    "content_type": content_type,
                    "wamid": wamid,
                    "message_id":message_id,
                    "created_at":created_at,
                    "from_bot":"False",
                    "is_successfully":"true"
                }))
        else:
            front_id = event['front_id']
            await self.send(text_data=json.dumps({
                    "type": "message",
                    "content_type":content_type,
                    "message_id": message_id,
                    "wamid": wamid,
                    "conversation_id": conversation_id,
                    "front_id": front_id,
                    "created_at":created_at,
                    "media_url": media_url,
                    "from_bot":"True",
                    "is_successfully": "true",
                }))      
                
    async def chat_message_document(self, event):
        from_flow = event["from_flow"]
        if from_flow == "True":
            content_type = event["content_type"]
            created_at = event["created_at"]
            media_url = event["media_url"]
        else:
            content_type = "message_status"
            created_at = ""
            media_url = ""
        wamid = event["wamid"]
        message_id = event["message_id"]
        from_bot = event["from_bot"]
        caption = event["caption"]
        conversation_id = event["conversation_id"]

        if from_bot == "False":
            created_at = event["created_at"]
            media_url = event["media_url"]
            await self.send(text_data=json.dumps({
                    "type":"message",
                    "conversation_id": conversation_id,
                    "media_url":media_url,
                    "caption":caption,
                    "content_type": content_type,
                    "wamid": wamid,
                    "message_id":message_id,
                    "created_at":created_at,
                    "from_bot":"False",
                    "is_successfully":"true"
                }))
        else:
            front_id = event['front_id']
            await self.send(text_data=json.dumps({
                    "type": "message",
                    "content_type":content_type,
                    "message_id": message_id,
                    "wamid": wamid,
                    "conversation_id": conversation_id,
                    "front_id": front_id,
                    "created_at":created_at,
                    "media_url": media_url,
                    "from_bot":"True",
                    "is_successfully": "true",
                }))
            
    # Receive message from room group
    async def chat_message(self, event):
        from_flow = event["from_flow"]
        created_at = event["created_at"]
        if from_flow == "True":
            content_type = event["content_type"]
            created_at = event["created_at"]
        else:
            content_type = "message_status"
            created_at = ""
        content = event["content"]
        from_bot = event["from_bot"]
        wamid = event['wamid']
        conversation_id = event["conversation_id"]

        message_id_ = event["message_id"]
        created_at = event["created_at"]
        if from_bot == "False":
            await self.send(text_data=json.dumps({
                "type":"message",
                "message_id": message_id_,
                "content":content,
                "content_type":content_type,
                "conversation_id": conversation_id,
                "wamid":wamid,
                "created_at":created_at,
                "from_bot":"False",
                "is_successfully":"true"
            }))
        else:
            front_id = event["front_id"]
            await self.send(text_data=json.dumps({
                    "type": "message",
                    "content":content,
                    "content_type":content_type,
                    "message_id": message_id_,
                    "wamid": wamid,
                    "conversation_id": conversation_id,
                    "front_id": front_id,
                    "created_at":created_at,
                    "from_bot":"True",
                    "is_successfully": "true",
                }))
    async def error_message(self, event):
        error = event["error"]

        await self.send(text_data=json.dumps({
            "type":"message",
            "error": error,
            "is_successfully":"False"
        }))
    async def chat_message_status(self, event):
        content_type = event["content_type"] 
        conversation_id = event["conversation_id"]
        message_id_ = event["message_id"]
        status_message = event["status_message"]

        await self.send(text_data=json.dumps({
                "message_id": message_id_,
                "conversation_id": conversation_id,
                "content_type": content_type,
                "status_message" : status_message
                }))

           
    @database_sync_to_async
    def get_last_message(self, conversation_id):
        conversation = Conversation.objects.filter(conversation_id=conversation_id).first()
        message = conversation.chatmessage_set.exclude(from_message ='bot').order_by("-created_at").first()
        return message
    
    @database_sync_to_async
    def create_chat_message(self, conversation_id, user, content_type, content, wamid):
        conversation = Conversation.objects.filter(conversation_id=conversation_id).first()
        chat_message = ChatMessage.objects.create(
            conversation_id = conversation,
            user_id = user,
            content_type = content_type,
            content = content,
            wamid = wamid,
            # from_message = from_bot
        )
        return chat_message.message_id
    
    @database_sync_to_async
    def create_chat_image(self, conversation_id, user, content_type, caption, wamid, media_url):
        conversation = Conversation.objects.filter(conversation_id=conversation_id).first()
        chat_message = ChatMessage.objects.create(
            conversation_id = conversation,
            user_id = user,
            content_type = content_type,
            caption = caption,
            wamid = wamid,
            media_url = media_url,
        )
        return chat_message.message_id
    
    
    @database_sync_to_async
    def get_messages(self, conversation_id):
        conversation_id = Conversation.objects.filter(conversation_id=conversation_id).first()
        messages = conversation_id.chatmessage_set.all().order_by("created_at")
        serializer_messages = ChatMessageSerializer(messages, many=True)
        return serializer_messages.data

    @database_sync_to_async
    def get_phonenumber(self, conversation_id):
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        phonenumber = conversation.contact_id.phone_number
        return phonenumber
    
    @database_sync_to_async
    def get_waid(self, conversation_id):
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        waid = conversation.channle_id.phone_number_id
        return waid

    @database_sync_to_async
    def get_token(self, conversation_id):
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        tocken = conversation.channle_id.tocken
        return tocken

    @database_sync_to_async
    def create_file(self, file_name):
        file = UploadImage.objects.create(image_file=file_name)
        return file.get_absolute_url

    @database_sync_to_async
    def get_phonenumber_id(self, conversation_id):
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        phonenumber_id = conversation.channle_id.phone_number_id
        return phonenumber_id
          
    @database_sync_to_async
    def get_conversation(self, conversation_id):
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        conversation.updated_at = timezone.now()
        conversation.save()
        return conversation.conversation_id

    @database_sync_to_async
    def get_conversations(self, channel_id):
        user = CustomUser.objects.get(id=self.user.id)
        permissions = list(user.get_all_permissions())
        if 'api.visibility all conversations' in permissions:
            conversation = Conversation.objects.filter(channle_id=channel_id)
            # conversation = channel.conversation_set.all().order_by('-updated_at')
            serializer = ConversationSerializer(conversation, many=True)
            return serializer.data
        else:
            conversation = Conversation.objects.filter(channle_id=channel_id, user=self.user)
            # conversation = channel.conversation_set.all().order_by('-updated_at')
            serializer = ConversationSerializer(conversation, many=True)
            return serializer.data
    @database_sync_to_async
    def get_channel(self, channel_id):
        channel = Channle.objects.get(channle_id = channel_id)
        return channel
    
    @database_sync_to_async
    def get_message(self, message_id):
        message = ChatMessage.objects.get(message_id = message_id)
        message.status_message = 'delivered'
        message.save()
        return message
    
    @database_sync_to_async
    def return_conversation(self, con_id):
        conv = Conversation.objects.get(conversation_id=con_id)
        conv.status = 'lock'
        return conv.save()
    
    @database_sync_to_async
    def change_status(self, conversation_id, from_bot):
        if from_bot == 'False':
            c =Conversation.objects.get(conversation_id=conversation_id)
            c.status = 'open'
            c.save()
        return True
    
    @database_sync_to_async
    def update_state_conversation(self, conversation_id):
        c =Conversation.objects.get(conversation_id=conversation_id)
        c.state = "end_bot"
        return c.save()

    async def bot_integration_error(self, event):
        message = event["Message"]

        await self.send(text_data=json.dumps({
            "type":"message",
            "message": message,
            "is_successfully":"False"
        }))

    async def bot_integration(self, event):
        message = event["Message"]

        await self.send(text_data=json.dumps({
            "type":"message",
            "message": message,
            "is_successfully":"True"
        }))

    @database_sync_to_async
    def get_channel(self, channel):
        channel = Channle.objects.get(channle_id = channel)
        return channel

