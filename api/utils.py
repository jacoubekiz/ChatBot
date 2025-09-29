import json
import requests
import ast
import re
from .models import Attribute
from django.db import connection
from urllib.parse import urlparse
import os
from .models import *
from django_redis import get_redis_connection
import websocket
from django.core.files.base import ContentFile
from bot.settings import TOKEN_ACCOUNTS
import mimetypes

bearer_token = 'Bearer EAAJCCh5AS8gBOyUjN8UtrTa9p4apLsoMMOTmEJL3ur2TJbniZBOAPReVh6TrmZBMiwg7Ixdqr06H8VTQTNImcBNuZBmbBlcZCKYmMNZCjWFHIjnlQ7ByKZCMjxhLxaCYn7ZCf3U7VGgqyMi4chCfjb899WXV0HBFlEnPhWbZBQUaL54ZAikhNZCOP3pRuGu7YdUREv1WyZAc8w8vAc28gN6yObFeXmVCQL4ZBMxcM1ByZAvEZD'

def read_json(file_path, encoding='utf-8'):
    try:
        with open(file_path, 'r', encoding=encoding) as file:
            data = json.load(file)
            return data
    except FileNotFoundError:
        return
    except json.JSONDecodeError as e:
        return

def show_response(question, questions):
    current_response = ''
    choices_with_next = None
    next_question_id = None
    choices = None
    r_type = None
    current_response += question['label'] + '\n'
    import itertools
    try:
        options = question['options']
    except:
        options = None
    # try:
    if  options :
        if question['type'] == 'smart_question':
            choices_with_next = [(option['value'], option['id'], option['next']['target'], option['keywordType'], option['smartKeywords']) for option in question['options']]
        
        elif question['type'] == 'condition' or question['type'] == 'Condition':
            choices_with_next = [(option['ConditionValue'], option['value'], option['id'], option['next']['target']) for option in question['options']]

        elif question['type'] == 'button':
            choices_with_next = [(option['value'], option['id'], option['next']['target']) for option in question['options']]
            choices = [c[0] for c in choices_with_next]
        

        elif question['type'] == 'list':
            choices_with_next = [(option['value'], option['id'], option['next']['target']) for option in question['options']]
            choices = [c[0] for c in choices_with_next]
            
        elif question['type'] == 'api':
            choices_with_next = [(option['value'], option['id'], option['next']['target']) for option in question['options']]
            next_id = [next_question['next']['target'] for next_question in question['options']]
            choices = [c[0] for c in choices_with_next]
            
        elif question['type'] == 'calendar':
            choices_with_next = [(option['value'], option['next']['target']) for option in question['options']]
            choices = [c[0] for c in choices_with_next]

        elif question['type'] == 'detect_language':
            choices_with_next = [(option['value'], option['next']['target']) for option in question['options']]
            choices = [c[0] for c in choices_with_next]
    else:
        next_id = ''
        next_question_id = question['next']['target']

    r_type = question['type']
    try:
        question_attribute = question['attribute_name']
    except:
        question_attribute = ''
    if current_response:
        return current_response, next_question_id, choices_with_next, choices, r_type, question_attribute
    else:
        return 'Chat Ended'

def change_occurences(content, pattern, chat_id, sql=False):
    matches = re.findall(pattern, content)
    for match in matches:
        try:
            attr = Attribute.objects.get(key=match, chat_id = chat_id)
            if sql:
                
                if not attr.value.isdigit():
                    replacement_word = f'{attr.value}'
                else:
                    replacement_word = attr.value
            else:
                replacement_word = attr.value

            content = content.replace(f'{{{{{match}}}}}', replacement_word)
        except:
            if sql:
                if match == "phone":
                    chat = Chat.objects.get(id=chat_id)
                    content = content.replace(f'{{{{{match}}}}}', chat.conversation_id)
    return content
        

def check_sql_condition(sql_condition):
    with connection.cursor() as cursor:
        try:
            cursor.execute(f"SELECT CASE WHEN {sql_condition} THEN 1 ELSE 0 END")
            result = cursor.fetchone()[0]
            return bool(result)
        except Exception as e:
            return f"Error executing SQL condition: {e}"

