from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
# from django.shortcuts import get_object_or_404
from api.Utility.models_utility import Report
from api.Contact.models_contact import Conversation
from api.Auth.models_auth import CustomUser
from api.Utility.serializers_utility import ReportSerializer
from api.Auth.serializers_auth import UserProfileSerializer
from api.Contact.serializers_contact import ChatMessageSerializer
from api.Core.pagination import CustomPaginatins
import json
import base64
from django.http import JsonResponse
from ..utils import handel_request_redis


class UserProfileView(RetrieveAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'


class ListMessgesForSpecificConversation(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPaginatins

    def get(self, request, conversation_id):
        paginator = CustomPaginatins()
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        messages = conversation.chatmessage_set.all().order_by('-created_at')
        result_page = paginator.paginate_queryset(messages, request)
        messages_serializer = ChatMessageSerializer(result_page, many=True)
        return paginator.get_paginated_response(messages_serializer.data)


@method_decorator(csrf_exempt, name='dispatch')
class WebhookView(APIView):

    def post(self, request):
        try:
            payload = json.dumps(request.data)
            handel_request_redis.delay(payload)
            return Response(status=status.HTTP_200_OK)
        except Exception as e:
            f = open('redis_error.txt', 'a')
            f.write(f"Error processign webhok: {str(e)}" + '\n')
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def get(self, request):
        try:
            data = request.data
            handel_request_redis.delay(data)
            return HttpResponse(data, content_type="text/html")
        except Exception as e:
            f = open('redis_error.txt', 'a')
            f.write(f"Error processign webhok: {str(e)}" + '\n')
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ImageToBase64View(APIView):
    def get(self, request):
        image = request.data['image']
        img_data = image.read()
        encoded_img = base64.b64encode(img_data).decode('utf-8')

        return JsonResponse({
            "base64_image": encoded_img
        })


class ListReportView(ListAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]
