from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # re_path(r'^ws/chat/(?P<conversation_id>\w+)/(?P<contact_phonenumber>\w+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'^ws/chat/(?P<channel_id>\w+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'^ws/list-conversation/(?P<channel_id>\w+)/$', consumers.ListAllConversations.as_asgi()),
    re_path(r'^ws/start-chat-bot/(?P<channel_id>\w+)/(?P<conversation_id>\w+)/$', consumers.ChatBotConsumer.as_asgi()),
]