def send_message(version = '18.0',
                wa_id = '108253965410678',
                bearer_token = bearer_token,
                messaging_product = 'whatsapp',
                to = '966552345566',
                message_content=None,
                choices=None,
                type='text',
                header=None,
                footer=None,
                interaction_type=None,
                source=None,
                chat_id=None,
                platform='whatsapp',
                beem_media_id=None,
                preview_url : bool = True,
                question=None,):
    
    message_content = change_occurences(message_content, pattern=r'\{\{(\w+)\}\}', chat_id=chat_id, sql=True)
    if platform =='whatsapp':
        url = f"https://graph.facebook.com/v{version}/{wa_id}/messages"
        
        if type == 'interactive':

            if interaction_type == 'list':
                
                sections = question['sections']
                for section in sections:
                    # Rename 'options' to 'rows'
                    section['rows'] = section.pop('options')
                    section.pop('id')
                    for row in section['rows']:
                        # Rename 'value' to 'title'
                        row['title'] = row.pop('value')
                        # Remove 'next'
                        if 'next' in row:
                            del row['next']
                payload = json.dumps(
                    {
                        "messaging_product": f"{messaging_product}",
                        "recipient_type": "individual",
                        "to": f"{to}",
                        "type": f"{type}",
                        "interactive": {
                            "type": interaction_type,
                            "header": question.get('header'), 
                            "body": {
                                "text": f"{message_content}"
                            },
                            "footer": {
                                "text": f"{footer}"
                            },
                            "action": {
                                "button": "Send",
                                "sections": sections
                            }
                        }
                    })
                
     
            elif interaction_type == 'button':
                buttons = []
                rows = []
                if len(choices) > 3:
                    title = "message_content"
                    for index, choice in enumerate(choices):
                        row = {
                            "id":f"unique-id-{index}",
                            "title":choice,
                            
                        }
                        rows.append(row)
                        if index == 9:
                            break
                    sections = [{"title":title, "rows":rows}]
                    
                    payload = json.dumps(
                        {
                            "messaging_product": f"{messaging_product}",
                            "recipient_type": "individual",
                            "to": f"{to}",
                            "type": f"{type}",
                            "interactive": {
                                "type": "list",
                                "body": {
                                    "text": f"{message_content}"
                                },
                                "action": {
                                    "button": "Send",
                                    "sections": sections
                                }
                            }
                        })
                    

                else:
                    for index, choice in enumerate(choices):
                        button = {
                            "type": "reply",
                            "reply": {
                                "id": f"unique-id-{index}",
                                "title": choice
                            }
                        }
                        buttons.append(button)
                    payload = json.dumps(
                        {
                            "messaging_product": "whatsapp",
                            "recipient_type": "individual",
                            "to": f"{to}",
                            "type": "interactive",
                            "interactive": {
                                "type": "button",
                                "body": {
                                    "text": f"{message_content}"
                                },
                                "action": {
                                    "buttons": buttons
                                }
                            }
                        }
                    )

        elif type == 'document':
            filename = os.path.basename(urlparse(source).path)
            payload = json.dumps({
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": f"{to}",
                    "type": "document",
                    "document": {
                        "link": f"{source}",
                        "caption": f"{message_content}",
                        "filename" :f"{filename}"
                    }
                })

        elif type == 'image':
            payload = json.dumps({
                "messaging_product": f"{messaging_product}",
                "recipient_type": "individual",
                "to": f"{to}",
                "type": f"{type}",
                "image": {
                    "link": f"{source}",
                    "caption": f"{message_content}"
                }
            })

        elif type == 'video':
            payload = json.dumps({
                "messaging_product": f"{messaging_product}",
                "recipient_type": "individual",
                "to": f"{to}",
                "type": type,
                "video": {
                    "link": source,
                    "caption" : question.get('label')
                }
            })

        
        elif type == 'contact':
            payload = json.dumps(
            {
                "messaging_product": "whatsapp",
                "to": f"{to}",
                "type": "contacts",
                "contacts": [
                    {
                    "emails": [
                        {
                            "email": question.get('contact').get('email'),
                        }
                    ],
                    "name": {
                        "formatted_name" : question.get('contact').get('name').get('formattedName'),    
                        "first_name" : question.get('contact').get('name').get('firstName'),    
                        "last_name" : question.get('contact').get('name').get('lastName'),    
                        "middle_name" : question.get('contact').get('name').get('middleName'), 
                        "suffix" : question.get('contact').get('name').get('suffix'), 
                        "prefix" : question.get('contact').get('name').get('prefix'), 
                        
                    },
                    "org": {
                        "company": question.get('contact').get('org'),
                    },
                    "phones": [
                        {
                            "phone": question.get('contact').get('phone'),
                        }
                    ],
                    "urls": [
                        {
                            "url": question.get('contact').get('url'),
                        }
                    ]
                }
            ]
            })
        
        elif type == 'audio':
            payload = json.dumps(
                {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": f"{to}",
                "type": type,
                "audio": {
                    "id": source
                }
                }
            )

            
        elif type == 'location':
            payload = json.dumps(
                {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": f"{to}",
                    "type": type,
                    "location": question['location']
                }
            )


        elif type == 'sticker':
            payload = json.dumps(
                {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": f"{to}",
                "type": type,
                "audio": {
                    "link": source
                }
                }
            )

        else:

            payload = json.dumps({
            "messaging_product": f"{messaging_product}",
            # "preview_url": question.get('previewUrl'),
            "recipient_type": "individual",
            "to": f"{to}",
            "type": f"{type}",
            "text": {
                "body": f"{message_content}"
            }
            })

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'{bearer_token}'
        }

        response = requests.request("POST", url, headers=headers, data=payload)

        data = json.loads(response.content.decode())
        return data

        
    elif platform == 'beam':
        url = f'https://offapi-sccc-test.rongcloud.net/v1/{wa_id}/message'
        if type == 'interactive':
            if isinstance(choices, list):
                if len(choices) > 3:
                    rows = []
                    for index, choice in enumerate(choices):
                        row = {
                            "id": f'SECTION_1_ROW_{index}_ID',
                            "title": choice,
                            "description": ""
                        }
                        rows.append(row)
                    payload = json.dumps(
                        {
                            "to": f"{to}",
                            "type": f"{type}",
                            "interactive": {
                                "type": "list",
                                "header": {
                                    "type": "text",
                                    "text": f"{header}"
                                },
                                "body": {
                                    "text": f"{message_content}"
                                },
                                "footer": {
                                    "text": f"{footer}"
                                },
                                "action": {
                                    "button": "<BUTTON_TEXT>",
                                    "sections": [
                                        {
                                        "title": "Choose one.",
                                        "rows": rows
                                        },
                                    ]
                                }
                            }
                        }
                    )
                
                else:
                    buttons = []
                    for index, choice in enumerate(choices):
                        button = {
                            "type": "reply",
                            "reply": {
                                "id": f"UNIQUE_BUTTON_ID_{index}",
                                "title": choice
                            }
                        }
                        buttons.append(button)

                    payload = json.dumps(
                        {
                            "to": f"{to}",
                            "type": f"{type}",
                            "interactive": {
                                "type": "button",
                                "header": {
                                    "type": "text",
                                    "text": f"{header}"
                                },
                                "body": {
                                    "text": f"{message_content}"
                                    },
                                "action": {
                                "buttons": buttons
                                }
                            }
                        },
                        # indent=4
                    )

        elif type == 'document' or type =='image':
            payload = json.dumps({
                "to": f"{to}",
                "type": "media",
                "media": {
                    "id" : f"{beem_media_id}"
                }
            })
        elif type == 'yt_video':
            payload = json.dumps({
                "to": f"{to}",
                "type" : "text",
                "text": {
                    "preview_url": preview_url,
                    "body": f'{source}\n{message_content}'
                }
            })
        elif type == 'contact':
            links = [link['value'] for link in source]
            payload = json.dumps({
                "to": f"{to}",
                "type" : "text",
                "text": {
                    "preview_url": preview_url,
                    "body": f"{message_content}\n{'-'.join(links)}"
                }
            })
        else:
            payload = json.dumps({
                "to": f"{to}",
                "type": f"{type}",
                "text": {
                    "body": f"{message_content}"
                    }
            })

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'{bearer_token}'
        }

        response = requests.request("POST", url, headers=headers, data=payload)

        
