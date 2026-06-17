from django.urls import path
from .views_contact import (
    CreateNewContact,
    RetrieveUpdateDestroyContactView,
    ListContactView,
    ListConversationView,
    DeleteConversation,
    ReasignConversation,
    InitiateLiveChat,
    ChangeConversationStatus,
    CreateTagView,
    AddTagToConversation
)

urlpatterns = [
    path('tags/<str:account_id>/', CreateTagView.as_view(), name='create_tag'),
    path('add-tag-to-conversation/<str:conversation_id>/', AddTagToConversation.as_view(), name='add_tag_to_conversation'),
    path('create-contact/<account_id>/<channel_id>/', CreateNewContact.as_view(), name='create_contact'),
    path('update-delete-contact/<str:contact_id>/<str:channel_id>/', RetrieveUpdateDestroyContactView.as_view(), name='update_delete_contact'),
    path('contacts/', ListContactView.as_view(), name='contacts'),
    path('conversations/<str:channel_id>/', ListConversationView.as_view(), name='conversations'),
    path('conversation-delete/<str:conversation_id>/', DeleteConversation.as_view(), name='conversation_delete'),
    path('reassign-conversation/<str:conversation_id>/', ReasignConversation.as_view(), name='reassign_conversation'),
    # path('list-messages/<str:conversation_id>/', ListMessgesForSpecificConversation.as_view(), name='list-messages'),
    path('initite-live-chat/<str:conversation_id>/', InitiateLiveChat.as_view(), name='initite_live_chat'),
    path('change-conversation-status/<str:conversation_id>/', ChangeConversationStatus.as_view(), name='change_conversation_status'),
]
