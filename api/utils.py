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
            print("this is file name " + filename)
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
            print('this is imaage ' + source)
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
            print('this is video ' + source)
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
            # print('im contantnct')
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
                    "link": source
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
        print(response.status_code)
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
            print(beem_media_id)
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
        # print(buttons)
        response = requests.request("POST", url, headers=headers, data=payload)
        # print(response)
        
def validate_email(email):
  return bool(re.search(r"^[\w\.\+\-]+\@[\w]+\.[a-z]{2,3}$", email))

def validate_phone_number(phone_number):
    pattern = r'^\s*(?:\+?(\d{1,3}))?[-. (]*(\d{3})[-. )]*(\d{3})[-. ]*(\d{4})(?: *x(\d+))?\s*$'

    if re.match(pattern, phone_number):
        return True
    else:
        return False
    



v_v = '{"event": {"value": {"messaging_product": "whatsapp", "metadata": {"display_phone_number": "966920025589", "phone_number_id": "157289147477280"}, "contacts": [{"profile": {"name": "Jacoub"}, "wa_id": "966114886645"}], "messages": [{"from": "966114886645", "id": "wamid.HBgMOTY2MTE0ODg2NjQ1FQIAEhggQkUwNEU2ODg0MzI4MDZERTlCMDBGRDAzNkZFRTlDRUIA", "timestamp": "1739867538", "type": "video", "video": {"mime_type": "video/mp4", "sha256": "hekbZhF76pvXHZgbD7XwjeYgulKnS63Q1uNXyB0p7AM=", "id": "602300352596747"}}]}, "field": "messages"}, "medias": [{"url": "https://static-assets-v2.s3.us-east-2.amazonaws.com/uploads/1739867541070_media-0.3026585401465338.mp4", "caption": "", "type": "video", "file_name": "1739867541070_media-0.3026585401465338.mp4"}]}'
i_i = '{"event": {"value": {"messaging_product": "whatsapp","metadata": {"display_phone_number": "966920025589","phone_number_id": "157289147477280"},"contacts": [{"profile": {"name": "Jacoub"},"wa_id": "966114886645"}], "messages": [{"from": "966114886645","id": "wamid.HBgMOTY2MTE0ODg2NjQ1FQIAEhggQzcyMTlCQkM0QTExRjEwQkEwMThFQkQyMDM0N0ZEMkIA","timestamp": "1739778473","type": "image","image": {"mime_type": "image/jpeg","sha256": "t6NxRTNKvhHvzfZguOfPKKzhKLp89dIDrL7p3KxQ3Hg=","id": "1274841703581495"}}]},"field":"messages"},"medias": [{"url": "https://static-assets-v2.s3.us-east-2.amazonaws.com/uploads/1739778476665_media-0.4923813022854102.jpeg","caption": "فرع جده","type": "image","file_name": "1739778476665_media-0.4923813022854102.jpeg"}]}'
a_a = '{"event": {"value": {"messaging_product": "whatsapp", "metadata": {"display_phone_number": "966920025589", "phone_number_id": "157289147477280"}, "contacts": [{"profile": {"name": "Jacoub"}, "wa_id": "966114886645"}], "messages": [{"from": "966114886645", "id": "wamid.HBgMOTY2MTE0ODg2NjQ1FQIAEhggODdBRjkzREQxMzhDNDAyOTExODJGOTlFNEFENzgyN0MA", "timestamp": "1739951467", "type": "audio", "audio": {"mime_type": "audio/ogg; codecs=opus", "sha256": "0L/d6Pkc7nt+AYl6gtOPOjXeTMuInphwQmKK/d3VNKo=", "id": "1150877063380292", "voice": "True"}}]}, "field": "messages"}, "medias": [{"url": "https://static-assets-v2.s3.us-east-2.amazonaws.com/uploads/1739951469475_media-0.6118878625757445.ogg", "caption": "", "type": "audio", "file_name": "1739951469475_media-0.6118878625757445.ogg"}]}'
d_d = '{"event": {"value": {"messaging_product": "whatsapp", "metadata": {"display_phone_number": "966920025589", "phone_number_id": "157289147477280"}, "contacts": [{"profile": {"name": "Jacoub"}, "wa_id": "966114886645"}], "messages": [{"from": "966114886645", "id": "wamid.HBgMOTY2MTE0ODg2NjQ1FQIAEhggNjAyNzIyNDYyNjUzMDVFMzU4NEExNDMzMkRFRjhGQ0IA", "timestamp": "1739961961", "type": "document", "document": {"filename": "1709124383910_ICS Company Profile AR.pdf", "mime_type": "application/pdf", "sha256": "IHPpJcYjvjTepZTrKvXAacDUge/p0JKvQHOX7t4V1ag=", "id": "1134184264697475"}}]}, "field": "messages"}, "medias": [{"url": "https://static-assets-v2.s3.us-east-2.amazonaws.com/uploads/1739961964386_1709124383910_ICS%20Company%20Profile%20AR.pdf", "caption": "", "type": "document", "file_name": "1739961964386_1709124383910_ICS%20Company%20Profile%20AR.pdf"}]}'

