import json
import os
import re
import requests
from urllib.parse import urlparse
from functools import lru_cache
from typing import Dict, Any, Optional, List
from api.Flow.utils_flow import change_occurences
from dotenv import load_dotenv
import environ

env = environ.Env()
load_dotenv()

BEARER_TOKEN = env('BEARER_TOKEN')

# Pre-compiled regex patterns for validation
EMAIL_PATTERN = re.compile(r"^[\w\.\+\-]+\@[\w]+\.[a-z]{2,3}$")
PHONE_PATTERN = re.compile(r'^\s*(?:\+?(\d{1,3}))?[-. (]*(\d{3})[-. )]*(\d{3})[-. ]*(\d{4})(?: *x(\d+))?\s*$')

# Connection pooling for better performance
_session = requests.Session()
_session.headers.update({
    'Content-Type': 'application/json',
})


def _build_whatsapp_interactive_list(message_content: str, to: str, footer: str, sections: List[Dict]) -> Dict:
    """Build WhatsApp interactive list message payload."""
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": sections[0].get('header') if sections else None,
            "body": {"text": message_content},
            "footer": {"text": footer},
            "action": {
                "button": "Send",
                "sections": sections
            }
        }
    }


def _build_whatsapp_interactive_button(message_content: str, to: str, buttons: List[Dict]) -> Dict:
    """Build WhatsApp interactive button message payload."""
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": message_content},
            "action": {"buttons": buttons}
        }
    }


def _build_whatsapp_text_message(message_content: str, to: str, msg_type: str = 'text') -> Dict:
    """Build WhatsApp text message payload."""
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": msg_type,
        "text": {"body": message_content}
    }


def _build_whatsapp_media_message(message_content: str, to: str, source: str, media_type: str, filename: Optional[str] = None) -> Dict:
    """Build WhatsApp media message payload."""
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": media_type,
        media_type: {"link": source}
    }
    
    if message_content:
        payload[media_type]["caption"] = message_content
    if filename:
        payload[media_type]["filename"] = filename
        
    return payload


def _process_whatsapp_list_sections(sections: List[Dict]) -> List[Dict]:
    """Process and transform WhatsApp list sections."""
    processed_sections = []
    for section in sections:
        processed_section = section.copy()
        processed_section['rows'] = section.pop('options', [])
        processed_section.pop('id', None)
        
        for row in processed_section['rows']:
            row['title'] = row.pop('value', row.get('title', ''))
            row.pop('next', None)
            
        processed_sections.append(processed_section)
    return processed_sections


def _create_choice_rows(choices: List[str], max_choices: int = 10, id_prefix: str = "unique-id-") -> List[Dict]:
    """Create choice rows for interactive messages."""
    rows = []
    for index, choice in enumerate(choices[:max_choices]):
        rows.append({
            "id": f"{id_prefix}{index}",
            "title": choice,
        })
    return rows


def _create_choice_buttons(choices: List[str], max_buttons: int = 3, id_prefix: str = "unique-id-") -> List[Dict]:
    """Create choice buttons for interactive messages."""
    buttons = []
    for index, choice in enumerate(choices[:max_buttons]):
        buttons.append({
            "type": "reply",
            "reply": {
                "id": f"{id_prefix}{index}",
                "title": choice
            }
        })
    return buttons


def _send_api_request(url: str, payload: Dict, bearer_token: str, timeout: int = 30) -> Dict:
    """Send API request with error handling and timeout."""
    try:
        headers = {
            'Authorization': f'Bearer {bearer_token}'
        }
        response = _session.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "status": "failed"}


