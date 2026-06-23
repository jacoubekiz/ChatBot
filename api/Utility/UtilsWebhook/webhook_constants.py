"""
Configuration constants for webhook processing.
"""

# WhatsApp API Configuration
WHATSAPP_API_BASE_URL = "https://graph.facebook.com/v15.0"

# Media Configuration
MEDIA_BASE_PATH = "/www/wwwroot/chatapi.icsl.me/media/chat_message"
MEDIA_PUBLIC_URL = "https://chatapi.icsl.me/media/chat_message"

# Cache Configuration
CACHE_TIMEOUT = 3600  # 1 hour

# HTTP Configuration
HTTP_TIMEOUT = 30

# File Extensions by Media Type
MEDIA_EXTENSIONS = {
    'image': '.jpeg',
    'video': '.mp4',
    'audio': '.ogg',
    'document': None  # Uses original filename
}
