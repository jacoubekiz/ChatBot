from django.urls import path
from .views_auth import (
    ViewLogin,
    LogoutAPIView,
    RefreshTokenView,
    ChangePasswordView
)

urlpatterns = [
    path('auth/login/', ViewLogin.as_view(), name='log-in'),
    path('auth/logout/', LogoutAPIView.as_view()),
    path('refresh-token/', RefreshTokenView.as_view(), name='refresh_token'),
    path('change-password/<str:user_id>/', ChangePasswordView.as_view(), name='change_password'),
]