def handel_request_redis(data):

    try:
        redis_client = get_redis_connection()
        print("klfjdlkjflkdjlk")
        redis_client.lpush('data_queue', json.dumps(data))
        f = open('content_redis.txt', 'a')
        f.write("recive redis: " + str(data) + '\n')
        raw_data = redis_client.rpop('data_queue')
        test_data = json.loads(raw_data)
        f.write("from redis: " + str(test_data) + '\n' + "new_line-------------------" + '\n')
        if raw_data == None:
            return Response({'message':data}, status=status.HTTP_200_OK)
        else:
            
            log_entry = json.loads(raw_data)
            value = log_entry.get('event', '').get('value', '')
            
            if value:   
                wamid = log_entry.get('event', {}).get('value', {}).get('messages', '')[0].get('id', '')
                content_type = log_entry.get('event', {}).get('value', {}).get('messages', '')[0].get('type', '')
                contact_phonenumber = log_entry.get('event', {}).get('value', {}).get('messages', '')[0].get('from', '')
                # timestamp = log_entry.get('event', {}).get('value', {}).get('messages', '')[0].get('timestamp', '')
                # messaging_product = log_entry.get('event', {}).get('value', {}).get('messaging_product', '')
                display_phone_number = log_entry.get('event', {}).get('value', {}).get('metadata', '').get('display_phone_number', '')
                # phone_number_id = log_entry.get('event', {}).get('value', {}).get('metadata', '').get('phone_number_id', '')
                contacts = log_entry.get('event', '').get('value', '').get('contacts', '')
                if contacts:                   
                    contact_name = log_entry.get('event', '').get('value', '').get('contacts', '')[0].get('profile', '').get('name', '')
                    contact, created = Contact.objects.get_or_create(name=contact_name, phone_number=contact_phonenumber)
                    channel = Channle.objects.filter(phone_number=display_phone_number).first()
                    conversation, created = Conversation.objects.get_or_create(contact_id=contact, account_id=contact.account_id, channle_id=channel)
                    match content_type:
                        case "text":
                            content = log_entry.get('event', {}).get('value', {}).get('messages', '')[0].get('text', '').get('body','')
                            chat_message = ChatMessage.objects.create(
                                conversation_id = conversation,
                                # user_id = CustomUser1.objects.filter(id=15).first(),
                                content_type = content_type,
                                content = content,
                                from_message = conversation.contact_id.name,
                                wamid = wamid
                            )
                            sent_message_text(conversation.conversation_id, content, content_type, wamid, chat_message.message_id, chat_message.created_at, contact.phone_number)

                        case "image":
                            mime_type = log_entry.get('event', {}).get('value', {}).get('messages', '')[0].get('image', '').get('mime_type', '')
                            sha256 = log_entry.get('event', {}).get('value', {}).get('messages', '')[0].get('image', '').get('sha256', '')
                            # medias = log_entry.get('medias', '')
                            media_url = log_entry.get('medias', '')[0].get('url', '')
                            file_name = log_entry.get('medias', '')[0].get('file_name', '')
                            caption = log_entry.get('medias', '')[0].get('caption', '')
                            response = requests.get(media_url)
                            if response.status_code == 200:
                                # url = download_and_save_image(media_url, 'media/chat_message')
                                url = download_and_save_image(media_url, '/var/www/html/media/chat_message')
                                # image = UploadImage.objects.create(
                                #     image_file= ContentFile(response.content, name=file_name)
                                # )
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
                                sent_message_image(conversation.conversation_id, caption, content_type, wamid, chat_image.message_id, chat_image.created_at, contact.phone_number, chat_image.media_url)
                                
                        case "video":
                            mime_type = log_entry.get('event', {}).get('value', {}).get('messages', [])[0].get('video', {}).get('mime_type', '')
                            sha256 = log_entry.get('event', {}).get('value', {}).get('messages', [])[0].get('viedo', {}).get('sha256', '')
                            media_url = log_entry.get('medias', [])[0].get('url', '')
                            file_name = log_entry.get('medias', [])[0].get('file_name', '')
                            caption = log_entry.get('medias', [])[0].get('caption', '')
                            response = requests.get(media_url)
                            if response.status_code == 200:
                                # url = download_and_save_image(media_url, 'media/chat_message')
                                url = download_and_save_image(media_url, '/var/www/html/media/chat_message')
                                # image = UploadImage.objects.create(
                                #     image_file= ContentFile(response.content, name=file_name)
                                # )
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
                                sent_message_video(conversation.conversation_id, caption, content_type, wamid, chat_video.message_id, chat_video.created_at, contact.phone_number, chat_video.media_url)
                        case "audio":
                            mime_type = log_entry.get('event', {}).get('value', {}).get('messages', [])[0].get('audio', {}).get('mime_type', '')
                            sha256 = log_entry.get('event', {}).get('value', {}).get('messages', [])[0].get('audio', {}).get('sha256', '')
                            media_url = log_entry.get('medias', [])[0].get('url', '')
                            file_name = log_entry.get('medias', [])[0].get('file_name', '')
                            caption = log_entry.get('medias', [])[0].get('caption', '')
                            response = requests.get(media_url)
                            if response.status_code == 200:
                                # url = download_and_save_image(media_url, 'media/chat_message')
                                url = download_and_save_image(media_url, '/var/www/html/media/chat_message')
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
                                sent_message_audio(conversation.conversation_id, caption, content_type, wamid, chat_audio.message_id, chat_audio.created_at, contact.phone_number, chat_audio.media_url)
                        case 'document':
                            mime_type = log_entry.get('event', {}).get('value', {}).get('messages', [])[0].get('document', {}).get('mime_type', '')
                            sha256 = log_entry.get('event', {}).get('value', {}).get('messages', [])[0].get('document', {}).get('sha256', '')
                            media_url = log_entry.get('medias', [])[0].get('url', '')
                            file_name = log_entry.get('medias', [])[0].get('file_name', '')
                            caption = log_entry.get('medias', [])[0].get('caption', '')
                            response = requests.get(media_url)
                            if response.status_code == 200:
                                # url = download_and_save_image(media_url, 'media/chat_message')
                                url = download_and_save_image(media_url, '/var/www/html/media/chat_message')
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
                                sent_message_document(conversation.conversation_id, caption, content_type, wamid, chat_document.message_id, chat_document.created_at, contact.phone_number, chat_document.media_url)
            else:
                mid = log_entry.get('event', {}).get('mid', ' ')
                status_messaage = log_entry.get('event', {}).get('status', ' ')
                status_updated_at = log_entry.get('event', {}).get('payload', {}).get('timestamp', ' ')
                message = ChatMessage.objects.get(wamid=mid)
                message.status_message = status_messaage
                message.status_updated_at = status_updated_at
                message.save()
    except Exception as e:
        error_redis = open('error_redis.txt', 'a')
        error_redis.write(f"your get the error: {e}\n")
    
