from celery import shared_task
from api.Channel.models_channel import Channle
from api.Auth.models_auth import CustomUser
from api.Account.models_account import Account
from api.Contact.models_contact import Contact, Conversation, ChatMessage
from api.Campaign.models_campaign import WhatsAppCampaign, AnalyticsCampaign
import requests 

import json

@shared_task()
def send_whatsapp_campaign(payload):

    data_e = json.loads(payload)
    user = CustomUser.objects.get(id=data_e['user_id'])
    account_id = Account.objects.get(account_id=data_e['account'])
    channel_id = Channle.objects.get(channle_id=data_e['channel'])
    whatsappcampaign_ = WhatsAppCampaign.objects.get(campaign_id=data_e['whatsappcampaign'])
    df_ = json.loads(data_e['df'])
    
    try:
        for row in df_:

            contact = Contact.objects.get_or_create(
                    account_id=account_id,
                    phone_number=f"{row.get('Phone Dial Code')}{row.get('Phone Number')}"
                )
            conversation = Conversation.objects.get_or_create(
                account_id=account_id,
                contact_id=contact[0],
                channle_id=channel_id
            )
            template_info = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": f"{row.get('Phone Dial Code')}{row.get('Phone Number')}",
                "type": "template",
                "template": {
                    "name": f"{data_e['template_name']}",
                    "language": {
                        "code": f"{data_e['language_code']}"
                    },
                    "components": 
                            f"{data_e['template_parameters']}"
                }
            }
            url = f"https://graph.facebook.com/v22.0/{channel_id.phone_number_id}/messages"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {channel_id.tocken}"
            }
            template_data = json.dumps(template_info)
            response = requests.post(url, headers=headers, data=template_data)
            data_ = json.loads(response.content.decode())
            if response.status_code == 200 and 'messages' in data_:
                template_wamid = data_['messages'][0]['id']
                ChatMessage.objects.create(
                    conversation_id=conversation[0],
                    user_id=user,
                    content_type="template",
                    content=data_e['content_template'],
                    wamid=template_wamid
                )
                AnalyticsCampaign.objects.create(
                    account_id=account_id,
                    campaign_id=whatsappcampaign_,
                    contact=contact[0],
                    status_message='sent',
                    error_message = None
                )
            else:
                error_message_ = data_.get('error', {}).get('message', 'Unknown error')
                AnalyticsCampaign.objects.create(
                    account_id=account_id,
                    campaign_id=whatsappcampaign_,
                    contact=contact[0],
                    status_message='failed',
                    error_message = error_message_
                )
        falied_count = AnalyticsCampaign.objects.filter(campaign_id=whatsappcampaign_, status_message='failed').count()
        sent_count = AnalyticsCampaign.objects.filter(campaign_id=whatsappcampaign_, status_message='sent').count()
        total_contacts = AnalyticsCampaign.objects.filter(campaign_id=whatsappcampaign_).count()
        whatsappcampaign_.failed_count = falied_count
        whatsappcampaign_.sent_count = sent_count
        whatsappcampaign_.total_recipients = total_contacts
        whatsappcampaign_.status = 'completed'
        whatsappcampaign_.save()
        return {
            'success': 'True',
            'message': 'WhatsApp campaign sent successfully.',
            'compaign_id': whatsappcampaign_.campaign_id,
            'failed_count': falied_count,
            'sent_count': sent_count,
            'total_contacts': total_contacts
        }

    except Exception as e:
        return {'error': str(e)}
    
