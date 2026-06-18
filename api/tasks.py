from celery import shared_task
from celery.exceptions import Retry
from django.core.cache import cache
from api.Channel.models_channel import Channle
from api.Auth.models_auth import CustomUser
from api.Account.models_account import Account
from api.Contact.models_contact import Contact, Conversation, ChatMessage
from api.Campaign.models_campaign import WhatsAppCampaign, AnalyticsCampaign
import requests
import json
from functools import lru_cache
from typing import Dict, List, Any
from django.db import transaction

# Connection pooling for better performance
_http_session = requests.Session()
_http_session.headers.update({
    'Content-Type': 'application/json',
})

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(requests.exceptions.RequestException,),
)
def send_whatsapp_campaign(self, payload: str) -> Dict[str, Any]:
    """Send WhatsApp campaign with optimized performance and error handling."""
    try:
        data_e = json.loads(payload)
        
        # Optimize database queries with select_related
        user = CustomUser.objects.get(id=data_e['user_id'])
        account = Account.objects.get(account_id=data_e['account'])
        channel = Channle.objects.get(channle_id=data_e['channel'])
        campaign = WhatsAppCampaign.objects.get(campaign_id=data_e['whatsappcampaign'])
        df_ = json.loads(data_e['df'])
        
        sent_count = 0
        failed_count = 0
        analytics_batch = []
        
        # Use transaction for atomic operations
        with transaction.atomic():
            for row in df_:
                phone_number = f"{row.get('Phone Dial Code')}{row.get('Phone Number')}"
                
                # Optimize contact/conversation creation with select_related
                contact, _ = Contact.objects.get_or_create(
                    account_id=account,
                    phone_number=phone_number
                )
                
                conversation, _ = Conversation.objects.get_or_create(
                    account_id=account,
                    contact_id=contact,
                    channle_id=channel
                )
                
                # Build template payload
                template_info = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": phone_number,
                    "type": "template",
                    "template": {
                        "name": data_e['template_name'],
                        "language": {
                            "code": data_e['language_code']
                        },
                        "components": data_e['template_parameters']
                    }
                }
                
                # Use connection pooling and add timeout
                url = f"https://graph.facebook.com/v22.0/{channel.phone_number_id}/messages"
                headers = {
                    "Authorization": f"Bearer {channel.tocken}"
                }
                
                try:
                    response = _http_session.post(url, headers=headers, json=template_info, timeout=30)
                    response.raise_for_status()
                    data_ = response.json()
                    
                    if 'messages' in data_:
                        template_wamid = data_['messages'][0]['id']
                        ChatMessage.objects.create(
                            conversation_id=conversation,
                            user_id=user,
                            content_type="template",
                            content=data_e['content_template'],
                            wamid=template_wamid
                        )
                        analytics_batch.append(AnalyticsCampaign(
                            account_id=account,
                            campaign_id=campaign,
                            contact=contact,
                            status_message='sent',
                            error_message=None
                        ))
                        sent_count += 1
                    else:
                        error_message = data_.get('error', {}).get('message', 'Unknown error')
                        analytics_batch.append(AnalyticsCampaign(
                            account_id=account,
                            campaign_id=campaign,
                            contact=contact,
                            status_message='failed',
                            error_message=error_message
                        ))
                        failed_count += 1
                        
                except requests.exceptions.RequestException as e:
                    analytics_batch.append(AnalyticsCampaign(
                        account_id=account,
                        campaign_id=campaign,
                        contact=contact,
                        status_message='failed',
                        error_message=str(e)
                    ))
                    failed_count += 1
            
            # Bulk create analytics for better performance
            if analytics_batch:
                AnalyticsCampaign.objects.bulk_create(analytics_batch, batch_size=100)
        
        # Update campaign statistics
        campaign.failed_count = failed_count
        campaign.sent_count = sent_count
        campaign.total_recipients = len(df_)
        campaign.status = 'completed'
        campaign.save()
        
        return {
            'success': True,
            'message': 'WhatsApp campaign sent successfully.',
            'campaign_id': campaign.campaign_id,
            'failed_count': failed_count,
            'sent_count': sent_count,
            'total_contacts': len(df_)
        }
        
    except Exception as e:
        # Retry on transient errors
        if isinstance(e, (requests.exceptions.RequestException,)):
            raise self.retry(exc=e, countdown=60)
        return {'error': str(e)}
    
