from django.urls import path
from .views_messaging import (
    CreateListQuickReplyView,
    RetrieveUpdateDeleteQuickReplyView,
    ListCreateTriggerView,
    RetrieveUpdateDeleteTriggerView,
    ListCreateGroupView,
    RetrieveUpdateDeleteGroupView,
    ListMessgesForSpecificConversation,
)

urlpatterns = [
    path('list-messages/<str:conversation_id>/', ListMessgesForSpecificConversation.as_view(), name='list-messages'),
    path('quick-reply/<str:account_id>/', CreateListQuickReplyView.as_view(), name='quick_replies'),
    path('delete-retriev-update-quick-reply/<str:quickreply_id>/<str:account_id>/', RetrieveUpdateDeleteQuickReplyView.as_view(), name='delete_quick_reply'),
    path('triggers/<str:account_id>/', ListCreateTriggerView.as_view(), name='triggers'),
    path('delete-retriev-update-trigger/<str:id>/<str:account_id>/', RetrieveUpdateDeleteTriggerView.as_view(), name='delete_trigger'),
    path('list-create-group/<str:account_id>/', ListCreateGroupView.as_view(), name='list_create_group'),
    path('ret-up-del-group/<str:id>/<str:account_id>/', RetrieveUpdateDeleteGroupView.as_view(), name='ret_up_del_group'),
]
