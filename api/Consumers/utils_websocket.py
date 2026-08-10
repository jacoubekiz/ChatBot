import json
import websocket


def connect_web_socket(channel_id, conversation_id, source_id, content, wamid, contact_name, contact_id, account):
    """Connect to WebSocket and send bot integration message."""
    account_id = account.account_id if hasattr(account, 'account_id') else account
    url_ws = f"wss://chatapi.icsl.me/ws/chat/{account_id}/?token=&from_bot=False"
    ws = websocket.WebSocket()
    ws.connect(url_ws)
    data = {
        "conversation_id": f"{conversation_id}",
        "content_type": "bot_integration",
        "channel_id": f"{channel_id}",
        "from_bot": "True",
        "data": {
            "content": f"{content}",
            "source_id": f"{source_id}",
            "conversation": {
                "contact_inbox": {
                    "source_id": f"{source_id}"
                }
            }
        },
        "wamid": wamid,
        "contact_name": contact_name,
        "from_bot": "",
        "contact_id":contact_id
    }
    try:
        ws.send(json.dumps(data))
        result = ws.recv()
        ws.close()
    except Exception as e:
        pass


def sent_message_text(conversation_id, content, content_type, wamid, message_id, created_at, contact_phonenumber, channel_id, contact_id, account):
    """Send text message via WebSocket."""
    account_id = account.account_id if hasattr(account, 'account_id') else account
    url_ws = f"wss://chatapi.icsl.me/ws/chat/{account_id}/?token=&from_bot=False"
    ws = websocket.WebSocket()
    ws.connect(url_ws)
    data = {
        "content": content,
        "content_type": 'text',
        "wamid": wamid,
        "from_bot": "False",
        "contact_id": contact_id,
        "channel_id": f"{channel_id}",
        "message_id": message_id,
        "created_at": f"{created_at}",
        "conversation_id": f"{conversation_id}"
    }
    try:
        ws.send(json.dumps(data))
        result = ws.recv()
        ws.close()
    except Exception as e:
        pass


def sent_message_image(conversation_id, caption, content_type, wamid, message_id, created_at, contact_phonenumber, media_url, channel_id, contact_id, account):
    """Send image message via WebSocket."""
    account_id = account.account_id if hasattr(account, 'account_id') else account
    url_ws = f"wss://chatapi.icsl.me/ws/chat/{account_id}/?token=&from_bot=False"
    ws = websocket.WebSocket()
    ws.connect(url_ws)
    data = {
        "caption": caption,
        "content_type": content_type,
        "wamid": wamid,
        "from_bot": "False",
        "channel_id": f"{channel_id}",
        "message_id": message_id,
        "contact_id":contact_id,
        "media_url": f"{media_url}",
        "created_at": f"{created_at}",
        "conversation_id": f"{conversation_id}"
    }
    try:
        ws.send(json.dumps(data))
        result = ws.recv()
        ws.close()
    except Exception as e:
        pass


def sent_message_video(conversation_id, caption, content_type, wamid, message_id, created_at, contact_phonenumber, media_url, channel_id, contact_id, account):
    """Send video message via WebSocket."""
    account_id = account.account_id if hasattr(account, 'account_id') else account
    url_ws = f"wss://chatapi.icsl.me/ws/chat/{account_id}/?token=&from_bot=False"
    ws = websocket.WebSocket()
    ws.connect(url_ws)
    data = {
        "caption": caption,
        "content_type": content_type,
        "wamid": wamid,
        "from_bot": "False",
        "channel_id": f"{channel_id}",
        "message_id": message_id,
        "contact_id":contact_id,
        "media_url": f"{media_url}",
        "created_at": f"{created_at}",
        "conversation_id": f"{conversation_id}"
    }
    try:
        ws.send(json.dumps(data))
        result = ws.recv()
        ws.close()
    except Exception as e:
        pass


def sent_message_audio(conversation_id, caption, content_type, wamid, message_id, created_at, phone_number, media_url, channel_id, contact_id, account):
    """Send audio message via WebSocket."""
    account_id = account.account_id if hasattr(account, 'account_id') else account
    url_ws = f"wss://chatapi.icsl.me/ws/chat/{account_id}/?token=&from_bot=False"
    ws = websocket.WebSocket()
    ws.connect(url_ws)
    data = {
        "caption": caption,
        "content_type": content_type,
        "wamid": wamid,
        "channel_id": f"{channel_id}",
        "from_bot": "False",
        "message_id": message_id,
        "contact_id":contact_id,
        "media_url": f"{media_url}",
        "created_at": f"{created_at}",
        "conversation_id": f"{conversation_id}"
    }
    try:
        ws.send(json.dumps(data))
        result = ws.recv()
        ws.close()
    except Exception as e:
        pass


def sent_message_document(conversation_id, caption, content_type, wamid, message_id, created_at, phone_number, media_url, mime_type, channel_id, contact_id, account):
    """Send document message via WebSocket."""
    account_id = account.account_id if hasattr(account, 'account_id') else account
    url_ws = f"wss://chatapi.icsl.me/ws/chat/{account_id}/?token=&from_bot=False"
    ws = websocket.WebSocket()
    ws.connect(url_ws)
    data = {
        "caption": caption,
        "content_type": content_type,
        "wamid": wamid,
        "from_bot": "False",
        "channel_id": f"{channel_id}",
        "message_id": message_id,
        "contact_id":contact_id,
        "media_url": f"{media_url}",
        "created_at": f"{created_at}",
        "conversation_id": f"{conversation_id}"
    }
    try:
        ws.send(json.dumps(data))
        result = ws.recv()
        ws.close()
    except Exception as e:
        pass


def read_receipt(channel_id, message_id, conversation_id, status, account):
    """Send read receipt via WebSocket."""
    account_id = account.account_id if hasattr(account, 'account_id') else account
    url_ws = f"wss://chatapi.icsl.me/ws/chat/{account_id}/?token=&from_bot=False"
    ws = websocket.WebSocket()
    ws.connect(url_ws)
    data = {
        "content_type": "message_status",
        "message_id": message_id,
        "channel_id": f"{channel_id}",
        "conversation_id": conversation_id,
        "status": status,
        "from_bot": "True"
    }
    try:
        ws.send(json.dumps(data))
        result = ws.recv()
        ws.close()
    except Exception as e:
        pass