def send_message(version: str = '18.0',
                wa_id: str = '108253965410678',
                bearer_token: str = BEARER_TOKEN,
                messaging_product: str = 'whatsapp',
                to: str = '966552345566',
                message_content: Optional[str] = None,
                choices: Optional[List[str]] = None,
                type: str = 'text',
                header: Optional[str] = None,
                footer: Optional[str] = None,
                interaction_type: Optional[str] = None,
                source: Optional[str] = None,
                chat_id: Optional[str] = None,
                platform: str = 'whatsapp',
                beem_media_id: Optional[str] = None,
                preview_url: bool = True,
                question: Optional[Dict] = None) -> Dict:
    """Send message via WhatsApp or Beam platform with improved performance."""
    # Early validation
    if not to:
        return {"error": "Recipient 'to' is required", "status": "failed"}
    
    if not bearer_token:
        return {"error": "Bearer token is required", "status": "failed"}
    
    # Process message content
    if message_content and chat_id:
        message_content = change_occurences(message_content, pattern=r'\{\{(\w+)\}\}', chat_id=chat_id, sql=True)
    
    if platform == 'whatsapp':
        url = f"https://graph.facebook.com/v{version}/{wa_id}/messages"
        payload = {}
        
        if type == 'interactive':
            if interaction_type == 'list':
                sections = _process_whatsapp_list_sections(question['sections'])
                payload = _build_whatsapp_interactive_list(message_content, to, footer or '', sections)
            elif interaction_type == 'button':
                if choices and len(choices) > 3:
                    rows = _create_choice_rows(choices, max_choices=10)
                    sections = [{"title": "message_content", "rows": rows}]
                    payload = _build_whatsapp_interactive_list(message_content, to, footer or '', sections)
                else:
                    buttons = _create_choice_buttons(choices or [], max_buttons=3)
                    payload = _build_whatsapp_interactive_button(message_content, to, buttons)
        elif type == 'document':
            filename = os.path.basename(urlparse(source).path) if source else 'document'
            payload = _build_whatsapp_media_message(message_content, to, source, type, filename)
        elif type == 'image':
            payload = _build_whatsapp_media_message(message_content, to, source, type)
        elif type == 'video':
            payload = _build_whatsapp_media_message(question.get('label') if question else None, to, source, type)
        elif type == 'contact':
            contact = question.get('contact', {}) if question else {}
            contact_name = contact.get('name', {})
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "contacts",
                "contacts": [{
                    "emails": [{"email": contact.get('email')}],
                    "name": {
                        "formatted_name": contact_name.get('formattedName'),
                        "first_name": contact_name.get('firstName'),
                        "last_name": contact_name.get('lastName'),
                        "middle_name": contact_name.get('middleName'),
                        "suffix": contact_name.get('suffix'),
                        "prefix": contact_name.get('prefix'),
                    },
                    "org": {"company": contact.get('org')},
                    "phones": [{"phone": contact.get('phone')}],
                    "urls": [{"url": contact.get('url')}]
                }]
            }
        elif type == 'audio':
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": type,
                "audio": {"id": source}
            }
        elif type == 'location':
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": type,
                "location": question['location'] if question else {}
            }
        elif type == 'sticker':
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": type,
                "sticker": {"link": source}
            }
        else:
            payload = _build_whatsapp_text_message(message_content or '', to, type)
        
        return _send_api_request(url, payload, bearer_token)
    
    elif platform == 'beam':
        url = f'https://offapi-sccc-test.rongcloud.net/v1/{wa_id}/message'
        payload = {}
        
        if type == 'interactive':
            if isinstance(choices, list):
                if len(choices) > 3:
                    rows = _create_choice_rows(choices, max_choices=10, id_prefix="SECTION_1_ROW_")
                    for row in rows:
                        row["description"] = ""
                    payload = {
                        "to": to,
                        "type": type,
                        "interactive": {
                            "type": "list",
                            "header": {"type": "text", "text": header or ""},
                            "body": {"text": message_content or ""},
                            "footer": {"text": footer or ""},
                            "action": {
                                "button": "<BUTTON_TEXT>",
                                "sections": [{"title": "Choose one.", "rows": rows}]
                            }
                        }
                    }
                else:
                    buttons = _create_choice_buttons(choices, max_buttons=3, id_prefix="UNIQUE_BUTTON_ID_")
                    payload = {
                        "to": to,
                        "type": type,
                        "interactive": {
                            "type": "button",
                            "header": {"type": "text", "text": header or ""},
                            "body": {"text": message_content or ""},
                            "action": {"buttons": buttons}
                        }
                    }
        elif type in ('document', 'image'):
            payload = {
                "to": to,
                "type": "media",
                "media": {"id": beem_media_id}
            }
        elif type == 'yt_video':
            payload = {
                "to": to,
                "type": "text",
                "text": {
                    "preview_url": preview_url,
                    "body": f'{source}\n{message_content}' if source and message_content else source or message_content or ''
                }
            }
        elif type == 'contact':
            if isinstance(source, list):
                links = [link.get('value', '') for link in source]
                payload = {
                    "to": to,
                    "type": "text",
                    "text": {
                        "preview_url": preview_url,
                        "body": f"{message_content}\n{'-'.join(links)}" if message_content else '-'.join(links)
                    }
                }
        else:
            payload = {
                "to": to,
                "type": type,
                "text": {"body": message_content or ""}
            }
        
        return _send_api_request(url, payload, bearer_token)
    
    return {"error": f"Unsupported platform: {platform}", "status": "failed"}


def validate_email(email: str) -> bool:
    """Validate email format using pre-compiled regex pattern."""
    if not email:
        return False
    return bool(EMAIL_PATTERN.match(email))


def validate_phone_number(phone_number: str) -> bool:
    """Validate phone number format using pre-compiled regex pattern."""
    if not phone_number:
        return False
    return bool(PHONE_PATTERN.match(phone_number))
