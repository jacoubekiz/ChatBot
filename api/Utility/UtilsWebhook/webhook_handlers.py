"""
Handler functions for webhook processing.
"""
from asyncio.windows_events import NULL
from django.db import transaction
from api.Contact.models_contact import Contact, Conversation, ChatMessage
from api.Consumers.utils_websocket import (
    connect_web_socket,
    sent_message_text,
    sent_message_image,
    sent_message_video,
    sent_message_audio,
    sent_message_document,
    read_receipt
)
from .webhook_helpers import (
    get_channel_by_phone,
    get_chat_message_by_wamid,
    get_restart_keywords,
    extract_message_data,
    extract_media_data,
    download_media,
    get_media_file_name
)


def handle_status_update(value: dict) -> dict:
    """Handle message status updates."""
    statuses = value.get('statuses', [])
    if not statuses:
        return {'error': 'No statuses found'}
    
    status_data = statuses[0]
    message_id = status_data.get('id', '')
    status_message = status_data.get('status', '')
    display_phone_number = value.get('metadata', {}).get('display_phone_number', '')
    
    channel = get_channel_by_phone(display_phone_number)
    if not channel:
        return {'error': 'Channel not found'}
    
    chatmessage = get_chat_message_by_wamid(message_id)
    chatmessage.status_message = status_message
    chatmessage.save()
    
    read_receipt(
        channel.channle_id,
        chatmessage.message_id,
        chatmessage.conversation_id.conversation_id,
        status_message
    )
    
    return {'success': True}


def handle_text_message(conversation, contact, message_data: dict, content: str, wamid: str):
    """Handle text message creation and broadcasting."""
    chat_message = ChatMessage.objects.create(
        conversation_id=conversation,
        content_type='text',
        content=content,
        from_message=conversation.contact_id.name or contact.phone_number,
        wamid=wamid
    )
    sent_message_text(
        conversation.conversation_id,
        content,
        'text',
        wamid,
        chat_message.message_id,
        chat_message.created_at,
        contact.phone_number,
        conversation.channle_id.channle_id,
        contact.contact_id
    )


def handle_media_message(conversation, contact, channel, message_data: dict, media_type: str, wamid: str):
    """Handle media message download, creation and broadcasting."""
    media_data = extract_media_data(message_data[media_type])
    file_name = get_media_file_name(media_type, media_data)
    
    media_url = download_media(media_data['id'], channel.tocken, file_name)
    
    chat_message = ChatMessage.objects.create(
        conversation_id=conversation,
        content_type=media_type,
        from_message=conversation.contact_id.name,
        wamid=wamid,
        media_url=media_url,
        media_sha256_hash=media_data['sha256'],
        media_mime_type=media_data['mime_type'],
        caption=media_data['caption']
    )
    
    # Send appropriate message based on media type
    send_functions = {
        'image': sent_message_image,
        'video': sent_message_video,
        'audio': sent_message_audio,
        'document': sent_message_document
    }
    
    send_func = send_functions.get(media_type)
    if send_func:
        if media_type == 'document':
            send_func(
                conversation.conversation_id,
                chat_message.caption,
                media_type,
                wamid,
                chat_message.message_id,
                chat_message.created_at,
                contact.phone_number,
                chat_message.media_url,
                media_data['mime_type'],
                channel.channle_id,
                contact.contact_id
            )
        else:
            send_func(
                conversation.conversation_id,
                chat_message.caption,
                media_type,
                wamid,
                chat_message.message_id,
                chat_message.created_at,
                contact.phone_number,
                chat_message.media_url,
                channel.channle_id,
                contact.contact_id
            )


def handle_incoming_message(value: dict) -> dict:
    """Handle incoming messages from webhook."""
    message_data = extract_message_data(value)
    if not message_data:
        return {'error': 'No message data found'}
    
    contact_phonenumber = message_data['from']
    wamid = message_data['id']
    content_type = message_data['type']
    display_phone_number = value.get('metadata', {}).get('display_phone_number', '')
    contacts = value.get('contacts', [])
    
    if not contacts:
        return {'error': 'No contact data found'}
    
    channel = get_channel_by_phone(display_phone_number)
    if not channel:
        return {'error': 'Channel not found'}
    
    account = channel.account_id
    contact_name = contacts[0].get('profile', {}).get('name', '')
    
    with transaction.atomic():
        contact, _ = Contact.objects.get_or_create(
            phone_number=contact_phonenumber,
            account_id=account
        )
        if contact.name != '':
            contact.name = contact_name
            contact.save()
        
        conversation, _ = Conversation.objects.get_or_create(
            contact_id=contact,
            account_id=account,
            channle_id=channel
        )
    
    # Check for restart keyword
    restart_keywords = get_restart_keywords(channel.channle_id)
    content = message_data.get('text', message_data.get('button', message_data.get('interactive', '')))
    
    if content in restart_keywords:
        conversation.state = 'start_bot'
        conversation.status = 'open'
        conversation.save()
    
    # Always store message in database regardless of conversation state
    if content_type in ['text', 'button']:
        handle_text_message(conversation, contact, message_data, content, wamid)
    elif content_type in ['image', 'video', 'audio', 'document']:
        handle_media_message(conversation, contact, channel, message_data, content_type, wamid)
    
    # Handle WebSocket connection for bot state
    if conversation.state == 'start_bot':
        connect_web_socket(
            channel.channle_id,
            conversation.conversation_id,
            contact_phonenumber,
            content,
            wamid,
            contact_name,
            contact.contact_id
        )
    
    return {'success': True}


def handle_event_status(log_entry: dict) -> dict:
    """Handle event status updates."""
    event = log_entry.get('event', {})
    mid = event.get('mid', '')
    status_message = event.get('status', '')
    status_updated_at = event.get('payload', {}).get('timestamp', '')
    
    if not mid:
        return {'error': 'No message ID found'}
    
    message = ChatMessage.objects.get(wamid=mid)
    message.status_message = status_message
    message.status_updated_at = status_updated_at
    message.save()
    
    return {'success': True}
