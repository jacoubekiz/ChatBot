from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from api.models import *
import requests
import json
import os
import mimetypes
from api.utils import resolve_app_id_from_token, _http_post, MetaApiError
from pathlib import Path

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
        # if data['type_template'] == "with_header":
        #     file_path = data["template_info"].get('components', [])[0].get('example', {}).get('header_handle', [])[0]
        #     if not os.path.exists(file_path):
        #         raise FileNotFoundError(f"PDF file does not exist: {file_path}")
        #     file_name = os.path.basename(file_path)
        #     with open(file_path, "rb") as f:
        #         file_bytes = f.read()
        #     file_size = len(file_bytes)
        #     file_type = mimetypes.guess_type(file_path)[0]
        #     # 1) Resolve App ID
        #     app_id = resolve_app_id_from_token(f"{channel.tocken[7:]}")
        #     # 2) Start resumable upload session
        #     init_url = f"https://graph.facebook.com/v22.0/{app_id}/uploads"
        #     init_params = {
        #         "file_name": file_name,
        #         "file_length": str(file_size),
        #         "file_type": file_type,
        #         "access_token": f"{channel.tocken[7:]}",
        #     }
        #     init_resp = _http_post(init_url, params=init_params)
        #     init_json = init_resp.json()
        #     upload_session_id = init_json.get("id")
        #     if not upload_session_id:
        #         raise MetaApiError(f"Upload session init did not return id: {init_json}")
        #     # 3) Upload the bytes to the session to obtain the file handle
        #     upload_url = f"https://graph.facebook.com/v22.0/{upload_session_id}"
        #     upload_headers = {
        #         # For the upload step, Meta expects OAuth here (not Bearer)
        #         "Authorization": f"{channel.tocken}",
        #         "file_offset": "0",
        #         # CHANGED: use octet-stream and remove 'Expect' header to avoid HTTP 417
        #         "Content-Type": "application/octet-stream",
        #         "Content-Length": str(file_size),  # requests sets this anyway; harmless to keep
        #     }
        #     upload_resp = _http_post(upload_url, headers=upload_headers, data=file_bytes)
        #     try:
        #         upload_json = upload_resp.json()
        #     except Exception:
        #         raise MetaApiError(f"Upload returned non-JSON (status {upload_resp.status_code}): {upload_resp.text}")

        #     file_handle = upload_json.get("h")
        #     data["template_info"].get('components', [])[0].get('example', {}).update({"header_handle": [file_handle]})
        #     if not file_handle:
        #         raise MetaApiError(f"Upload did not return a file handle: {upload_json}")
        template_data = json.dumps(request.data)
        response = requests.post(url, headers=headers, data=template_data)
        result = response.json()
        return Response(result, status=status.HTTP_200_OK)

class HandleFileUpload(APIView):
    def post(self, request, channel_id):
        channel = Channle.objects.get(channle_id= channel_id)
        file = request.FILES['file']
        file_path = os.path.join(settings.MEDIA_ROOT, file.name)
        if not os.path.exists(f"{file_path}"):
            raise FileNotFoundError(f"PDF file does not exist: {file_path}")
        file_name = os.path.basename(file_path)
        with open(file, "rb") as f:
            file_bytes = f.read()
        file_size = len(file_bytes)
        file_type = mimetypes.guess_type(file)[0]
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
            "Authorization": f"{channel.tocken}",
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
        if not file_handle:
            raise MetaApiError(f"Upload did not return a file handle: {upload_json}")
        return Response({"file_handle": file_handle}, status=status.HTTP_200_OK)
        

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
            wamid = "result.get('messages', '')[0].get('id', '')"
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
            "Authorization": f"{channel.tocken}",
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