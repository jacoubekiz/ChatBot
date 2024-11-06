from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework import status
from django_redis import get_redis_connection
from django.utils.decorators import method_decorator
from .serializers import *
from .models import *
import json

@method_decorator(csrf_exempt, name='dispatch')
class WebhookView(APIView):
    # @csrf_exempt
    def post(self, request):
        try:
            data = request.data
            redis_client = get_redis_connection()
            redis_client.rpush('data_queue', json.dumps(data))
            f = open('content_redis.txt', 'a')
            f.write(str(data) + '\n')
            return Response(status=status.HTTP_200_OK)
        except Exception as e:
            print(f"Error processign webhok: {str(e)}")
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class GetDataFromRedis(APIView):

    def get(self, request):
        redis_client = get_redis_connection()
        raw_data = redis_client.lpop('data_queue')
        # print(raw_data)
        return Response({'message':raw_data}, status=status.HTTP_200_OK)
    
class ListTestWebhook(ListAPIView):
    queryset = TestWebhook.objects.all()
    serializer_class = TestWebhookSerializer