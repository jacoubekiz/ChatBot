"""
api/utils.py - Central utility module with backward compatibility imports.

This module re-exports all utility functions from domain-specific modules
for backward compatibility. New code should import directly from the
domain-specific utility modules:

- api.Core.utils_general: General utilities (hash_key, read_json)
- api.Flow.utils_flow: Flow/Chatbot utilities (show_response, change_occurences, check_sql_condition)
- api.Messaging.utils_messaging: Messaging/WhatsApp utilities (send_message, validate_email, validate_phone_number)
- api.Contact.utils_webhook: Webhook/Redis utilities (handel_request_redis, download_and_save_image)
- api.Consumers.utils_websocket: WebSocket utilities (connect_web_socket, sent_message_*, read_receipt)
- api.Utility.utils_media: Media utilities (download_and_save_image)
- api.Channel.utils_whatsapp_api: WhatsApp API utilities (_raise_for_api_error, _http_get, _http_post, resolve_app_id_from_token)
- api.Utility.utils_audio: Audio processing utilities (which, ffmpeg_has_opus_encoder, run, convert_to_ogg_opus_mono, upload_audio_get_media_id, send_voice_note_with_media_id, process_and_send_voice_note)
"""

# General utilities
from api.Core.utils_general import hash_key, read_json

# Flow/Chatbot utilities
from api.Flow.utils_flow import show_response, change_occurences, check_sql_condition

# Messaging/WhatsApp utilities
from api.Messaging.utils_messaging import (
    send_message,
    validate_email,
    validate_phone_number,
    bearer_token
)

# Webhook/Redis utilities
from api.Utility.utils_webhook import handel_request_redis, download_and_save_image

# WebSocket utilities
from api.Consumers.utils_websocket import (
    connect_web_socket,
    sent_message_text,
    sent_message_image,
    sent_message_video,
    sent_message_audio,
    sent_message_document,
    read_receipt
)

# Media utilities
from api.Utility.utils_media import download_and_save_image

# WhatsApp API utilities
from api.Utility.utils_whatsapp_api import (
    _raise_for_api_error,
    _http_get,
    _http_post,
    resolve_app_id_from_token,
    MetaApiError,
    HTTP_TIMEOUT_GET,
    HTTP_TIMEOUT_POST
)

# Audio processing utilities
from api.Utility.utils_audio import (
    which,
    ffmpeg_has_opus_encoder,
    run,
    convert_to_ogg_opus_mono,
    upload_audio_get_media_id,
    send_voice_note_with_media_id,
    process_and_send_voice_note,
    WhatsAppApiError,
    GRAPH_VERSION,
    TIMEOUT
)

# Re-export all for backward compatibility
__all__ = [
    # General utilities
    'hash_key',
    'read_json',
    # Flow/Chatbot utilities
    'show_response',
    'change_occurences',
    'check_sql_condition',
    # Messaging/WhatsApp utilities
    'send_message',
    'validate_email',
    'validate_phone_number',
    'bearer_token',
    # Webhook/Redis utilities
    'handel_request_redis',
    'download_and_save_image',
    # WebSocket utilities
    'connect_web_socket',
    'sent_message_text',
    'sent_message_image',
    'sent_message_video',
    'sent_message_audio',
    'sent_message_document',
    'read_receipt',
    # Media utilities
    'download_and_save_image',
    # WhatsApp API utilities
    '_raise_for_api_error',
    '_http_get',
    '_http_post',
    'resolve_app_id_from_token',
    'MetaApiError',
    'HTTP_TIMEOUT_GET',
    'HTTP_TIMEOUT_POST',
    # Audio processing utilities
    'which',
    'ffmpeg_has_opus_encoder',
    'run',
    'convert_to_ogg_opus_mono',
    'upload_audio_get_media_id',
    'send_voice_note_with_media_id',
    'process_and_send_voice_note',
    'WhatsAppApiError',
    'GRAPH_VERSION',
    'TIMEOUT',
]
