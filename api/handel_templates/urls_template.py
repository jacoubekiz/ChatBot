from django.urls import path
from .views import (
    ListCreateTemplate,
    GetUrl,
    GetTemplate,
    SendTemplate,
    FileUploadView,
    ListCreateTemplateButtons,
    UpdateTemplateButtons
)

urlpatterns = [
    path('create-template/<str:channel_id>/', ListCreateTemplate.as_view(), name='create-template'),
    path('get-url/', GetUrl.as_view(), name='handle-file-upload'),
    path('get-template/', GetTemplate.as_view(), name='get-template'),
    path('send-template/<str:channel_id>/', SendTemplate.as_view(), name='send_template'),
    path('file-upload/<str:channel_id>/', FileUploadView.as_view(), name='file-upload'),
    path('create-template-buttons/<str:templatebox_id>/', ListCreateTemplateButtons.as_view()),
    path('update-template-buttons/<str:template_id>/', UpdateTemplateButtons.as_view())
]
