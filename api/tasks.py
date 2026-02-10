from celery import shared_task
import pandas as pd
from .models import *
import requests 
import json

@shared_task
def send_whatsapp_campaign(
        channel, 
        df, 
        account, 
        content_template, user_id, 
        language_code, 
        template_parameters, 
        template_name, 
        whatsappcampaign
    ):
    user = CustomUser.objects.get(id=user_id)
    account_id = Account.objects.get(account_id=account)
    channel_id = Channle.objects.get(channle_id=channel)
    whatsappcampaign_ = WhatsAppCampaign.objects.get(campaign_id=whatsappcampaign)
    # print("Starting WhatsApp campaign task...")
    df_ = json.loads(df)
    print(df_)
    try:
        for row in df_:
            template_info = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": f"{row.get('Phone Dial Code')}{row.get('Phone Number')}",
                "type": "template",
                "template": {
                    "name": f"{template_name}",
                    "language": {
                        "code": f"{language_code}"
                    },
                    "components": 
                            f"{template_parameters}"
                }
            }
            url = f"https://graph.facebook.com/v22.0/{channel_id.phone_number_id}/messages"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"{channel_id.tocken}"
            }
            template_data = json.dumps(template_info)
            response = requests.post(url, headers=headers, data=template_data)
            data_ = json.loads(response.content.decode())
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
                AnalyticsCamaign.objects.create(
                    account_id=account_id,
                    campaign_id=whatsappcampaign_,
                    contact=contact[0],
                    status_message='sent',
                    error_message = None
                )
            except KeyError:
                error_message_ = data_['error'].get('message')
                AnalyticsCamaign.objects.create(
                    account_id=account_id,
                    campaign_id=whatsappcampaign_,
                    contact=contact[0],
                    status_message='failed',
                    error_message = error_message_
                )
    except:
        return Response({'error':'Invalid file format. Please upload a CSV file.'}, status=status.HTTP_400_BAD_REQUEST)