def validate_email(email):
  return bool(re.search(r"^[\w\.\+\-]+\@[\w]+\.[a-z]{2,3}$", email))

def validate_phone_number(phone_number):
    pattern = r'^\s*(?:\+?(\d{1,3}))?[-. (]*(\d{3})[-. )]*(\d{3})[-. ]*(\d{4})(?: *x(\d+))?\s*$'

    if re.match(pattern, phone_number):
        return True
    else:
        return False
    



v_v = '{"event": {"value": {"messaging_product": "whatsapp", "metadata": {"display_phone_number": "966920025589", "phone_number_id": "157289147477280"}, "contacts": [{"profile": {"name": "Jacoub"}, "wa_id": "966114886645"}], "messages": [{"from": "966114886645", "id": "wamid.HBgMOTY2MTE0ODg2NjQ1FQIAEhggQkUwNEU2ODg0MzI4MDZERTlCMDBGRDAzNkZFRTlDRUIA", "timestamp": "1739867538", "type": "video", "video": {"mime_type": "video/mp4", "sha256": "hekbZhF76pvXHZgbD7XwjeYgulKnS63Q1uNXyB0p7AM=", "id": "602300352596747"}}]}, "field": "messages"}, "medias": [{"url": "https://static-assets-v2.s3.us-east-2.amazonaws.com/uploads/1739867541070_media-0.3026585401465338.mp4", "caption": "", "type": "video", "file_name": "1739867541070_media-0.3026585401465338.mp4"}]}'
image_ = '{"object": "whatsapp_business_account", "entry": [{"id": "395690116951596", "changes": [{"value": {"messaging_product": "whatsapp", "metadata": {"display_phone_number": "15556231998", "phone_number_id": "327799347091553"}, "contacts": [{"profile": {"name": "Jacoub"}, "wa_id": "966114886645"}], "messages": [{"from": "966114886645", "id": "wamid.HBgMOTY2MTE0ODg2NjQ1FQIAEhggNEYxNTRFMzYxQTRGN0JFRUJCOTAwOThCMjI1MUMxOUUA", "timestamp": "1740826863", "type": "image", "image": {"mime_type": "image/jpeg", "sha256": "Uo6PCbjMKoC1CrA4KF9N2fLTnNsZ8fcvTSkGnsdPm0g=", "id": "1127919925801634"}}]}, "field": "messages"}]}]}'
a_a = '{"event": {"value": {"messaging_product": "whatsapp", "metadata": {"display_phone_number": "966920025589", "phone_number_id": "157289147477280"}, "contacts": [{"profile": {"name": "Jacoub"}, "wa_id": "966114886645"}], "messages": [{"from": "966114886645", "id": "wamid.HBgMOTY2MTE0ODg2NjQ1FQIAEhggODdBRjkzREQxMzhDNDAyOTExODJGOTlFNEFENzgyN0MA", "timestamp": "1739951467", "type": "audio", "audio": {"mime_type": "audio/ogg; codecs=opus", "sha256": "0L/d6Pkc7nt+AYl6gtOPOjXeTMuInphwQmKK/d3VNKo=", "id": "1150877063380292", "voice": "True"}}]}, "field": "messages"}, "medias": [{"url": "https://static-assets-v2.s3.us-east-2.amazonaws.com/uploads/1739951469475_media-0.6118878625757445.ogg", "caption": "", "type": "audio", "file_name": "1739951469475_media-0.6118878625757445.ogg"}]}'
d_d = '{"event": {"value": {"messaging_product": "whatsapp", "metadata": {"display_phone_number": "966920025589", "phone_number_id": "157289147477280"}, "contacts": [{"profile": {"name": "Jacoub"}, "wa_id": "966114886645"}], "messages": [{"from": "966114886645", "id": "wamid.HBgMOTY2MTE0ODg2NjQ1FQIAEhggNjAyNzIyNDYyNjUzMDVFMzU4NEExNDMzMkRFRjhGQ0IA", "timestamp": "1739961961", "type": "document", "document": {"filename": "1709124383910_ICS Company Profile AR.pdf", "mime_type": "application/pdf", "sha256": "IHPpJcYjvjTepZTrKvXAacDUge/p0JKvQHOX7t4V1ag=", "id": "1134184264697475"}}]}, "field": "messages"}, "medias": [{"url": "https://static-assets-v2.s3.us-east-2.amazonaws.com/uploads/1739961964386_1709124383910_ICS%20Company%20Profile%20AR.pdf", "caption": "", "type": "document", "file_name": "1739961964386_1709124383910_ICS%20Company%20Profile%20AR.pdf"}]}'
c_c = '{"event": {"value": {"messaging_product": "whatsapp", "metadata": {"display_phone_number": "966920025589", "phone_number_id": "157289147477280"}, "contacts": [{"profile": {"name": "Jacoub"}, "wa_id": "966114886645"}], "messages": [{"context": {"from": "966920025589", "id": "wamid.HBgMOTY2MTE0ODg2NjQ1FQIAERgSNEU2RTg2MDdFQzkzRjM1OURGAA=="}, "from": "966114886645", "id": "wamid.HBgMOTY2MTE0ODg2NjQ1FQIAEhggQUJBNjg1MjA1M0Q3QjFDM0MyQUU4MDc2MzFEOUZEMzYA", "timestamp": "1740040871", "type": "button", "button": {"payload": "موقع المناسبة", "text": "موقع المناسبة"}}]}, "field": "messages"}}'

