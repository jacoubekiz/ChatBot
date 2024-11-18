# from datetime import datetime
# from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
# from rest_framework.generics import GenericAPIView
# from rest_framework.generics import ListAPIView, ListCreateAPIView
from rest_framework.response import Response
from rest_framework import status
# from rest_framework.permissions import IsAuthenticated
# from django_redis import get_redis_connection
# from django.utils.decorators import method_decorator
# from .permissions import UserIsAdmin
# from .serializers import *
from .models import *

from django.core.files.base import ContentFile

class uploadfile(APIView):
    def post(self, request):
        file_name = request.data['name']+'test.txt'
        print(file_name)
        with open(f'media/files/{file_name}', 'a') as f:
            f.write(f'''
اسم المستخدم: {request.data['name']}
------------------------------------
رقم هاتف المستخدم: {request.data['phonenumber']}
------------------------------------
بناء القائد في تجربتك, هل تنصح الآخرين بالتعامل معنا؟ {request.data['deal_with_us']}
------------------------------------
هل سيتم إعادة الشراء من متجر سندس؟ {request.data['re_purchase']}
------------------------------------
هل لديك اقتراحات أو تعليقات توجه إلى تجربتنا؟ {request.data['suggestion']}
------------------------------------
ما أكثر خدمة الاستقبال الخاصة بك في تجربتك معنا؟ {request.data['reception_service']}
------------------------------------
ما مدى رضاك العام عن خدماتنا ومنتجاتنا؟ {request.data['evaluation']}
''')
        file = open(f'media/files/{file_name}', 'rb')
        file_content = file.read()
        print(file_content)
        file_obj = ContentFile(file_content, name='test.txt')
        map_ = MapFile.objects.create(map_name='test', map_data=file_obj)
        return Response({'messa':"true"})
# @method_decorator(csrf_exempt, name='dispatch')
# class WebhookView(APIView):
#     # @csrf_exempt
#     def post(self, request):
#         try:
#             data = request.data
#             redis_client = get_redis_connection()
#             redis_client.rpush('data_queue', json.dumps(data))
#             f = open('content_redis.txt', 'a')
#             f.write(str(data) + '\n')
#             return Response(status=status.HTTP_200_OK)
#         except Exception as e:
#             print(f"Error processign webhok: {str(e)}")
#             return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# @method_decorator(csrf_exempt, name='dispatch')
# class GetDataFromRedis(APIView):

#     def get(self, request):
#         redis_client = get_redis_connection()
#         raw_data = redis_client.lpop('data_queue')
#         log_entry = json.loads(raw_data)
#         f = open('content_redis.txt', 'a')
#         f.write(str(log_entry) + '\n')
#         return Response({'message':raw_data}, status=status.HTTP_200_OK)
    
# class ListTestWebhook(ListAPIView):
#     queryset = TestWebhook.objects.all()
#     serializer_class = TestWebhookSerializer

# class AddUsersView(ListCreateAPIView):
#     # permission_classes = [IsAuthenticated, UserIsAdmin]
#     queryset = Custom2User.objects.all()
#     serializer_class = AddUserSerializer

#     def get_permissions(self):
#         self.request.pk = self.kwargs.get('pk') # Pass the pk to the request
#         return super().get_permissions()

# # class YourListView(ListCreateAPIView):
# #     permission_classes = [IsAuthenticated]
# #     serializer_class = AddUserSerializer
    
# #     def list(self, request, *args, **kwargs):
# #         # Get the authenticated user's ID
# #         user_id = request.user.id
        
# #         # Pass the user_id to your custom permission
# #         permission = YourCustomPermission()
# #         permission.has_permission(None, None, user_id)
        
# #         # Proceed with the list operation
# #         response = super().list(request, *args, **kwargs)
# #         return response
    
# #     def create(self, request, *args, **kwargs):
# #         # Get the authenticated user's ID
# #         user_id = request.user.id
        
# #         # Pass the user_id to your custom permission
# #         permission = YourCustomPermission()
# #         permission.has_permission(None, None, user_id)
        
# #         # Proceed with the create operation
# #         response = super().create(request, *args, **kwargs)
# #         return response

# class GetUserView(GenericAPIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         print(request.user.id)
#         # try:
#         user = Custom2User.objects.get(pk=request.user.id)
#         print(user.id)
#         # except:
#             # pass
#         # try:
#         #     user = CustomUser.objects.get(pk=request.user.id)
#         #     print(user.id)
#         # except:
#         #     pass
#         return Response({'user':user.id})
# # class LoginView(GenericAPIView):
# #     def post(self, request):
# #         data = request.data
# #         serializer = LoginSerializer(data=data)
# #         if serializer.is_valid(raise_exception=True):
# #             user = Custom2User.objects.get(email=data['username'])
# #             token = RefreshToken.for_user(user)

# #             user_data = {
# #                 'tokens' : {
# #                     'refresh':str(token), 
# #                     'access':str(token.access_token)
# #                 },
# #                 'user_id':user.id,
# #                 'name':user.username,
# #                 'role':user.role
# #             } 
# #             return Response(user_data, status=status.HTTP_200_OK)
# #         else:
# #             return Response(serializer.error_messages, status=status.HTTP_400_BAD_REQUEST)



