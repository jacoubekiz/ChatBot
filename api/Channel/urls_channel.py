from django.urls import path
from .views_channel import (
    ListCreateChannelView,
    RetrieveUpdateDeleteChannelView,
)

urlpatterns = [
    path('add-channel/<str:account_id>/', ListCreateChannelView.as_view(), name='add_channel'),
    path('update-delete-channel/<str:account_id>/<str:channel_id>/', RetrieveUpdateDeleteChannelView.as_view(), name='update_delete_channel')
]