new_response = '{"object": "whatsapp_business_account", "entry": [{"id": "395690116951596", "changes": [{"value": {"messaging_product": "whatsapp", "metadata": {"display_phone_number": "15556231998", "phone_number_id": "327799347091553"}, "contacts": [{"profile": {"name": "Jacoub"}, "wa_id": "966114886645"}], "messages": [{"from": "966114886645", "id": "wamid.HBgMOTY2MTE0ODg2NjQ1FQIAEhggOTk3MjIzNkJDMjUzRDRGRDMzOTNCOTg3RkY3MzVCQjYA", "timestamp": "1740823930", "text": {"body": "ببل"}, "type": "text"}]}, "field": "messages"}]}]}'

def handel_request_redis(data, account_id):
    # if hub_mode == 'subscribe' and hub_verify_token == TOKEN_ACCOUNTS:

    try:
        redis_client = get_redis_connection()
        redis_client.lpush('data_queue', json.dumps(data))
        f = open(f'content_redis-{account_id}.txt', 'a')
        f.write("recive redis: " + str(data) + '\n')
        raw_data = redis_client.rpop('data_queue')
        test_data = json.loads(raw_data)
        f.write("from redis: " + str(test_data) + '\n' + "new_line-------------------" + '\n')
        if raw_data == None:
            return Response({'message':data}, status=status.HTTP_200_OK)
        else:
            log_entry = json.loads(raw_data)
            value = log_entry.get('entry', [])[0].get('changes', [0])[0].get('value', {})
            statuses = log_entry.get('entry', [])[0].get('changes', [0])[0].get('value', {}).get('statuses', {})
            if statuses:
                message_id = statuses[0].get('id', '')
                status_message = statuses[0].get('status', '')
                display_phone_number = value.get('metadata', '').get('display_phone_number', '')
                channel = Channle.objects.filter(phone_number=display_phone_number).first()
                chatmessage = ChatMessage.objects.get(wamid=message_id)
                chatmessage.status_message = status_message
                chatmessage.save()
                read_receipt(channel.channle_id, chatmessage.message_id, chatmessage.conversation_id.conversation_id, status_message)
            if value:
                contact_phonenumber = value.get('messages', '')[0].get('from', '')
                try:
                    content_ = value.get('messages', '')[0].get('text', '').get('body','')
                except:
                    content_ = ''
                wamid = value.get('messages', '')[0].get('id', '')
                content_type = value.get('messages', '')[0].get('type', '')
                display_phone_number = value.get('metadata', '').get('display_phone_number', '')
                contacts = value.get('contacts', '')
                if contacts: 
                    channel = Channle.objects.filter(phone_number=display_phone_number).first()
                    account = Account.objects.get(account_id=channel.account_id.account_id)
                    contact_name = value.get('contacts', '')[0].get('profile', '').get('name', '')
                    contact, created = Contact.objects.get_or_create(name=contact_name, phone_number=contact_phonenumber, account_id= account)
                    conversation, created = Conversation.objects.get_or_create(contact_id=contact, account_id=account, channle_id=channel)
                    restart_keywords = [r.keyword for r in RestartKeyword.objects.filter(channel_id=channel.channle_id)]
                    if content_ in restart_keywords:
                        chat = Chat.objects.get(conversation_id=contact_phonenumber)
                        chat.isSent = False
                        chat.save
                        chat.update_state('start')
                        conversation.state = 'start_bot'
                        conversation.status =  'open'
                        conversation.save()
                    if conversation.state == 'start_bot':
                        match content_type:
                            case "text":
                                content = value.get('messages', '')[0].get('text', '').get('body','')
                                # chat_message = ChatMessage.objects.create(
                                #     conversation_id = conversation,
                                #     content_type = 'text',
                                #     content = content,
                                #     from_message = conversation.contact_id.name,
                                #     wamid = wamid
                                # )
                            case "button":
                                content = value.get('messages', '')[0].get('button', '').get('text','')
                                # chat_message = ChatMessage.objects.create(
                                #     conversation_id = conversation,
                                #     content_type = 'text',
                                #     content = content,
                                #     from_message = conversation.contact_id.name,
                                #     wamid = wamid
                                # )
                            case "interactive":
                                content = value.get('messages', '')[0].get('interactive', '').get('button_reply','').get('title', '')
                                # chat_message = ChatMessage.objects.create(
                                #     conversation_id = conversation,
                                #     content_type = 'text',
                                #     content = content,
                                #     from_message = conversation.contact_id.name,
                                #     wamid = wamid
                                # )
                        connect_web_socket(channel.channle_id, conversation.conversation_id, contact_phonenumber, content, wamid, contact_name)
                    else:        
                        match content_type:
                            case "button":
                                content = value.get('messages', '')[0].get('button', '').get('text','')
                                chat_message = ChatMessage.objects.create(
                                    conversation_id = conversation,
                                    content_type = 'text',
                                    content = content,
                                    from_message = conversation.contact_id.name,
                                    wamid = wamid
                                )
                                sent_message_text(conversation.conversation_id, content, content_type, wamid, chat_message.message_id, chat_message.created_at, contact.phone_number, channel.channle_id)
                            case "text":
                                content = value.get('messages', '')[0].get('text', '').get('body','')
                                chat_message = ChatMessage.objects.create(
                                    conversation_id = conversation,
                                    # user_id = CustomUser1.objects.filter(id=15).first(),
                                    content_type = content_type,
                                    content = content,
                                    from_message = conversation.contact_id.name,
                                    wamid = wamid
                                )
                                sent_message_text(conversation.conversation_id, content, content_type, wamid, chat_message.message_id, chat_message.created_at, contact.phone_number, channel.channle_id)

                            case "image":
                                headers = {
                                    'Content-Type': 'application/json',
                                    'Authorization': f'{channel.tocken}'
                                }
                                mime_type = value.get('messages', '')[0].get('image', {}).get('mime_type', '')
                                sha256 = value.get('messages', '')[0].get('image', {}).get('sha256', '')
                                image_id = value.get('messages', '')[0].get('image', {}).get('id', '')
                                try :
                                    caption = value.get('messages', '')[0].get('image', {}).get('caption', '')
                                except:
                                    pass
                                response = requests.get(f"https://graph.facebook.com/v15.0/{image_id}", headers=headers)
                                if response.status_code == 200:
                                    result_data = response.json()
                                    # url = download_and_save_image(result_data.get('url'), headers, 'media/chat_message', f"{image_id}.jpeg")
                                    file_name = f"{image_id}.jpeg"
                                    url = download_and_save_image(result_data.get('url'), headers, '/var/www/html/media/chat_message', file_name)
                                    chat_image = ChatMessage.objects.create(
                                        conversation_id= conversation,
                                        content_type= content_type,
                                        from_message = conversation.contact_id.name,
                                        wamid = wamid,
                                        media_url = f"https://chatbot.icsl.me/media/chat_message/{file_name}",
                                        media_sha256_hash = sha256,
                                        media_mime_type = mime_type,
                                        caption= caption
                                    )
                                    sent_message_image(conversation.conversation_id, chat_image.caption, content_type, wamid, chat_image.message_id, chat_image.created_at, contact.phone_number, chat_image.media_url, channel.channle_id)
                                    
                            case "video":
                                headers = {
                                    'Content-Type': 'application/json',
                                    'Authorization': f'{channel.tocken}'
                                }
                                mime_type = value.get('messages', '')[0].get('video', {}).get('mime_type', '')
                                sha256 = value.get('messages', '')[0].get('video', {}).get('sha256', '')
                                video_id = value.get('messages', '')[0].get('video', {}).get('id', '')
                                try :
                                    caption = value.get('messages', '')[0].get('video', {}).get('caption', '')
                                except:
                                    pass
                                response = requests.get(f"https://graph.facebook.com/v15.0/{video_id}", headers=headers)
                                
                                if response.status_code == 200:
                                    result_data = response.json()
                                    # url = download_and_save_image(media_url, 'media/chat_message')
                                    file_name = f"{video_id}.mp4"
                                    url = download_and_save_image(result_data.get('url'), headers, '/var/www/html/media/chat_message', file_name)
                                    chat_video = ChatMessage.objects.create(
                                        conversation_id= conversation,
                                        content_type= content_type,
                                        from_message = conversation.contact_id.name,
                                        wamid = wamid,
                                        media_url = f"https://chatbot.icsl.me/media/chat_message/{file_name}",
                                        media_sha256_hash = sha256,
                                        media_mime_type = mime_type,
                                        caption= caption
                                    )
                                    sent_message_video(conversation.conversation_id, chat_video.caption, content_type, wamid, chat_video.message_id, chat_video.created_at, contact.phone_number, chat_video.media_url, channel.channle_id)
                            case "audio":
                                headers = {
                                    'Content-Type': 'application/json',
                                    'Authorization': f'{channel.tocken}'
                                }
                                mime_type = value.get('messages', '')[0].get('audio', {}).get('mime_type', '')
                                sha256 = value.get('messages', '')[0].get('audio', {}).get('sha256', '')
                                audio_id = value.get('messages', '')[0].get('audio', {}).get('id', '')
                                try :
                                    caption = value.get('messages', '')[0].get('audio', {}).get('caption', '')
                                except:
                                    pass
                                response = requests.get(f"https://graph.facebook.com/v15.0/{audio_id}", headers=headers)
                                
                                if response.status_code == 200:
                                    # url = download_and_save_image(media_url, 'media/chat_message')
                                    result_data = response.json()
                                    # url = download_and_save_image(media_url, 'media/chat_message')
                                    file_name = f"{audio_id}.ogg"
                                    url = download_and_save_image(result_data.get('url'), headers, '/var/www/html/media/chat_message', file_name)
                                    chat_audio = ChatMessage.objects.create(
                                        conversation_id= conversation,
                                        content_type= content_type,
                                        from_message = conversation.contact_id.name,
                                        wamid = wamid,
                                        media_url = f"https://chatbot.icsl.me/media/chat_message/{file_name}",
                                        media_sha256_hash = sha256,
                                        media_mime_type = mime_type,
                                        caption= caption
                                    )
                                    sent_message_audio(conversation.conversation_id, caption, content_type, wamid, chat_audio.message_id, chat_audio.created_at, contact.phone_number, chat_audio.media_url, channel.channle_id)
                            case 'document':
                                headers = {
                                    'Content-Type': 'application/json',
                                    'Authorization': f'{channel.tocken}'
                                }
                                mime_type = value.get('messages', '')[0].get('document', {}).get('mime_type', '')
                                sha256 = value.get('messages', '')[0].get('document', {}).get('sha256', '')
                                file_name = value.get('messages', '')[0].get('document', {}).get('filename', '')
                                document_id = value.get('messages', '')[0].get('document', {}).get('id', '')
                                try :
                                    caption = value.get('messages', '')[0].get('document', {}).get('caption', '')
                                except:
                                    pass
                                response = requests.get(f"https://graph.facebook.com/v15.0/{document_id}", headers=headers)
                                
                                if response.status_code == 200:
                                    result_data = response.json()
                                    # url = download_and_save_image(media_url, 'media/chat_message')
                                    # file_name = f"{document_id}"
                                    # url = download_and_save_image(result_data.get('url'), headers, 'media/chat_message', file_name)
                                    url = download_and_save_image(result_data.get('url'), headers, '/var/www/html/media/chat_message', file_name)
                                    chat_document = ChatMessage.objects.create(
                                        conversation_id= conversation,
                                        content_type= content_type,
                                        from_message = conversation.contact_id.name,
                                        wamid = wamid,
                                        media_url = f"https://chatbot.icsl.me/media/chat_message/{file_name}",
                                        media_sha256_hash = sha256,
                                        media_mime_type = mime_type,
                                        caption= caption
                                    )
                                    sent_message_document(conversation.conversation_id, chat_document.caption, content_type, wamid, chat_document.message_id, chat_document.created_at, contact.phone_number, chat_document.media_url, mime_type, channel.channle_id)
                else:
                    mid = log_entry.get('event', {}).get('mid', ' ')
                    status_messaage = log_entry.get('event', {}).get('status', ' ')
                    status_updated_at = log_entry.get('event', {}).get('payload', {}).get('timestamp', ' ')
                    message = ChatMessage.objects.get(wamid=mid)
                    message.status_message = status_messaage
                    message.status_updated_at = status_updated_at
                    message.save()
    except Exception as e:
        print(e)
        error_redis = open('error_redis.txt', 'a')
        error_redis.write(f"your get the error: {e}\n")
    
