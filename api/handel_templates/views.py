from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from api.models import *
import requests
import json

class ListCreateTemplate(APIView):

    def get(self, request, channel_id):
        channel = Channle.objects.get(channle_id= channel_id)
        url = f"https://graph.facebook.com/v22.0/{channel.organization_id}/message_templates"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"{channel.tocken}"
        }
        response = requests.get(url, headers=headers)
        responses = []
        results = response.json()
        print(results)
        for result in results.get('data', []):
            responses.append(
                {
                    "name":result.get('name', ''),
                    "category": result.get('category', ''),
                    "status" : result.get('status', ''),
                    "language": result.get('language', ''),
                    "id": result.get('id', '')
                }
            )
        return Response({"results":responses}, status=status.HTTP_200_OK)
    
    def post(self, request, channel_id):
        channel = Channle.objects.get(channle_id= channel_id)
        url = f"https://graph.facebook.com/v22.0/{channel.organization_id}/message_templates"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"{channel.tocken}"
        }
        data = request.data
        template_data = json.dumps(data)
        response = requests.post(url, headers=headers, data=template_data)
        result = response.json()
        return Response(result, status=status.HTTP_200_OK)

class GetTemplate(APIView):
    def get(self, request):
        template_id = request.GET.get('template_id')
        channel_id = request.GET.get('channel_id')
        channel = Channle.objects.get(channle_id= channel_id)
        url = f"https://graph.facebook.com/v22.0/{template_id}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"{channel.tocken}"
        }

        response = requests.get(url, headers=headers)
        print(response.json())
        return Response(response.json(), status=status.HTTP_200_OK)
    
class SendTemplate(APIView):
    def post(self, request, channel_id):
        channel = Channle.objects.get(channle_id= channel_id)
        url = f"https://graph.facebook.com/v22.0/{channel.phone_number_id}/messages"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"{channel.tocken}"
        }
        data = request.data
        template_data = json.dumps(data)
        # print(template_data)
        conversation = Conversation.objects.get(contact_id__phone_number=data.get('to'))
        response = requests.post(url, headers=headers, data=template_data)
        result = response.json()
        chat_message = ChatMessage.objects.create(
            conversation_id = conversation,
            # user_id = CustomUser1.objects.filter(id=15).first(),
            content_type = "text",
            content = data.get('content_template', ''),
            from_message = 'bot',
            wamid = result.get('messages', '')[0].get('id', '')
        )
        return Response(result, status=status.HTTP_200_OK)
    
# class TestView(APIView):
#     pass