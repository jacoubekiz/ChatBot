from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from api.models import *
import requests
import json

class CreateTemplate(APIView):
    def post(self, request, channel_id):
        channel = Channle.objects.get(channle_id= channel_id)
        url = f"https://graph.facebook.com/v22.0/{channel.organization_id}/message_templates"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"{channel.tocken}"
        }
        data = request.data
        print(data)
        template_data = json.dumps(data)
        response = requests.post(url, headers=headers, data=template_data)
        result = response.json()
        return Response(result, status=status.HTTP_200_OK)