def connect_web_socket(channel_id, conversation_id, source_id, content, wamid, contact_name):
    url_ws = f"wss://chatbot.icsl.me/ws/chat/{channel_id}/?token=&from_bot=False"
    # url_ws = f"ws://127.0.0.1:8000/ws/chat/{channel_id}/?token=&from_bot=False"
    ws = websocket.WebSocket()
    ws.connect(url_ws)
    data = {
        "conversation_id":f"{conversation_id}",
        "content_type": "bot_integration",
        "from_bot":"True",
        "data": {
            "content": f"{content}",
            "source_id": f"{source_id}",
            "conversation": {
                "contact_inbox": {
                    "source_id":f"{source_id}"
                }
            }
        },
        "wamid": wamid,
        "contact_name": contact_name,
        "from_bot" : ""
    }
    try:
        ws.send(json.dumps(data))
        result = ws.recv()
        ws.close()
    except Exception as e:
        pass

def sent_message_text(conversation_id, content, content_type, wamid, message_id, created_at, contact_phonenumber,channel_id):
    url_ws = f"wss://chatbot.icsl.me/ws/chat/{channel_id}/?token=&from_bot=False"
    # url_ws = f"ws://127.0.0.1:8000/ws/chat/{channel_id}/?token=&from_bot=False"
    ws = websocket.WebSocket()
    ws.connect(url_ws)
    data = {
        "content":content,
        "content_type":'text',
        "wamid":wamid,
        "from_bot":"False",
        "message_id": message_id,
        "created_at": f"{created_at}",
        "conversation_id": f"{conversation_id}"
    }
    try:
        ws.send(json.dumps(data))
        result = ws.recv()
        ws.close()
        
    except Exception as e:
        pass

