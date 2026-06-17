# =========================
# Constants for Chat Consumer
# =========================

class MessageType:
    MESSAGE = "message"
    CONVERSATION = "conversation"
    ERROR = "error"
    MESSAGE_STATUS = "chat_message_status"
    CHAT_MESSAGE = "chat_message"


class ContentType:
    BOT_INTEGRATION = "bot_integration"
    MESSAGE_STATUS = "message_status"
    TEMPLATE = "template"
    AUDIO = "audio"
    IMAGE = "image"
    TEXT = "text"
    DOCUMENT = "document"
    VIDEO = "video"
    VOICE = "voice"

class ContentTypeBot:
    SMART_QUESTION = "smart_question"
    API = "api"
    NAME = "name"
    PHONE = "phone"
    EMAIL = "email"
    LIVE_CHAT = "live_chat"
    QUESTION = "question"
    NUMBER = "number"
    DOCUMENT = "document"
    IMAGE = "image"
    VOICE = "voice"

class MediaType:
    AUDIO = "audio"
    IMAGE = "image"
    DOCUMENT = "document"
    VIDEO = "video"
    VOICE = "voice"


class WhatsAppAPI:
    BASE_URL = "https://graph.facebook.com/v22.0"
    MEDIA_URL = "https://chatapi.icsl.me/"