def sent_message_text(conversation_id, content, content_type, wamid, message_id, created_at, contact_phonenumber):
    url_ws = f"wss://chatbot.icsl.me/ws/chat/{conversation_id}/{contact_phonenumber}/?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzQwNTY0MTg4LCJpYXQiOjE3Mzk3MDAxODgsImp0aSI6IjNiMTVmNTc1NTQyMTRjYTdiZTg3OWNiMjUyZjBjM2Y2IiwidXNlcl9pZCI6MX0.4nw1OZDRJbLPOvhaBUIjAp0Bm-B_PyL45PkOU9uMhKY"
    # url_ws = f"ws://127.0.0.1:8000/ws/chat/{conversation_id}/{contact_phonenumber}/?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzQwNTYyMDY1LCJpYXQiOjE3Mzk2OTgwNjUsImp0aSI6IjliNDFlYWZmMTJhMjQxOTY4NzA4NjI4MmI5YzVjYTU1IiwidXNlcl9pZCI6MTN9.2kRBS2T-m6kpi1-FwwlAKiG2vcSk1joJx9httz_hyok"
    ws = websocket.WebSocket()
    ws.connect(url_ws)
    data = {
        "content":content,
        "content_type":content_type,
        "wamid":wamid,
        "from_bot":"False",
        "message_id": message_id,
        "created_at": f"{created_at}"
    }
    try:
        ws.send(json.dumps(data))
        result = ws.recv()
        ws.close()
        
    except Exception as e:
        pass