def sent_message_image(conversation_id, caption, content_type, wamid, message_id, created_at, contact_phonenumber, media_url, channel_id):
    url_ws = f"wss://chatbot.icsl.me/ws/chat/{channel_id}/?token=&from_bot=False"
    # url_ws = f"ws://127.0.0.1:8000/ws/chat/{channel_id}/"
    ws = websocket.WebSocket()
    ws.connect(url_ws)
    data = {
        "caption":caption,
        "content_type":content_type,
        "wamid":wamid,
        "from_bot":"False",
        "message_id": message_id,
        "media_url": f"{media_url}",
        "created_at": f"{created_at}",
        "conversation_id": f"{conversation_id}"
    }
    try:
        ws.send(json.dumps(data))
        result = ws.recv()
        ws.close()

    except Exception as e:
        pass

def sent_message_video(conversation_id, caption, content_type, wamid, message_id, created_at, contact_phonenumber, media_url, channel_id):
    url_ws = f"wss://chatbot.icsl.me/ws/chat/{channel_id}/?token=&from_bot=False"
    # url_ws = f"ws://127.0.0.1:8000/ws/chat/{channel_id}/"
    ws = websocket.WebSocket()
    ws.connect(url_ws)
    data = {
        "caption":caption,
        "content_type":content_type,
        "wamid":wamid,
        "from_bot":"False",
        "message_id": message_id,
        "media_url": f"{media_url}",
        "created_at": f"{created_at}",
        "conversation_id": f"{conversation_id}"
    }
    try:
        ws.send(json.dumps(data))
        result = ws.recv()
        ws.close()

    except Exception as e:
        pass


