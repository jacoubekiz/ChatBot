from django.urls import path
from .views_utility import (
    WebhookView,
    ImageToBase64View,
    UserProfileView
)

urlpatterns = [
    path('user-profile/<str:id>/', UserProfileView.as_view(), name='user_profile'),
    path('webhook/', WebhookView.as_view(), name='webhook'),
    path('convert-image-base64/', ImageToBase64View.as_view(), name='image_to_base64'),
    # path('register-response-client/', RegisterResponseClient.as_view()),
]
