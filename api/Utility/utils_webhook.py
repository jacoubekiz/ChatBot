import json
import requests
from celery import shared_task
from api.Channel.models_channel import Channle
from api.Contact.models_contact import Contact, Conversation, ChatMessage
from api.Flow.models_flow import RestartKeyword
from api.Consumers.utils_websocket import (
    connect_web_socket,
    sent_message_text,
    sent_message_image,
    sent_message_video,
    sent_message_audio,
    sent_message_document,
    read_receipt
)
from api.Utility.utils_media import download_and_save_image
from rest_framework import status
from rest_framework.response import Response


@shared_task
def handel_request_redis(data):
    """Handle webhook data from Redis queue."""
    try:
        f = open(f'content_redis.txt', 'a')
        f.write("recive redis: " + str(data) + '\n')
        test_data = json.loads(data)
        f.write("from redis: " + str(test_data) + '\n' + "new_line-------------------" + '\n')
        
        if data == None:
            return Response({'message': data}, status=status.HTTP_200_OK)
        else:
            log_entry = json.loads(data)
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
            else:
                contact_phonenumber = value.get('messages', '')[0].get('from', '')
                try:
                    content_ = value.get('messages', '')[0].get('text', '').get('body', '')
                except:
                    content_ = ''
                wamid = value.get('messages', '')[0].get('id', '')
                content_type = value.get('messages', '')[0].get('type', '')
                display_phone_number = value.get('metadata', '').get('display_phone_number', '')
                contacts = value.get('contacts', '')
                
                if contacts:
                    channel = Channle.objects.filter(phone_number=display_phone_number).first()
                    account = channel.account_id
                    contact_name = value.get('contacts', '')[0].get('profile', '').get('name', '')
                    contact, created = Contact.objects.get_or_create(phone_number=contact_phonenumber, account_id=account)
                    contact.name = contact_name
                    contact.save()
                    conversation, created = Conversation.objects.get_or_create(contact_id=contact, account_id=account, channle_id=channel)
                    restart_keywords = [r.keyword for r in RestartKeyword.objects.filter(channel_id=channel.channle_id)]
                    
                    if content_ in restart_keywords:
                        conversation.state = 'start_bot'
                        conversation.status = 'open'
                        conversation.save()
                    
                    if conversation.state == 'start_bot':
                        match content_type:
                            case "text":
                                content = value.get('messages', '')[0].get('text', '').get('body', '')
                            case "button":
                                content = value.get('messages', '')[0].get('button', '').get('text', '')
                            case "interactive":
                                content = value.get('messages', '')[0].get('interactive', '').get('button_reply', '').get('title', '')
                        
                        connect_web_socket(channel.channle_id, conversation.conversation_id, contact_phonenumber, content, wamid, contact_name)
                    else:
                        match content_type:
                            case "button":
                                content = value.get('messages', '')[0].get('button', '').get('text', '')
                                chat_message = ChatMessage.objects.create(
                                    conversation_id=conversation,
                                    content_type='text',
                                    content=content,
                                    from_message=conversation.contact_id.name,
                                    wamid=wamid
                                )
                                sent_message_text(conversation.conversation_id, content, content_type, wamid, chat_message.message_id, chat_message.created_at, contact.phone_number, channel.channle_id)
                            case "text":
                                content = value.get('messages', '')[0].get('text', '').get('body', '')
                                chat_message = ChatMessage.objects.create(
                                    conversation_id=conversation,
                                    content_type=content_type,
                                    content=content,
                                    from_message=conversation.contact_id.name or contact.phone_number,
                                    wamid=wamid
                                )
                                sent_message_text(conversation.conversation_id, content, content_type, wamid, chat_message.message_id, chat_message.created_at, contact.phone_number, channel.channle_id)
                            case "image":
                                headers = {
                                    'Content-Type': 'application/json',
                                    'Authorization': f'Bearer {channel.tocken}'
                                }
                                mime_type = value.get('messages', '')[0].get('image', {}).get('mime_type', '')
                                sha256 = value.get('messages', '')[0].get('image', {}).get('sha256', '')
                                image_id = value.get('messages', '')[0].get('image', {}).get('id', '')
                                try:
                                    caption = value.get('messages', '')[0].get('image', {}).get('caption', '')
                                except:
                                    caption = ''
                                response = requests.get(f"https://graph.facebook.com/v15.0/{image_id}", headers=headers)
                                if response.status_code == 200:
                                    result_data = response.json()
                                    file_name = f"{image_id}.jpeg"
                                    url = download_and_save_image(result_data.get('url'), headers, '/www/wwwroot/chatapi.icsl.me/media/chat_message', file_name)
                                    chat_image = ChatMessage.objects.create(
                                        conversation_id=conversation,
                                        content_type=content_type,
                                        from_message=conversation.contact_id.name,
                                        wamid=wamid,
                                        media_url=f"https://chatapi.icsl.me/media/chat_message/{file_name}",
                                        media_sha256_hash=sha256,
                                        media_mime_type=mime_type,
                                        caption=caption
                                    )
                                    sent_message_image(conversation.conversation_id, chat_image.caption, content_type, wamid, chat_image.message_id, chat_image.created_at, contact.phone_number, chat_image.media_url, channel.channle_id)
                            case "video":
                                headers = {
                                    'Content-Type': 'application/json',
                                    'Authorization': f'Bearer {channel.tocken}'
                                }
                                mime_type = value.get('messages', '')[0].get('video', {}).get('mime_type', '')
                                sha256 = value.get('messages', '')[0].get('video', {}).get('sha256', '')
                                video_id = value.get('messages', '')[0].get('video', {}).get('id', '')
                                try:
                                    caption = value.get('messages', '')[0].get('video', {}).get('caption', '')
                                except:
                                    caption = ''
                                response = requests.get(f"https://graph.facebook.com/v15.0/{video_id}", headers=headers)
                                if response.status_code == 200:
                                    result_data = response.json()
                                    file_name = f"{video_id}.mp4"
                                    url = download_and_save_image(result_data.get('url'), headers, '/www/wwwroot/chatapi.icsl.me/media/chat_message', file_name)
                                    chat_video = ChatMessage.objects.create(
                                        conversation_id=conversation,
                                        content_type=content_type,
                                        from_message=conversation.contact_id.name,
                                        wamid=wamid,
                                        media_url=f"https://chatapi.icsl.me/media/chat_message/{file_name}",
                                        media_sha256_hash=sha256,
                                        media_mime_type=mime_type,
                                        caption=caption
                                    )
                                    sent_message_video(conversation.conversation_id, chat_video.caption, content_type, wamid, chat_video.message_id, chat_video.created_at, contact.phone_number, chat_video.media_url, channel.channle_id)
                            case "audio":
                                headers = {
                                    'Content-Type': 'application/json',
                                    'Authorization': f'Bearer {channel.tocken}'
                                }
                                mime_type = value.get('messages', '')[0].get('audio', {}).get('mime_type', '')
                                sha256 = value.get('messages', '')[0].get('audio', {}).get('sha256', '')
                                audio_id = value.get('messages', '')[0].get('audio', {}).get('id', '')
                                try:
                                    caption = value.get('messages', '')[0].get('audio', {}).get('caption', '')
                                except:
                                    caption = ''
                                response = requests.get(f"https://graph.facebook.com/v15.0/{audio_id}", headers=headers)
                                if response.status_code == 200:
                                    result_data = response.json()
                                    file_name = f"{audio_id}.ogg"
                                    url = download_and_save_image(result_data.get('url'), headers, '/www/wwwroot/chatapi.icsl.me/media/chat_message', file_name)
                                    chat_audio = ChatMessage.objects.create(
                                        conversation_id=conversation,
                                        content_type=content_type,
                                        from_message=conversation.contact_id.name,
                                        wamid=wamid,
                                        media_url=f"https://chatapi.icsl.me/media/chat_message/{file_name}",
                                        media_sha256_hash=sha256,
                                        media_mime_type=mime_type,
                                        caption=caption
                                    )
                                    sent_message_audio(conversation.conversation_id, caption, content_type, wamid, chat_audio.message_id, chat_audio.created_at, contact.phone_number, chat_audio.media_url, channel.channle_id)
                            case 'document':
                                headers = {
                                    'Content-Type': 'application/json',
                                    'Authorization': f'Bearer {channel.tocken}'
                                }
                                mime_type = value.get('messages', '')[0].get('document', {}).get('mime_type', '')
                                sha256 = value.get('messages', '')[0].get('document', {}).get('sha256', '')
                                file_name = value.get('messages', '')[0].get('document', {}).get('filename', '')
                                document_id = value.get('messages', '')[0].get('document', {}).get('id', '')
                                try:
                                    caption = value.get('messages', '')[0].get('document', {}).get('caption', '')
                                except:
                                    caption = ''
                                response = requests.get(f"https://graph.facebook.com/v15.0/{document_id}", headers=headers)
                                if response.status_code == 200:
                                    result_data = response.json()
                                    url = download_and_save_image(result_data.get('url'), headers, '/www/wwwroot/chatapi.icsl.me/media/chat_message', file_name)
                                    chat_document = ChatMessage.objects.create(
                                        conversation_id=conversation,
                                        content_type=content_type,
                                        from_message=conversation.contact_id.name,
                                        wamid=wamid,
                                        media_url=f"https://chatapi.icsl.me/media/chat_message/{file_name}",
                                        media_sha256_hash=sha256,
                                        media_mime_type=mime_type,
                                        caption=caption
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
        error_redis = open('error_redis.txt', 'a')
        error_redis.write(f"your get the error: {e}\n")