def sent_message_audio(conversation_id, caption, content_type, wamid, message_id, created_at, phone_number, media_url, channel_id):
    url_ws = f"wss://chatbot.icsl.me/ws/chat/{channel_id}/?token=&from_bot=False"
    # url_ws = f"ws://127.0.0.1:8000/ws/chat/{channel_id}/"
    ws = websocket.WebSocket()
    ws.connect(url_ws)
    data = {
        "caption":caption,
        "content_type":content_type,
        "wamid":wamid,
        "from_bot":"False",
        "message_id": message_id,
        "media_url": f"{media_url}",
        "created_at": f"{created_at}",
        "conversation_id": f"{conversation_id}"
    }
    try:
        ws.send(json.dumps(data))
        result = ws.recv()
        ws.close()

    except Exception as e:
        pass

def sent_message_document(conversation_id, caption, content_type, wamid, message_id, created_at, phone_number, media_url, mime_type, channel_id):
    url_ws = f"wss://chatbot.icsl.me/ws/chat/{channel_id}/?token=&from_bot=False"
    # url_ws = f"ws://127.0.0.1:8000/ws/chat/{channel_id}/"
    ws = websocket.WebSocket()
    ws.connect(url_ws)
    data = {
        "caption":caption,
        "content_type":content_type,
        "wamid":wamid,
        "from_bot":"False",
        "message_id": message_id,
        "media_url": f"{media_url}",
        "created_at": f"{created_at}",
        # "mime_type": f"{mime_type}",
        "conversation_id": f"{conversation_id}"
    }
    try:
        ws.send(json.dumps(data))
        result = ws.recv()
        ws.close()

    except Exception as e:
        pass

