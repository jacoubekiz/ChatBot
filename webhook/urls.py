from django.urls import path
from .views import *


urlpatterns = [
    path('upload-file/', uploadfile.as_view(), name='webhook'),
]