def sent_message_image(conversation_id, caption, content_type, wamid, message_id, created_at, contact_phonenumber, media_url):
    url_ws = f"wss://chatbot.icsl.me/ws/chat/{conversation_id}/{contact_phonenumber}/?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzQwNTY0MTg4LCJpYXQiOjE3Mzk3MDAxODgsImp0aSI6IjNiMTVmNTc1NTQyMTRjYTdiZTg3OWNiMjUyZjBjM2Y2IiwidXNlcl9pZCI6MX0.4nw1OZDRJbLPOvhaBUIjAp0Bm-B_PyL45PkOU9uMhKY"
    # url_ws = f"ws://127.0.0.1:8000/ws/chat/{conversation_id}/{contact_phonenumber}/?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzQwNTYyMDY1LCJpYXQiOjE3Mzk2OTgwNjUsImp0aSI6IjliNDFlYWZmMTJhMjQxOTY4NzA4NjI4MmI5YzVjYTU1IiwidXNlcl9pZCI6MTN9.2kRBS2T-m6kpi1-FwwlAKiG2vcSk1joJx9httz_hyok"
    ws = websocket.WebSocket()
    ws.connect(url_ws)
    data = {
        "caption":caption,
        "content_type":content_type,
        "wamid":wamid,
        "from_bot":"False",
        "message_id": message_id,
        "media_url": f"{media_url}",
        "created_at": f"{created_at}"
    }
    try:
        ws.send(json.dumps(data))
        result = ws.recv()
        ws.close()

    except Exception as e:
        pass

def sent_message_video(conversation_id, caption, content_type, wamid, message_id, created_at, contact_phonenumber, media_url):
    url_ws = f"wss://chatbot.icsl.me/ws/chat/{conversation_id}/{contact_phonenumber}/?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzQwNTY0MTg4LCJpYXQiOjE3Mzk3MDAxODgsImp0aSI6IjNiMTVmNTc1NTQyMTRjYTdiZTg3OWNiMjUyZjBjM2Y2IiwidXNlcl9pZCI6MX0.4nw1OZDRJbLPOvhaBUIjAp0Bm-B_PyL45PkOU9uMhKY"
    # url_ws = f"ws://127.0.0.1:8000/ws/chat/{conversation_id}/{contact_phonenumber}/?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzQwNTYyMDY1LCJpYXQiOjE3Mzk2OTgwNjUsImp0aSI6IjliNDFlYWZmMTJhMjQxOTY4NzA4NjI4MmI5YzVjYTU1IiwidXNlcl9pZCI6MTN9.2kRBS2T-m6kpi1-FwwlAKiG2vcSk1joJx9httz_hyok"
    ws = websocket.WebSocket()
    ws.connect(url_ws)
    data = {
        "caption":caption,
        "content_type":content_type,
        "wamid":wamid,
        "from_bot":"False",
        "message_id": message_id,
        "media_url": f"{media_url}",
        "created_at": f"{created_at}"
    }
    try:
        ws.send(json.dumps(data))
        result = ws.recv()
        ws.close()

    except Exception as e:
        pass


