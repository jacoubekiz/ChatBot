# from django.contrib.auth.backends import ModelBackend
# from .models import Custom2User

# class CustomAuthBackend(ModelBackend):
#     def authenticate(self, request, username=None, password=None, **kwargs):
#         try:
#             user = Custom2User.objects.get(email=username)
#             if user.password == password:
#                 return user
#         except Custom2User.DoesNotExist:
#             return None

#     def get_user(self, user_id):
#         try:
#             return Custom2User.objects.get(pk=user_id)
#         except Custom2User.DoesNotExist:
#             return None