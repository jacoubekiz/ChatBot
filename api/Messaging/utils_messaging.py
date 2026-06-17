import json
import os
import requests
from urllib.parse import urlparse
from api.Flow.utils_flow import change_occurences


bearer_token = 'Bearer EAAJCCh5AS8gBOyUjN8UtrTa9p4apLsoMMOTmEJL3ur2TJbniZBOAPReVh6TrmZBMiwg7Ixdqr06H8VTQTNImcBNuZBmbBlcZCKYmMNZCjWFHIjnlQ7ByKZCMjxhLxaCYn7ZCf3U7VGgqyMi4chCfjb899WXV0HBFlEnPhWbZBQUaL54ZAikhNZCOP3pRuGu7YdUREv1WyZAc8w8vAc28gN6yObFeXmVCQL4ZBMxcM1ByZAvEZD'


def send_message(version='18.0',
                wa_id='108253965410678',
                bearer_token=bearer_token,
                messaging_product='whatsapp',
                to='966552345566',
                message_content=None,
                choices=None,
                type='text',
                header=None,
                footer=None,
                interaction_type=None,
                source=None,
                chat_id=None,
                platform='whatsapp',
                beem_media_id=None,
                preview_url: bool = True,
                question=None):
    """Send message via WhatsApp or Beam platform."""
    message_content = change_occurences(message_content, pattern=r'\{\{(\w+)\}\}', chat_id=chat_id, sql=True)
    
    if platform == 'whatsapp':
        url = f"https://graph.facebook.com/v{version}/{wa_id}/messages"
        
        if type == 'interactive':
            if interaction_type == 'list':
                sections = question['sections']
                for section in sections:
                    section['rows'] = section.pop('options')
                    section.pop('id')
                    for row in section['rows']:
                        row['title'] = row.pop('value')
                        if 'next' in row:
                            del row['next']
                payload = json.dumps({
                    "messaging_product": f"{messaging_product}",
                    "recipient_type": "individual",
                    "to": f"{to}",
                    "type": f"{type}",
                    "interactive": {
                        "type": interaction_type,
                        "header": question.get('header'), 
                        "body": {
                            "text": f"{message_content}"
                        },
                        "footer": {
                            "text": f"{footer}"
                        },
                        "action": {
                            "button": "Send",
                            "sections": sections
                        }
                    }
                })
            elif interaction_type == 'button':
                buttons = []
                rows = []
                if len(choices) > 3:
                    title = "message_content"
                    for index, choice in enumerate(choices):
                        row = {
                            "id": f"unique-id-{index}",
                            "title": choice,
                        }
                        rows.append(row)
                        if index == 9:
                            break
                    sections = [{"title": title, "rows": rows}]
                    payload = json.dumps({
                        "messaging_product": f"{messaging_product}",
                        "recipient_type": "individual",
                        "to": f"{to}",
                        "type": f"{type}",
                        "interactive": {
                            "type": "list",
                            "body": {
                                "text": f"{message_content}"
                            },
                            "action": {
                                "button": "Send",
                                "sections": sections
                            }
                        }
                    })
                else:
                    for index, choice in enumerate(choices):
                        button = {
                            "type": "reply",
                            "reply": {
                                "id": f"unique-id-{index}",
                                "title": choice
                            }
                        }
                        buttons.append(button)
                    payload = json.dumps({
                        "messaging_product": "whatsapp",
                        "recipient_type": "individual",
                        "to": f"{to}",
                        "type": "interactive",
                        "interactive": {
                            "type": "button",
                            "body": {
                                "text": f"{message_content}"
                            },
                            "action": {
                                "buttons": buttons
                            }
                        }
                    })
        elif type == 'document':
            filename = os.path.basename(urlparse(source).path)
            payload = json.dumps({
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": f"{to}",
                "type": "document",
                "document": {
                    "link": f"{source}",
                    "caption": f"{message_content}",
                    "filename": f"{filename}"
                }
            })
        elif type == 'image':
            payload = json.dumps({
                "messaging_product": f"{messaging_product}",
                "recipient_type": "individual",
                "to": f"{to}",
                "type": f"{type}",
                "image": {
                    "link": f"{source}",
                    "caption": f"{message_content}"
                }
            })
        elif type == 'video':
            payload = json.dumps({
                "messaging_product": f"{messaging_product}",
                "recipient_type": "individual",
                "to": f"{to}",
                "type": type,
                "video": {
                    "link": source,
                    "caption": question.get('label')
                }
            })
        elif type == 'contact':
            payload = json.dumps({
                "messaging_product": "whatsapp",
                "to": f"{to}",
                "type": "contacts",
                "contacts": [{
                    "emails": [{"email": question.get('contact').get('email')}],
                    "name": {
                        "formatted_name": question.get('contact').get('name').get('formattedName'),
                        "first_name": question.get('contact').get('name').get('firstName'),
                        "last_name": question.get('contact').get('name').get('lastName'),
                        "middle_name": question.get('contact').get('name').get('middleName'),
                        "suffix": question.get('contact').get('name').get('suffix'),
                        "prefix": question.get('contact').get('name').get('prefix'),
                    },
                    "org": {"company": question.get('contact').get('org')},
                    "phones": [{"phone": question.get('contact').get('phone')}],
                    "urls": [{"url": question.get('contact').get('url')}]
                }]
            })
        elif type == 'audio':
            payload = json.dumps({
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": f"{to}",
                "type": type,
                "audio": {"id": source}
            })
        elif type == 'location':
            payload = json.dumps({
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": f"{to}",
                "type": type,
                "location": question['location']
            })
        elif type == 'sticker':
            payload = json.dumps({
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": f"{to}",
                "type": type,
                "audio": {"link": source}
            })
        else:
            payload = json.dumps({
                "messaging_product": f"{messaging_product}",
                "recipient_type": "individual",
                "to": f"{to}",
                "type": f"{type}",
                "text": {"body": f"{message_content}"}
            })

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {bearer_token}'
        }

        response = requests.request("POST", url, headers=headers, data=payload)
        data = json.loads(response.content.decode())
        return data
    
    elif platform == 'beam':
        url = f'https://offapi-sccc-test.rongcloud.net/v1/{wa_id}/message'
        if type == 'interactive':
            if isinstance(choices, list):
                if len(choices) > 3:
                    rows = []
                    for index, choice in enumerate(choices):
                        row = {
                            "id": f'SECTION_1_ROW_{index}_ID',
                            "title": choice,
                            "description": ""
                        }
                        rows.append(row)
                    payload = json.dumps({
                        "to": f"{to}",
                        "type": f"{type}",
                        "interactive": {
                            "type": "list",
                            "header": {"type": "text", "text": f"{header}"},
                            "body": {"text": f"{message_content}"},
                            "footer": {"text": f"{footer}"},
                            "action": {
                                "button": "<BUTTON_TEXT>",
                                "sections": [{"title": "Choose one.", "rows": rows}]
                            }
                        }
                    })
                else:
                    buttons = []
                    for index, choice in enumerate(choices):
                        button = {
                            "type": "reply",
                            "reply": {
                                "id": f"UNIQUE_BUTTON_ID_{index}",
                                "title": choice
                            }
                        }
                        buttons.append(button)
                    payload = json.dumps({
                        "to": f"{to}",
                        "type": f"{type}",
                        "interactive": {
                            "type": "button",
                            "header": {"type": "text", "text": f"{header}"},
                            "body": {"text": f"{message_content}"},
                            "action": {"buttons": buttons}
                        }
                    })
        elif type == 'document' or type == 'image':
            payload = json.dumps({
                "to": f"{to}",
                "type": "media",
                "media": {"id": f"{beem_media_id}"}
            })
        elif type == 'yt_video':
            payload = json.dumps({
                "to": f"{to}",
                "type": "text",
                "text": {
                    "preview_url": preview_url,
                    "body": f'{source}\n{message_content}'
                }
            })
        elif type == 'contact':
            links = [link['value'] for link in source]
            payload = json.dumps({
                "to": f"{to}",
                "type": "text",
                "text": {
                    "preview_url": preview_url,
                    "body": f"{message_content}\n{'-'.join(links)}"
                }
            })
        else:
            payload = json.dumps({
                "to": f"{to}",
                "type": f"{type}",
                "text": {"body": f"{message_content}"}
            })

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {bearer_token}'
        }

        response = requests.request("POST", url, headers=headers, data=payload)


def validate_email(email):
    """Validate email format."""
    import re
    return bool(re.search(r"^[\w\.\+\-]+\@[\w]+\.[a-z]{2,3}$", email))


def validate_phone_number(phone_number):
    """Validate phone number format."""
    import re
    pattern = r'^\s*(?:\+?(\d{1,3}))?[-. (]*(\d{3})[-. )]*(\d{3})[-. ]*(\d{4})(?: *x(\d+))?\s*$'
    if re.match(pattern, phone_number):
        return True
    else:
        return False
