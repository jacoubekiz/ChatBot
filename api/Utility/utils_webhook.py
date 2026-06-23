"""
Main Celery task for webhook processing.
This module serves as the entry point for webhook processing,
delegating to specialized modules for handling different aspects.
"""
import json
import requests
from celery import shared_task
from api.Contact.models_contact import ChatMessage
from api.Channel.models_channel import Channle
from .UtilsWebhook import (
    log_webhook_data,
    log_error,
    handle_status_update,
    handle_incoming_message,
    handle_event_status
)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(requests.exceptions.RequestException,),
)
def handel_request_redis(self, data: str) -> dict:
    """
    Handle webhook data from Redis queue with optimized performance.
    
    This task processes WhatsApp webhook data including:
    - Message status updates
    - Incoming text messages
    - Incoming media messages (image, video, audio, document)
    - Event status updates
    
    Features:
    - Connection pooling for HTTP requests
    - Database query optimization with select_related
    - Caching for frequently accessed data
    - Proper error handling and retry logic
    - Transaction management for data consistency
    - Modular code structure for maintainability
    """
    if not data:
        return {'error': 'No data provided'}
    
    log_webhook_data(data)
    
    try:
        log_entry = json.loads(data)
        entries = log_entry.get('entry', [])
        
        if not entries:
            return {'error': 'No entries found'}
        
        changes = entries[0].get('changes', [])
        if not changes:
            return {'error': 'No changes found'}
        
        value = changes[0].get('value', {})
        
        # Handle message status updates
        if value.get('statuses'):
            return handle_status_update(value)
        
        # Handle incoming messages
        if value.get('messages'):
            return handle_incoming_message(value)
        
        # Handle event status updates
        if log_entry.get('event'):
            return handle_event_status(log_entry)
        
        return {'error': 'Unknown webhook type'}
        
    except ChatMessage.DoesNotExist:
        log_error(f"ChatMessage not found: {data}")
        return {'error': 'ChatMessage not found'}
    except Channle.DoesNotExist:
        log_error(f"Channel not found: {data}")
        return {'error': 'Channel not found'}
    except requests.exceptions.RequestException as e:
        log_error(f"HTTP request error: {e}")
        raise self.retry(exc=e, countdown=30)
    except json.JSONDecodeError as e:
        log_error(f"JSON decode error: {e}")
        return {'error': 'Invalid JSON data'}
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        return {'error': str(e)}
