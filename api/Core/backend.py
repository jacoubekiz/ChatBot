from django.contrib.auth.backends import ModelBackend
from api.Auth.models_auth import CustomUser

class CustomAuthBackend(ModelBackend):
    def authenticate(self, request, email=None, password=None, **kwargs):
        try:
            user1 = CustomUser.objects.get(email=email)
            if user1.check_password(password):
                return user1
        except CustomUser.DoesNotExist:
            pass

    def get_user(self, user_id):
        try:
            return CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
           pass