from django.urls import path
from .views import *

# from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
# from .serializers import CustomTokenObtainPairSerializer


# class MyTokenObtainPairView(TokenObtainPairView):
#     serializer_class = CustomTokenObtainPairSerializer

urlpatterns = [
    # path('webhook/', WebhookView.as_view(), name='webhook'),
    # path('get-data-from-redis/', GetDataFromRedis.as_view(), name='get-data-from-reis'),
    # path('test-webhook/', ListTestWebhook.as_view(), name='test-webhook'),


    # path('add-user/', AddUsersView.as_view(), name='add-user'),
    # path('get-user/', GetUserView.as_view(), name='get-user '),

    # path('token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    # path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
