from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from api.Utility.models_utility import UploadImage
from api.Channel.models_channel import Channle
from api.Contact.models_contact import ChatMessage, Conversation
import requests
import json
import os
import mimetypes
from urllib.parse import quote
from django.core.files.storage import default_storage
from api.Flow.models_flow import Flow
from .models_template import TemplateBox, Template, TemplateBoxTemplate
from api.Account.models_account import Account
from api.utils import resolve_app_id_from_token, _http_post, MetaApiError
from rest_framework.permissions import IsAuthenticated
from django.conf import settings

class ListCreateTemplate(APIView):

    def get(self, request, channel_id):
        channel = get_object_or_404(Channle, channle_id= channel_id)
        url = f"https://graph.facebook.com/v22.0/{channel.organization_id}/message_templates"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {channel.tocken}"
        }
        response = requests.get(url, headers=headers)
        responses = []
        results = response.json()
        for result in results.get('data', []):
            responses.append(
                {
                    "name":result.get('name', ''),
                    "category": result.get('category', ''),
                    "status" : result.get('status', ''),
                    "language": result.get('language', ''),
                    "id": result.get('id', ''),
                    "components": result.get('components', [])
                }
            )

            print(results)
        return Response({"results":responses}, status=status.HTTP_200_OK)
    
    def post(self, request, channel_id):
        channel = get_object_or_404(Channle, channle_id= channel_id)
        url = f"https://graph.facebook.com/v22.0/{channel.organization_id}/message_templates"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {channel.tocken}"
        }
        data = request.data
        template_data = json.dumps(request.data)
        response = requests.post(url, headers=headers, data=template_data)
        result = response.json()
        return Response(result, status=status.HTTP_200_OK)

class GetUrl(APIView):
    def post(self, request):
        # channel = get_object_or_404(Channle, channle_id=channel_id)
        file = request.FILES.get('file')
        
        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate unique filename to avoid conflicts
        file_extension = os.path.splitext(file.name)[1]
        unique_filename = f"{file.name.split('.')[0]}_{os.urandom(8).hex()}{file_extension}"
        
        # Save file to media/uploads directory
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, unique_filename)
        
        # Save the uploaded file
        with open(file_path, 'wb') as f:
            for chunk in file.chunks():
                f.write(chunk)
        
        # Generate full URL for the uploaded file with domain and URL-encoded filename
        base_url = "https://chatapi.icsl.me"
        encoded_filename = quote(unique_filename)
        file_url = f"{base_url}{settings.MEDIA_URL}uploads/{encoded_filename}"
        
        # Get file details
        file_size = os.path.getsize(file_path)
        file_type = mimetypes.guess_type(unique_filename)[0] or 'application/octet-stream'
        
        data = {
            'url': file_url,
            'file_name': unique_filename,
            'file_size': file_size,
            'file_type': file_type,
            'original_name': file.name
        }
        
        return Response(data, status=status.HTTP_200_OK)
        

class GetTemplate(APIView):
    def get(self, request):
        template_id = request.GET.get('template_id')
        channel_id = request.GET.get('channel_id')
        channel = get_object_or_404(Channle, channle_id= channel_id)
        url = f"https://graph.facebook.com/v22.0/{template_id}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {channel.tocken}"
        }

        response = requests.get(url, headers=headers)
        return Response(response.json(), status=status.HTTP_200_OK)
    

template_info = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": "{{phone_number}}",
        "type": "template",
        "template": {
            "name": "{{name}}",
            "language": {
                "code": "{{lang_code}}"
            },
            "components": "{{components}}"
        }
    }
