from django.urls import path
from .views import (
    ListCreateTemplate,
    HandleFileUpload,
    GetTemplate,
    SendTemplate,
    FileUploadView
)

urlpatterns = [
    path('create-template/<str:channel_id>/', ListCreateTemplate.as_view(), name='create-template'),
    path('handle-file-upload/<str:channel_id>/', HandleFileUpload.as_view(), name='handle-file-upload'),
    path('get-template/', GetTemplate.as_view(), name='get-template'),
    path('send-template/<str:channel_id>/', SendTemplate.as_view(), name='send_template'),
    path('file-upload/<str:channel_id>/', FileUploadView.as_view(), name='file-upload'),
]