def sent_message_audio(conversation_id, caption, content_type, wamid, message_id, created_at, contact_phonenumber, media_url):
    url_ws = f"wss://chatbot.icsl.me/ws/chat/{conversation_id}/{contact_phonenumber}/?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzQwNTY0MTg4LCJpYXQiOjE3Mzk3MDAxODgsImp0aSI6IjNiMTVmNTc1NTQyMTRjYTdiZTg3OWNiMjUyZjBjM2Y2IiwidXNlcl9pZCI6MX0.4nw1OZDRJbLPOvhaBUIjAp0Bm-B_PyL45PkOU9uMhKY"
    # url_ws = f"ws://127.0.0.1:8000/ws/chat/{conversation_id}/{contact_phonenumber}/?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzQwNTYyMDY1LCJpYXQiOjE3Mzk2OTgwNjUsImp0aSI6IjliNDFlYWZmMTJhMjQxOTY4NzA4NjI4MmI5YzVjYTU1IiwidXNlcl9pZCI6MTN9.2kRBS2T-m6kpi1-FwwlAKiG2vcSk1joJx9httz_hyok"
    ws = websocket.WebSocket()
    ws.connect(url_ws)
    data = {
        "caption":caption,
        "content_type":content_type,
        "wamid":wamid,
        "from_bot":"False",
        "message_id": message_id,
        "media_url": f"{media_url}",
        "created_at": f"{created_at}"
    }
    try:
        ws.send(json.dumps(data))
        result = ws.recv()
        ws.close()

    except Exception as e:
        pass

def sent_message_document(conversation_id, caption, content_type, wamid, message_id, created_at, contact_phonenumber, media_url):
    url_ws = f"wss://chatbot.icsl.me/ws/chat/{conversation_id}/{contact_phonenumber}/?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzQwNTY0MTg4LCJpYXQiOjE3Mzk3MDAxODgsImp0aSI6IjNiMTVmNTc1NTQyMTRjYTdiZTg3OWNiMjUyZjBjM2Y2IiwidXNlcl9pZCI6MX0.4nw1OZDRJbLPOvhaBUIjAp0Bm-B_PyL45PkOU9uMhKY"
    # url_ws = f"ws://127.0.0.1:8000/ws/chat/{conversation_id}/{contact_phonenumber}/?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzQwNTYyMDY1LCJpYXQiOjE3Mzk2OTgwNjUsImp0aSI6IjliNDFlYWZmMTJhMjQxOTY4NzA4NjI4MmI5YzVjYTU1IiwidXNlcl9pZCI6MTN9.2kRBS2T-m6kpi1-FwwlAKiG2vcSk1joJx9httz_hyok"
    ws = websocket.WebSocket()
    ws.connect(url_ws)
    data = {
        "caption":caption,
        "content_type":content_type,
        "wamid":wamid,
        "from_bot":"False",
        "message_id": message_id,
        "media_url": f"{media_url}",
        "created_at": f"{created_at}"
    }
    try:
        ws.send(json.dumps(data))
        result = ws.recv()
        ws.close()

    except Exception as e:
        pass

def download_and_save_image(image_url, save_directory):
    """
    Downloads an image from a URL and saves it to a specified directory on the server.

    :param image_url: URL of the image to download.
    :param save_directory: Directory where the image will be saved.
    :return: Full path to the saved image.
    """
    # Extract the image name from the URL
    image_name = os.path.basename(image_url)

    # Full path to save the image
    full_path = os.path.join(save_directory, image_name)

    # Download the image
    response = requests.get(image_url, stream=True)
    if response.status_code == 200:
        with open(full_path, 'wb') as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)
        return full_path
    else:
        raise Exception(f"Failed to download image. Status code: {response.status_code}")