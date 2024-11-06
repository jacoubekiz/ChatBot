from django.urls import path
from .views import *
urlpatterns = [
    path('webhook/', WebhookView.as_view(), name='webhook'),
    path('get-data-from-redis/', GetDataFromRedis.as_view(), name='get-data-from-reis'),
    path('test-webhook/', ListTestWebhook.as_view(), name='test-webhook'),
]
