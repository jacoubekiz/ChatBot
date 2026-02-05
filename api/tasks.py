from celery import shared_task
import pandas as pd
from .models import *
import requests 
import json

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 5})
def send_whatsapp_campaign(self, channel_id, data, file, content_template, phone_number_id, tocken, account, user_id):
    user = CustomUser.objects.get(id=user_id)
    account_id = Account.objects.get(id=account)
    print("Starting WhatsApp campaign task...")
    try:
        df = pd.read_csv(file)
        for index, row in df.iterrows():
            template_info = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": f"{row.get('Phone Dial Code')}{row.get('Phone Number')}",
                "type": "template",
                "template": {
                    "name": f"{data.get('template_name')}",
                    "language": {
                        "code": f"{data.get('language_code')}"
                    },
                    "components": 
                            f"{data.get('template_parameters')}"
                }
            }
            url = f"https://graph.facebook.com/v22.0/{phone_number_id}/messages"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"{tocken}"
            }
            template_data = json.dumps(template_info)
            response = requests.post(url, headers=headers, data=template_data)
            data_ = json.loads(response.content.decode())
            print(data_)
            try:
                template_wamid = data_['messages'][0]['id']
                contact = Contact.objects.get_or_create(
                    account_id=account_id,
                    phone_number=f"{row.get('Phone Dial Code')}{row.get('Phone Number')}"
                )
                conversation = Conversation.objects.get_or_create(
                    account_id=account_id,
                    contact_id=contact[0],
                    channle_id=channel_id
                )
                ChatMessage.objects.create(
                    conversation_id=conversation[0],
                    user_id=user,
                    content_type="template",
                    content=content_template,
                    wamid=template_wamid
                )
            except KeyError:
                pass
                # AnalyticsCamaign.objects.create(
                #     account_id=channel_id.account_id,
                #     channel_id=channel_id,
                #     contact=contact[0],
                #     status_message='failed'
                # )
            contact = {
                'name': row.get('Name'),
                'phone_dial_code': str(row.get('Phone Dial Code')),
                'phone_number': str(row.get('Phone Number'))
            }
    except:
        return Response({'error':'Invalid file format. Please upload a CSV file.'}, status=status.HTTP_400_BAD_REQUEST)