class SendTemplate(APIView):

    def post(self, request, channel_id):
        channel = get_object_or_404(Channle ,channle_id= channel_id)
        apiKey = request.headers.get('apiKey')
        if channel.account_id.apiKey != apiKey:
            return Response({"error": "Invalid API key"}, status=status.HTTP_401_UNAUTHORIZED)
        
        url = f"https://graph.facebook.com/v22.0/{channel.phone_number_id}/messages"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {channel.tocken}"
        }
        
        # Get template info from request
        template_info_request = request.data.get('template_info', {})
        
        # Build template payload
        template_payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": template_info_request.get('to'),
            "type": "template",
            "template": {
                "name": template_info_request.get('template', {}).get('name'),
                "language": {
                    "code": template_info_request.get('template', {}).get('language', {}).get('code')
                },
                "components": template_info_request.get('template', {}).get('components', [])
            }
        }
        
        # Filter out button components with empty parameters
        components = template_payload["template"]["components"]
        filtered_components = []
        for component in components:
            if component.get("type") == "button":
                # Only include button if it has parameters
                if component.get("parameters") and len(component.get("parameters", [])) > 0:
                    filtered_components.append(component)
            else:
                filtered_components.append(component)
        
        template_payload["template"]["components"] = filtered_components
        
        template_data = json.dumps(template_payload)
        conversation = Conversation.objects.get(contact_id__phone_number=template_info_request.get('to'))
        response = requests.post(url, headers=headers, data=template_data)
        result = response.json()
        
        # Check for errors in response
        if 'error' in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        chat_message = ChatMessage.objects.create(
            conversation_id = conversation,
            content_type = "text",
            content = request.data.get('content', ''),
            from_message = 'bot',
            wamid = result.get('messages', [{}])[0].get('id', '')
        )
        return Response(result, status=status.HTTP_200_OK)
    
class FileUploadView(APIView):
    def post(self, request, channel_id):
        channel = Channle.objects.get(channle_id= channel_id)
        file = request.FILES['file']
        file_instance = UploadImage.objects.create(image_file=file)
        file_path = os.path.join(settings.MEDIA_ROOT, file_instance.image_file.name)
        if not os.path.exists(file_path):
                raise FileNotFoundError(f"PDF file does not exist: {file_path}")
        file_name = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        file_size = len(file_bytes)
        file_type = mimetypes.guess_type(file_path)[0]
        # 1) Resolve App ID
        app_id = resolve_app_id_from_token(f"{channel.tocken[7:]}")
        # 2) Start resumable upload session
        init_url = f"https://graph.facebook.com/v22.0/{app_id}/uploads"
        init_params = {
            "file_name": file_name,
            "file_length": str(file_size),
            "file_type": file_type,
            "access_token": f"{channel.tocken[7:]}",
        }
        init_resp = _http_post(init_url, params=init_params)
        init_json = init_resp.json()
        upload_session_id = init_json.get("id")
        if not upload_session_id:
            raise MetaApiError(f"Upload session init did not return id: {init_json}")
        # 3) Upload the bytes to the session to obtain the file handle
        upload_url = f"https://graph.facebook.com/v22.0/{upload_session_id}"
        upload_headers = {
            # For the upload step, Meta expects OAuth here (not Bearer)
            "Authorization": f"Bearer {channel.tocken}",
            "file_offset": "0",
            # CHANGED: use octet-stream and remove 'Expect' header to avoid HTTP 417
            "Content-Type": "application/octet-stream",
            "Content-Length": str(file_size),  # requests sets this anyway; harmless to keep
        }
        upload_resp = _http_post(upload_url, headers=upload_headers, data=file_bytes)
        try:
            upload_json = upload_resp.json()
        except Exception:
            raise MetaApiError(f"Upload returned non-JSON (status {upload_resp.status_code}): {upload_resp.text}")

        file_handle = upload_json.get("h")
        return Response({"file_handle": file_handle}, status=status.HTTP_201_CREATED)

class ListCreateTemplateButtons(APIView):
    permission_classes = [IsAuthenticated,]

    def post(self, request, templatebox_id):
        template_box = get_object_or_404(TemplateBox, id=templatebox_id)
        account = get_object_or_404(Account, account_id=template_box.account.account_id)

        template = Template.objects.create(
            account=account,
            template_id = request.data['template_id'],
            template_name = request.data['template_name']
        )
        for button in request.data['buttons'] :
            flow = get_object_or_404(Flow, id=button.get('flow_id', ''))
            template_buttons = TemplateBoxTemplate.objects.create(
                template_box = template_box,
                template = template,
                button_name = button.get('button_name', ''),
                flow = flow
            )

        return Response(status=status.HTTP_201_CREATED)