def read_receipt(channel_id, message_id, conversation_id, status):
    url_ws = f"wss://chatbot.icsl.me/ws/chat/{channel_id}/?token=&from_bot=False"
    # url_ws = f"ws://127.0.0.1:8000/ws/chat/{channel_id}/"
    ws = websocket.WebSocket()
    ws.connect(url_ws)
    data = {
        "content_type":"message_status",
        "message_id": message_id,
        "conversation_id": conversation_id,
        "status": status,
        "from_bot": "True"
    }
    try:
        ws.send(json.dumps(data))
        result = ws.recv()
        ws.close()

    except Exception as e:
        pass

def download_and_save_image(image_url, headers, save_directory, image_name):
    """
    Downloads an image from a URL and saves it to a specified directory on the server.

    :param image_url: URL of the image to download.
    :param save_directory: Directory where the image will be saved.
    :return: Full path to the saved image.
    """
    full_path = os.path.join(save_directory, image_name)

    # Download the image
    response = requests.get(image_url, headers=headers, stream=True)
    # h = open('h.txt', 'a')
    # h.write(f"{response.content}")
    if response.status_code == 200:
        with open(full_path, 'wb') as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)
        return full_path
    else:
        raise Exception(f"Failed to download image. Status code: {response.status_code}")
    






# whatsapp_template_pdf.py
# Create a WhatsApp template with a PDF header and a single {{1}} variable in BODY,
# without requiring the caller to pass App ID explicitly.



HTTP_TIMEOUT_GET = 60
HTTP_TIMEOUT_POST = 120


class MetaApiError(Exception):
    pass


def _raise_for_api_error(resp: requests.Response):
    """Raise MetaApiError with body if status != 200."""
    if resp.status_code == 200:
        return
    try:
        body = resp.json()
    except Exception:
        body = resp.text
    raise MetaApiError(f"HTTP {resp.status_code}: {body}")


def _http_get(url: str, params=None, headers=None):
    resp = requests.get(
        url,
        params=params or {},
        headers=headers or {},
        timeout=HTTP_TIMEOUT_GET,
    )
    _raise_for_api_error(resp)
    return resp.json()


def _http_post(url: str, params=None, headers=None, data=None, json_body=None):
    resp = requests.post(
        url,
        params=params or {},
        headers=headers or {},
        data=data,
        json=json_body,
        timeout=HTTP_TIMEOUT_POST,
    )
    _raise_for_api_error(resp)
    return resp


def resolve_app_id_from_token(access_token: str) -> str:
    """
    Resolve app_id from the access token using /debug_token.
    Falls back to APP_TOKEN formed from META_APP_ID|META_APP_SECRET if needed.
    """
    base = f"https://graph.facebook.com/v22.0/debug_token"
    # Attempt 1: self-introspection
    try:
        j = _http_get(base, params={
            "input_token": access_token,
            "access_token": access_token,
        })
        if "data" in j and "app_id" in j["data"]:
            return j["data"]["app_id"]
    except MetaApiError as e1:
        first_err = str(e1)
    else:
        first_err = None

    raise MetaApiError(
        "Could not resolve app_id from token. "
        f"Self-introspection error: {first_err or 'n/a'}; "
        "No META_APP_ID/META_APP_SECRET set or second attempt failed."
    )

# import os
# import requests
# from mimetypes import guess_type

def upload_audio_to_whatsapp(file_path, access_token, phone_number_id):
    """
    Upload audio file to WhatsApp Business API
    """
    # Verify file exists
    if not os.path.exists(file_path):
        raise Exception(f"Audio file not found: {file_path}")
    
    # Get file extension and MIME type
    file_extension = os.path.splitext(file_path)[1].lower()
    mime_type, _ = mimetypes.guess_type(file_path)
    
    # Map file extensions to WhatsApp-supported MIME types
    mime_type_mapping = {
        '.mp3': 'audio/mpeg',
        '.aac': 'audio/aac',
        '.mp4': 'audio/mp4',
        '.amr': 'audio/amr',
        '.ogg': 'audio/ogg',
        '.opus': 'audio/opus',
        '.m4a': 'audio/mp4',
        '.wav': 'audio/ogg',  # Convert WAV to OGG or use MP3
    }
    
    # Use mapped MIME type or detected type
    if file_extension in mime_type_mapping:
        mime_type = mime_type_mapping[file_extension]
    elif not mime_type or mime_type == 'application/octet-stream':
        raise Exception(f"Unsupported audio format: {file_extension}. Supported: {list(mime_type_mapping.keys())}")
    
    # Prepare upload request
    upload_url = f"https://graph.facebook.com/v21.0/{phone_number_id}/media"
    
    headers = {
        "Authorization": f"{access_token}",
    }
    
    data = {
        "type": "audio",  # Important: specify this is audio
        "messaging_product": "whatsapp",
    }
    
    try:
        with open(file_path, 'rb') as audio_file:
            files = {
                "file": (os.path.basename(file_path), audio_file, mime_type)
            }
            
            response = requests.post(
                upload_url,
                headers=headers,
                data=data,
                files=files,
                timeout=30
            )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('id')  # Return media ID
        else:
            raise Exception(f"Failed to upload audio. Status code: {response.status_code}, Response: {response.text}")
            
    except Exception as e:
        raise Exception(f"Error uploading audio: {str(e)}")