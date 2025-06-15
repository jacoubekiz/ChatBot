# from django.contrib.auth.backends import ModelBackend
# from .models import CustomUser

# class EmailBackend(ModelBackend):

#     def authenticate(self, request, username=None, password=None, **kwargs):
        
#         try:
            
#             user = CustomUser.objects.get(email=username)
#             print(user)
#         except CustomUser.DoesNotExist:
#             return None

#         if user.check_password(password):
#             print(user)
#             return user

#     def get_user(self, user_id):
#         try:
#             return CustomUser.objects.get(pk=user_id)
#         except CustomUser.DoesNotExist:
#             return None


# authentication.py

from django.contrib.auth.backends import ModelBackend
from .models import CustomUser

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