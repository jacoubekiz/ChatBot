"""
Helper functions for webhook processing.
"""
import json
import requests
from django.core.cache import cache
from api.Channel.models_channel import Channle
from api.Contact.models_contact import Contact, Conversation, ChatMessage
from api.Flow.models_flow import RestartKeyword
from api.Utility.utils_media import download_and_save_image
from .webhook_constants import (
    WHATSAPP_API_BASE_URL,
    MEDIA_BASE_PATH,
    MEDIA_PUBLIC_URL,
    CACHE_TIMEOUT,
    HTTP_TIMEOUT,
    MEDIA_EXTENSIONS
)

# Connection pooling for better performance
_http_session = requests.Session()
_http_session.headers.update({'Content-Type': 'application/json'})


def log_webhook_data(data: str) -> None:
    """Log webhook data to file for debugging."""
    try:
        with open('content_redis.txt', 'a') as f:
            f.write(f"receive redis: {data}\n")
            test_data = json.loads(data)
            f.write(f"from redis: {test_data}\nnew_line-------------------\n")
    except Exception as e:
        log_error(f"Logging error: {e}")


def log_error(error_message: str) -> None:
    """Log errors to file for debugging."""
    try:
        with open('error_redis.txt', 'a') as f:
            f.write(f"Error: {error_message}\n")
    except Exception:
        pass  # Avoid infinite loop if file writing fails


def get_channel_by_phone(phone_number: str):
    """Get channel by phone number with optimized query."""
    return Channle.objects.filter(
        phone_number=phone_number
    ).select_related('account_id').first()


def get_chat_message_by_wamid(wamid: str):
    """Get chat message by wamid with optimized query."""
    return ChatMessage.objects.select_related('conversation_id').get(wamid=wamid)


def get_restart_keywords(channel_id: str):
    """Get restart keywords with caching."""
    cache_key = f'restart_keywords_{channel_id}'
    keywords = cache.get(cache_key)
    if keywords is None:
        keywords = list(RestartKeyword.objects.filter(
            channel_id=channel_id
        ).values_list('keyword', flat=True))
        cache.set(cache_key, keywords, timeout=CACHE_TIMEOUT)
    return keywords


def extract_message_data(value: dict) -> dict:
    """Extract common message data from webhook payload."""
    messages = value.get('messages', [])
    if not messages:
        return {}
    
    message = messages[0]
    return {
        'from': message.get('from', ''),
        'id': message.get('id', ''),
        'type': message.get('type', ''),
        'text': message.get('text', {}).get('body', ''),
        'button': message.get('button', {}).get('text', ''),
        'interactive': message.get('interactive', {}).get('button_reply', {}).get('title', ''),
        'image': message.get('image', {}),
        'video': message.get('video', {}),
        'audio': message.get('audio', {}),
        'document': message.get('document', {})
    }


def extract_media_data(media_dict: dict) -> dict:
    """Extract media metadata from message."""
    return {
        'mime_type': media_dict.get('mime_type', ''),
        'sha256': media_dict.get('sha256', ''),
        'id': media_dict.get('id', ''),
        'caption': media_dict.get('caption', ''),
        'filename': media_dict.get('filename', '')
    }


def download_media(media_id: str, token: str, file_name: str) -> str:
    """Download and save media file."""
    headers = {'Authorization': f'Bearer {token}'}
    response = _http_session.get(
        f"{WHATSAPP_API_BASE_URL}/{media_id}",
        headers=headers,
        timeout=HTTP_TIMEOUT
    )
    response.raise_for_status()
    
    result_data = response.json()
    file_path = download_and_save_image(
        result_data.get('url'),
        headers,
        MEDIA_BASE_PATH,
        file_name
    )
    return f"{MEDIA_PUBLIC_URL}/{file_path}"


def get_media_file_name(media_type: str, media_data: dict) -> str:
    """Generate appropriate filename for media type."""
    extension = MEDIA_EXTENSIONS.get(media_type)
    if extension:
        return f"{media_data['id']}{extension}"
    else:
        return media_data.get('filename', '')
